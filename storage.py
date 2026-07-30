from __future__ import annotations
import base64
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import TypeVar
import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet, InvalidToken
from config import *  # noqa: F403
from data_io import citizen_id, normalize_phone, repair_text
from i18n import status_label, t

JsonT = TypeVar("JsonT")


def _auth_current_user():
    from auth import current_user
    return current_user()


def _auth_current_username() -> str:
    from auth import current_username
    return current_username()


@contextmanager
def _data_file_lock(*, shared: bool = False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        lock_handle = DATA_LOCK_PATH.open("a+", encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(
            f"Ingen skriveadgang til datalageret ({DATA_DIR}). "
            "Genstart containeren med det nyeste image, eller kør: "
            f"chown -R 1000:1000 <din-data-mappe>"
        ) from exc
    with lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _load_json_file(path: Path, default: JsonT) -> JsonT:
    if not path.exists():
        return default
    with _data_file_lock(shared=True):
        try:
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return default


def _save_json_file(path: Path, payload: object) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with _data_file_lock(shared=False):
        _write_text_atomic(path, content)


def _get_or_create_encryption_key() -> bytes:
    env_key = os.environ.get("BORGERLISTE_ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")
    if ENCRYPTION_KEY_PATH.exists():
        return ENCRYPTION_KEY_PATH.read_bytes().strip()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    ENCRYPTION_KEY_PATH.write_bytes(key)
    _chmod_sensitive(ENCRYPTION_KEY_PATH)
    return key


def _get_fernet() -> Fernet:
    return Fernet(_get_or_create_encryption_key())


def encrypt_pii(value: str) -> str:
    text = repair_text(value)
    if not text or text.startswith(PII_ENC_PREFIX):
        return text
    token = _get_fernet().encrypt(text.encode("utf-8"))
    return PII_ENC_PREFIX + base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_pii(value: object) -> str:
    text = repair_text(value)
    if not text or not text.startswith(PII_ENC_PREFIX):
        return text
    encoded = text[len(PII_ENC_PREFIX) :]
    try:
        token = base64.urlsafe_b64decode(encoded.encode("ascii"))
        return _get_fernet().decrypt(token).decode("utf-8")
    except (InvalidToken, ValueError):
        return text


def encrypt_dict_pii(record: dict) -> dict:
    out = dict(record)
    for field in PII_FIELDS:
        if field in out and out[field]:
            out[field] = encrypt_pii(str(out[field]))
    return out


def decrypt_dict_pii(record: dict) -> dict:
    out = dict(record)
    for field in PII_FIELDS:
        if field in out and out[field]:
            out[field] = decrypt_pii(out[field])
    return out


def encrypt_df_pii(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in PII_FIELDS:
        if column in out.columns:
            out[column] = out[column].map(lambda value: encrypt_pii(str(value)) if repair_text(value) else value)
    return out


def decrypt_df_pii(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in PII_FIELDS:
        if column in out.columns:
            out[column] = out[column].map(lambda value: decrypt_pii(value))
    return out


def _record_needs_encryption(record: dict) -> bool:
    for field in PII_FIELDS:
        value = str(record.get(field, ""))
        if value and not value.startswith(PII_ENC_PREFIX):
            return True
    return False


def _master_sync_is_stale() -> bool:
    try:
        if not MASTER_SYNC_STAMP_PATH.exists():
            return True
        last = float(MASTER_SYNC_STAMP_PATH.read_text(encoding="utf-8").strip())
        return (time.time() - last) >= MASTER_SYNC_INTERVAL_SECONDS
    except (ValueError, OSError):
        return True


def _touch_master_sync_stamp() -> None:
    _write_text_atomic(MASTER_SYNC_STAMP_PATH, f"{time.time()}\n")


def _cookie_secure_flag() -> bool | None:
    raw = os.environ.get("BORGERLISTE_COOKIE_SECURE", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return None


def _read_json_raw(path: Path, default: JsonT) -> JsonT:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


def person_lookup_key(row: pd.Series) -> str:
    key = f"{row['Navn']}|{row['Adresse']}".lower().strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def history_keys_for_row(row: pd.Series) -> list[str]:
    keys: list[str] = []
    phone = normalize_phone(row["Telefonnummer"])
    if phone:
        keys.append(f"phone:{phone}")
    keys.append(f"person:{person_lookup_key(row)}")
    keys.append(citizen_id(row))
    return keys


def load_status_history() -> dict[str, dict]:
    data = _load_json_file(STATUS_HISTORY_PATH, {})
    if not isinstance(data, dict):
        return {}
    decrypted = {
        key: decrypt_dict_pii(entry) if isinstance(entry, dict) else entry
        for key, entry in data.items()
    }
    if any(isinstance(entry, dict) and _record_needs_encryption(entry) for entry in data.values()):
        save_status_history(decrypted)
    return decrypted


def save_status_history(history: dict[str, dict]) -> None:
    encrypted = {
        key: encrypt_dict_pii(entry) if isinstance(entry, dict) else entry
        for key, entry in history.items()
    }
    _save_json_file(STATUS_HISTORY_PATH, encrypted)


def history_entry_from_row(row: pd.Series) -> dict[str, str]:
    return {
        "Status": str(row["Status"]),
        "Status dato": repair_text(row.get("Status dato", "")),
        "Ring igen dato": repair_text(row.get("Ring igen dato", "")),
        "Navn": repair_text(row["Navn"]),
        "Adresse": repair_text(row["Adresse"]),
        "Telefonnummer": repair_text(row["Telefonnummer"]),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def lookup_history_entry(row: pd.Series, history: dict[str, dict]) -> dict | None:
    for key in history_keys_for_row(row):
        entry = history.get(key)
        if isinstance(entry, dict) and entry.get("Status") in STATUSES:
            return entry
    return None


def upsert_history_entry(row: pd.Series, history: dict[str, dict]) -> None:
    entry = history_entry_from_row(row)
    for key in history_keys_for_row(row):
        history[key] = entry.copy()


def apply_history_statuses(df: pd.DataFrame, history: dict[str, dict]) -> pd.DataFrame:
    out = df.copy()
    out["_id"] = out.apply(citizen_id, axis=1)
    out["Status"] = DEFAULT_STATUS
    out["Status dato"] = ""
    out["Ring igen dato"] = ""

    for idx, row in out.iterrows():
        entry = lookup_history_entry(row, history)
        if not entry:
            continue
        status = repair_text(entry.get("Status", DEFAULT_STATUS))
        if status not in STATUSES:
            continue
        out.at[idx, "Status"] = status
        out.at[idx, "Status dato"] = repair_text(entry.get("Status dato", ""))
        out.at[idx, "Ring igen dato"] = repair_text(entry.get("Ring igen dato", ""))

    return out


def sync_history_from_dataframe(df: pd.DataFrame) -> None:
    history = load_status_history()
    for _, row in df.iterrows():
        if row["Status"] != DEFAULT_STATUS or row.get("Status dato"):
            upsert_history_entry(row, history)
    save_status_history(history)


def list_storage_key(filename: str, df: pd.DataFrame) -> str:
    ids = sorted(df.apply(citizen_id, axis=1).tolist())
    digest = hashlib.sha256("|".join(ids).encode("utf-8")).hexdigest()[:12]
    safe_name = re.sub(r"[^\w\-]+", "_", Path(filename).stem)[:40]
    return f"{safe_name}_{digest}"


def safe_username(username: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", username.strip())
    return cleaned[:64] or "unknown"


def user_data_dir(username: str | None = None) -> Path:
    name = safe_username(username or _auth_current_username())
    path = USER_DATA_ROOT / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_active_list_parquet(username: str | None = None) -> Path:
    return user_data_dir(username) / "active_borgerliste.parquet"


def user_active_list_csv(username: str | None = None) -> Path:
    return user_data_dir(username) / "active_borgerliste.csv"


def user_active_session_path(username: str | None = None) -> Path:
    return user_data_dir(username) / "active_session.json"


def user_preferences_path(username: str | None = None) -> Path:
    return user_data_dir(username) / "preferences.json"


def storage_path(key: str, username: str | None = None) -> Path:
    return user_data_dir(username) / f"{key}.json"


def load_saved_state(key: str, username: str | None = None) -> dict[str, dict]:
    key = _safe_storage_key(key)
    path = storage_path(key, username)
    data = _load_json_file(path, {})
    return data if isinstance(data, dict) else {}


def save_state(key: str, state: dict[str, dict], username: str | None = None) -> None:
    key = _safe_storage_key(key)
    path = storage_path(key, username)
    _save_json_file(path, state)


def load_user_preferences(username: str | None = None) -> dict:
    path = user_preferences_path(username)
    if not path.exists() and USER_PREFERENCES_PATH.exists():
        path = USER_PREFERENCES_PATH
    data = _load_json_file(path, {})
    return data if isinstance(data, dict) else {}


def save_user_preferences(**updates: object) -> None:
    if not _auth_current_user():
        return
    prefs = load_user_preferences()
    prefs.update(updates)
    _save_json_file(user_preferences_path(), prefs)


def apply_saved_user_preferences() -> None:
    prefs = load_user_preferences()
    theme = prefs.get("theme_choice")
    if theme in THEME_OPTIONS:
        st.session_state.theme_choice = theme
    language = prefs.get("language")
    if language in ("da", "en"):
        st.session_state.language = language
    if "sidebar_pinned" in prefs:
        st.session_state.sidebar_pinned = bool(prefs.get("sidebar_pinned"))


def migrate_legacy_data_to_user(username: str) -> None:
    user_dir = user_data_dir(username)
    if any(user_dir.iterdir()):
        return

    for legacy, name in (
        (LEGACY_ACTIVE_LIST_PARQUET, "active_borgerliste.parquet"),
        (LEGACY_ACTIVE_LIST_CSV, "active_borgerliste.csv"),
        (LEGACY_ACTIVE_SESSION_PATH, "active_session.json"),
    ):
        if legacy.exists():
            shutil.copy2(legacy, user_dir / name)

    preserved = {
        USERS_PATH.name,
        AUDIT_LOG_PATH.name,
        MASTER_REFERENCE_REGISTER_PATH.name,
        USER_PREFERENCES_PATH.name,
        STATUS_HISTORY_PATH.name,
    }
    for path in DATA_DIR.glob("*.json"):
        if path.name in preserved:
            continue
        shutil.copy2(path, user_dir / path.name)

    if USER_PREFERENCES_PATH.exists() and not user_preferences_path(username).exists():
        shutil.copy2(USER_PREFERENCES_PATH, user_preferences_path(username))


def ensure_user_data_loaded() -> None:
    if not st.session_state.get("authenticated") or not _auth_current_user():
        return
    username = _auth_current_username()
    first_load = st.session_state.get("user_data_loaded_for") != username

    if first_load:
        migrate_legacy_data_to_user(username)
        apply_saved_user_preferences()
        if not st.session_state.get("retention_applied"):
            purged = apply_data_retention()
            st.session_state.retention_applied = True
            if purged:
                st.session_state.retention_purged_count = purged
        st.session_state.user_data_loaded_for = username

    df = st.session_state.get("citizens_df")
    if df is None or (hasattr(df, "empty") and df.empty):
        restore_active_list_if_available()


def save_active_session_metadata() -> None:
    if not _auth_current_user():
        return
    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return

    meta = {
        "source_filename": st.session_state.get("source_filename"),
        "list_key": st.session_state.get("list_key"),
        "page_number": st.session_state.get("page_number", 0),
        "page_size": st.session_state.get("page_size", 25),
        "selected_filter": st.session_state.get("selected_filter", "all"),
        "show_uploader": st.session_state.get("show_uploader", False),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_json_file(user_active_session_path(), meta)


def save_active_list(df: pd.DataFrame, *, username: str | None = None) -> None:
    owner = username or (_auth_current_username() if _auth_current_user() else None)
    if not owner:
        return
    parquet_path = user_active_list_parquet(owner)
    csv_path = user_active_list_csv(owner)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    export_df = encrypt_df_pii(df.copy())
    for column in ("Navn", "Adresse", "Telefonnummer", "Status", "Status dato", "Ring igen dato"):
        if column in export_df.columns:
            export_df[column] = export_df[column].map(_excel_safe_cell)

    saved_as_parquet = False
    try:
        export_df.to_parquet(parquet_path, index=False)
        saved_as_parquet = True
        if csv_path.exists():
            csv_path.unlink()
    except Exception:
        export_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        if parquet_path.exists():
            parquet_path.unlink()

    if saved_as_parquet or csv_path.exists():
        if not username:
            save_active_session_metadata()


def _read_active_list_file(username: str | None = None) -> pd.DataFrame | None:
    parquet_path = user_active_list_parquet(username)
    csv_path = user_active_list_csv(username)

    if parquet_path.exists():
        try:
            return decrypt_df_pii(pd.read_parquet(parquet_path))
        except Exception:
            pass

    if csv_path.exists():
        try:
            return decrypt_df_pii(pd.read_csv(csv_path, encoding="utf-8-sig"))
        except Exception:
            pass

    return None


def _load_active_session_metadata(username: str | None = None) -> dict:
    data = _load_json_file(user_active_session_path(username), {})
    return data if isinstance(data, dict) else {}


def restore_active_list_if_available() -> bool:
    if not _auth_current_user():
        return False

    df = _read_active_list_file()
    if df is None or df.empty:
        return False

    for column in ("Navn", "Adresse", "Telefonnummer"):
        if column not in df.columns:
            return False

    if "Status" not in df.columns:
        df["Status"] = DEFAULT_STATUS
    if "Status dato" not in df.columns:
        df["Status dato"] = ""
    if "Ring igen dato" not in df.columns:
        df["Ring igen dato"] = ""

    for column in df.columns:
        if column in {"Navn", "Adresse", "Telefonnummer", "Status", "Status dato", "Ring igen dato"}:
            df[column] = df[column].map(repair_text)

    if "_id" not in df.columns:
        df["_id"] = df.apply(citizen_id, axis=1)

    meta = _load_active_session_metadata()
    list_key = meta.get("list_key")
    if list_key:
        list_state = load_saved_state(str(list_key))
        if list_state:
            df = apply_saved_statuses(df, list_state)
    from matching import load_master_register, maybe_sync_master_from_all_user_data, merge_master_register_statuses

    maybe_sync_master_from_all_user_data(force=True)
    register = load_master_register()
    df, _matched = merge_master_register_statuses(df, register)

    page_size = meta.get("page_size", 25)
    selected_filter = meta.get("selected_filter", meta.get("filter_key", "all"))

    st.session_state.citizens_df = df.reset_index(drop=True)
    st.session_state.list_key = list_key
    st.session_state.source_filename = meta.get("source_filename") or "borgerliste"
    st.session_state.page_number = int(meta.get("page_number", 0))
    st.session_state.page_size = page_size if page_size in PAGE_SIZE_OPTIONS else 25
    st.session_state.selected_filter = selected_filter if selected_filter in FILTER_KEYS else "all"
    st.session_state.show_uploader = bool(meta.get("show_uploader", False))
    st.session_state.filter_signature = None
    st.session_state.session_restored = True
    sync_history_from_dataframe(st.session_state.citizens_df)
    return True


def clear_active_list(*, username: str | None = None, list_key: str | None = None) -> None:
    owner = username
    if owner is None and _auth_current_user():
        owner = _auth_current_username()

    if owner and owner != "unknown":
        for path in (
            user_active_list_parquet(owner),
            user_active_list_csv(owner),
            user_active_session_path(owner),
        ):
            if path.exists():
                path.unlink()

        key = list_key if list_key is not None else st.session_state.get("list_key")
        if key:
            try:
                list_path = storage_path(str(key), owner)
                if list_path.exists():
                    list_path.unlink()
            except ValueError:
                pass

    st.session_state.citizens_df = None
    st.session_state.list_key = None
    st.session_state.source_filename = None
    st.session_state.page_number = 0
    st.session_state.page_size = 25
    st.session_state.selected_filter = "all"
    st.session_state.search_query = ""
    st.session_state.filter_signature = None
    st.session_state.show_uploader = True
    st.session_state.session_restored = False


def set_selected_filter(filter_value: str) -> None:
    st.session_state.selected_filter = filter_value
    st.session_state.page_number = 0
    st.session_state.filter_signature = None


def today_str() -> str:
    return datetime.now().strftime("%d-%m-%Y")


def add_months(base: datetime, months: int) -> datetime:
    month = base.month - 1 + months
    year = base.year + month // 12
    month = month % 12 + 1
    day = min(
        base.day,
        [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1],
    )
    return datetime(year, month, day)


def apply_saved_statuses(df: pd.DataFrame, saved: dict[str, dict]) -> pd.DataFrame:
    out = df.copy()
    out["_id"] = out.apply(citizen_id, axis=1)
    out["Status"] = DEFAULT_STATUS
    out["Status dato"] = ""
    out["Ring igen dato"] = ""

    for idx, row in out.iterrows():
        entry = saved.get(row["_id"])
        if not entry:
            continue
        status = repair_text(entry.get("Status", DEFAULT_STATUS))
        if status not in STATUSES:
            status = DEFAULT_STATUS
        out.at[idx, "Status"] = status
        out.at[idx, "Status dato"] = repair_text(entry.get("Status dato", ""))
        out.at[idx, "Ring igen dato"] = repair_text(entry.get("Ring igen dato", ""))

    return out


def dataframe_to_state(df: pd.DataFrame) -> dict[str, dict]:
    return {
        row["_id"]: {
            "Status": row["Status"],
            "Status dato": row["Status dato"],
            "Ring igen dato": row["Ring igen dato"],
        }
        for _, row in df.iterrows()
    }


def count_by_status(df: pd.DataFrame) -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for status in df["Status"]:
        if status in counts:
            counts[status] += 1
    return counts


def update_citizen_status(full_df: pd.DataFrame, citizen_key: str, new_status: str) -> pd.DataFrame:
    out = full_df.copy()
    mask = out["_id"] == citizen_key
    if not mask.any():
        return out

    old_status = out.loc[mask, "Status"].iloc[0]
    if new_status not in STATUSES:
        new_status = DEFAULT_STATUS
    if new_status == old_status:
        return out

    now = today_str()
    ring_again = add_months(datetime.now(), 6).strftime("%d-%m-%Y")
    out.loc[mask, "Status"] = new_status
    out.loc[mask, "Status dato"] = now
    out.loc[mask, "Ring igen dato"] = ring_again if new_status == "Ring igen om 6 måneder" else ""
    return out


def _safe_storage_key(key: str) -> str:
    cleaned = Path(key).name
    if not re.fullmatch(r"[\w\-]+", cleaned):
        raise ValueError("Invalid storage key")
    return cleaned


def _excel_safe_cell(value: object) -> str:
    text_value = repair_text(value)
    if text_value and text_value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text_value
    return text_value


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    sheet_name = (t("sheet_name") or "Borgerliste")[:31]
    column_names = {
        "Navn": t("col_name"),
        "Adresse": t("col_address"),
        "Telefonnummer": t("col_phone"),
        "Status": t("col_status"),
        "Status dato": t("col_status_date"),
        "Ring igen dato": t("col_call_again"),
    }
    export_df = df[DISPLAY_COLUMNS].copy()
    for column in export_df.columns:
        export_df[column] = export_df[column].map(_excel_safe_cell)
    export_df["Status"] = export_df["Status"].map(lambda s: status_label(s, short=False))
    export_df = export_df.rename(columns=column_names)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for idx, column in enumerate(export_df.columns, start=1):
            max_len = max([len(str(column))] + [len(str(value)) for value in export_df[column].head(200)])
            col_letter = worksheet.cell(row=1, column=idx).column_letter
            worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)

    return buffer.getvalue()


def _sidebar_excel_cache_key() -> str | None:
    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return None
    list_key = st.session_state.get("list_key") or "unknown"
    return f"{list_key}:{len(df)}"


def sidebar_excel_bytes() -> bytes:
    """Generér Excel-eksport én gang pr. liste og genbrug ved efterfølgende renders."""
    cache_key = _sidebar_excel_cache_key()
    if cache_key is None:
        return b""
    if st.session_state.get("_sidebar_excel_key") != cache_key:
        st.session_state._sidebar_excel_bytes = to_excel_bytes(st.session_state.citizens_df)
        st.session_state._sidebar_excel_key = cache_key
    return st.session_state.get("_sidebar_excel_bytes") or b""


def _chmod_sensitive(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_audit_log() -> list[dict]:
    data = _load_json_file(AUDIT_LOG_PATH, None)
    if data is None:
        return []
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        entries = [entry for entry in data["entries"] if isinstance(entry, dict)]
    elif isinstance(data, list):
        entries = [entry for entry in data if isinstance(entry, dict)]
    else:
        return []

    sanitized = [_sanitize_audit_entry(entry) for entry in entries]
    if sanitized != entries:
        save_audit_log(sanitized)
    return sanitized


def save_audit_log(entries: list[dict]) -> None:
    trimmed = [_sanitize_audit_entry(entry) for entry in entries[-MAX_AUDIT_ENTRIES:]]
    _save_json_file(AUDIT_LOG_PATH, {"entries": trimmed})


def _sanitize_audit_entry(entry: dict) -> dict:
    return {
        key: value
        for key, value in entry.items()
        if key not in {"citizen_name", "citizen_address", "citizen_phone"}
    }


def append_audit_log(
    *,
    citizen_id: str,
    old_status: str,
    new_status: str,
    list_key: str | None,
) -> None:
    entry = {
        "id": secrets.token_hex(8),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "username": _auth_current_username(),
        "role": _auth_current_user().get("role", "user") if _auth_current_user() else "user",
        "citizen_id": citizen_id,
        "old_status": old_status,
        "new_status": new_status,
        "list_key": list_key,
    }
    entries = load_audit_log()
    entries.append(entry)
    save_audit_log(entries)


def latest_audit_for_citizen(citizen_id: str) -> dict | None:
    for entry in reversed(load_audit_log()):
        if entry.get("citizen_id") == citizen_id:
            return entry
    return None


def configured_retention_months() -> int:
    settings = load_app_settings()
    raw = settings.get("data_retention_months")
    if raw is not None:
        try:
            return max(MIN_RETENTION_MONTHS, min(MAX_RETENTION_MONTHS, int(raw)))
        except (TypeError, ValueError):
            pass
    return DEFAULT_RETENTION_MONTHS


def _entry_activity_date(entry: dict) -> datetime:
    updated_at = repair_text(entry.get("updated_at", ""))
    if updated_at:
        try:
            return datetime.fromisoformat(updated_at)
        except ValueError:
            pass
    date_str = repair_text(entry.get("Status dato", ""))
    if date_str:
        try:
            return datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            pass
    return datetime.min


def _history_entry_matches_row(entry: dict, row: pd.Series) -> bool:
    from matching import master_match_score

    if not isinstance(entry, dict):
        return False
    decoded = decrypt_dict_pii(entry)
    return master_match_score(row, decoded) >= 2


def _register_entry_matches_row(entry: dict, row: pd.Series) -> bool:
    from matching import master_match_score

    decoded = decrypt_dict_pii(entry) if any(str(entry.get(field, "")).startswith(PII_ENC_PREFIX) for field in PII_FIELDS) else entry
    return master_match_score(row, decoded) >= 2


def delete_user_data(username: str) -> None:
    user_dir = USER_DATA_ROOT / safe_username(username)
    if user_dir.exists():
        shutil.rmtree(user_dir)


def erase_citizen_data(row: pd.Series) -> None:
    """Fjern én borger fra alle lagre (Art. 17 — ret til sletning)."""
    from matching import _parse_master_register_payload

    target_id = str(row["_id"])
    history_keys = set(history_keys_for_row(row))

    with _data_file_lock(shared=False):
        register_payload = _read_json_raw(MASTER_REFERENCE_REGISTER_PATH, {"cleared": False, "entries": []})
        register_state = _parse_master_register_payload(register_payload)
        register = register_state["entries"]  # type: ignore[assignment]
        if isinstance(register, list):
            filtered_register = [entry for entry in register if not _register_entry_matches_row(entry, row)]
            if len(filtered_register) != len(register):
                _write_text_atomic(
                    MASTER_REFERENCE_REGISTER_PATH,
                    json.dumps({"cleared": False, "entries": filtered_register}, ensure_ascii=False, indent=2) + "\n",
                )

        history = _read_json_raw(STATUS_HISTORY_PATH, {})
        if isinstance(history, dict):
            filtered_history = {
                key: value
                for key, value in history.items()
                if key not in history_keys and not _history_entry_matches_row(value, row)
            }
            if len(filtered_history) != len(history):
                _write_text_atomic(
                    STATUS_HISTORY_PATH,
                    json.dumps(filtered_history, ensure_ascii=False, indent=2) + "\n",
                )

        audit_payload = _read_json_raw(AUDIT_LOG_PATH, {"entries": []})
        if isinstance(audit_payload, dict) and isinstance(audit_payload.get("entries"), list):
            audit_entries = audit_payload["entries"]
        elif isinstance(audit_payload, list):
            audit_entries = audit_payload
        else:
            audit_entries = []
        filtered_audit = [
            _sanitize_audit_entry(entry)
            for entry in audit_entries
            if isinstance(entry, dict) and entry.get("citizen_id") != target_id
        ]
        if len(filtered_audit) != len(audit_entries):
            _write_text_atomic(
                AUDIT_LOG_PATH,
                json.dumps({"entries": filtered_audit[-MAX_AUDIT_ENTRIES:]}, ensure_ascii=False, indent=2) + "\n",
            )

        if USER_DATA_ROOT.exists():
            for user_dir in USER_DATA_ROOT.iterdir():
                if not user_dir.is_dir():
                    continue
                owner = user_dir.name
                for json_path in user_dir.glob("*.json"):
                    if json_path.name in ("active_session.json", "preferences.json"):
                        continue
                    data = _load_json_file(json_path, {})
                    if isinstance(data, dict) and target_id in data:
                        del data[target_id]
                        _save_json_file(json_path, data)

                active_df = _read_active_list_file(owner)
                if active_df is not None and not active_df.empty:
                    if "_id" not in active_df.columns:
                        active_df = active_df.copy()
                        active_df["_id"] = active_df.apply(citizen_id, axis=1)
                    active_df = active_df[active_df["_id"] != target_id].reset_index(drop=True)
                    if active_df.empty:
                        for path in (user_active_list_parquet(owner), user_active_list_csv(owner)):
                            if path.exists():
                                path.unlink()
                    else:
                        save_active_list(active_df, username=owner)

    df = st.session_state.get("citizens_df")
    if isinstance(df, pd.DataFrame) and not df.empty and "_id" in df.columns:
        if target_id in df["_id"].values:
            updated = df[df["_id"] != target_id].reset_index(drop=True)
            st.session_state.citizens_df = updated if not updated.empty else None
            if updated.empty:
                clear_active_list()
            else:
                save_active_list(updated)


def apply_data_retention() -> int:
    from matching import load_master_register

    months = configured_retention_months()
    if months <= 0:
        return 0
    cutoff = datetime.now() - timedelta(days=months * 30)
    purged = 0
    for entry in list(load_master_register()):
        if _entry_activity_date(entry) >= cutoff:
            continue
        row = pd.Series(
            {
                "Navn": entry.get("Navn", ""),
                "Adresse": entry.get("Adresse", ""),
                "Telefonnummer": entry.get("Telefonnummer", ""),
                "Status": entry.get("Status", DEFAULT_STATUS),
                "Status dato": entry.get("Status dato", ""),
                "Ring igen dato": entry.get("Ring igen dato", ""),
            }
        )
        row["_id"] = citizen_id(row)
        erase_citizen_data(row)
        purged += 1
    return purged


def collect_citizen_data_export(row: pd.Series) -> dict:
    """Indsaml alle gemte data om én borger (Art. 15/20 — indsigt og portabilitet)."""
    from matching import find_master_register_match, load_master_register

    target_id = str(row["_id"])
    history = load_status_history()
    history_entries = {
        key: value
        for key, value in history.items()
        if key in history_keys_for_row(row) or _history_entry_matches_row(value, row)
    }
    audit_entries = [entry for entry in load_audit_log() if entry.get("citizen_id") == target_id]
    master_entry = find_master_register_match(row, load_master_register())
    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "citizen_id": target_id,
        "personal_data": {
            "Navn": repair_text(row["Navn"]),
            "Adresse": repair_text(row["Adresse"]),
            "Telefonnummer": repair_text(row["Telefonnummer"]),
        },
        "status": {
            "Status": repair_text(row.get("Status", DEFAULT_STATUS)),
            "Status dato": repair_text(row.get("Status dato", "")),
            "Ring igen dato": repair_text(row.get("Ring igen dato", "")),
        },
        "master_register": master_entry,
        "history": history_entries,
        "audit_log": audit_entries,
    }


def build_citizen_label_map() -> dict[str, str]:
    from matching import load_master_register

    labels: dict[str, str] = {}
    for entry in load_master_register():
        row = pd.Series(
            {
                "Navn": entry.get("Navn", ""),
                "Adresse": entry.get("Adresse", ""),
                "Telefonnummer": entry.get("Telefonnummer", ""),
            }
        )
        labels[citizen_id(row)] = repair_text(entry.get("Navn", "")) or str(citizen_id(row))
    df = st.session_state.get("citizens_df")
    if isinstance(df, pd.DataFrame) and not df.empty and "_id" in df.columns:
        for _, row in df.iterrows():
            labels[str(row["_id"])] = repair_text(row["Navn"])
    return labels


def load_app_settings() -> dict:
    data = _load_json_file(APP_SETTINGS_PATH, {})
    return data if isinstance(data, dict) else {}


def save_app_settings(**updates: object) -> None:
    settings = load_app_settings()
    for key, value in updates.items():
        if value is None:
            settings.pop(key, None)
        else:
            settings[key] = value
    _save_json_file(APP_SETTINGS_PATH, settings)
    _chmod_sensitive(APP_SETTINGS_PATH)


def configured_session_idle_minutes() -> int:
    settings = load_app_settings()
    raw_minutes = settings.get("session_idle_minutes")
    if raw_minutes is not None:
        try:
            return max(MIN_SESSION_IDLE_MINUTES, min(MAX_SESSION_IDLE_MINUTES, int(raw_minutes)))
        except (TypeError, ValueError):
            pass

    raw_hours = settings.get("session_idle_hours")
    if raw_hours is not None:
        try:
            minutes = int(float(raw_hours) * 60)
            return max(MIN_SESSION_IDLE_MINUTES, min(MAX_SESSION_IDLE_MINUTES, minutes))
        except (TypeError, ValueError):
            pass

    env_minutes = os.environ.get("BORGERLISTE_SESSION_IDLE_MINUTES", "").strip()
    if env_minutes:
        try:
            minutes = int(float(env_minutes))
            return max(MIN_SESSION_IDLE_MINUTES, min(MAX_SESSION_IDLE_MINUTES, minutes))
        except ValueError:
            pass

    env_hours = os.environ.get("BORGERLISTE_SESSION_IDLE_HOURS", "").strip()
    if env_hours:
        try:
            minutes = int(float(env_hours) * 60)
            return max(MIN_SESSION_IDLE_MINUTES, min(MAX_SESSION_IDLE_MINUTES, minutes))
        except ValueError:
            pass

    return DEFAULT_SESSION_IDLE_MINUTES


def session_idle_timeout_seconds() -> int:
    return max(60, configured_session_idle_minutes() * 60)

