from __future__ import annotations
import json
import re
import shutil
from datetime import datetime
import pandas as pd
import streamlit as st
from config import *  # noqa: F403
from data_io import citizen_id, normalize_phone, repair_text
from i18n import t
from storage import (
    _data_file_lock, _load_json_file, _read_json_raw, _record_needs_encryption,
    _save_json_file, _touch_master_sync_stamp, _master_sync_is_stale, clear_active_list,
    decrypt_dict_pii, encrypt_dict_pii, load_status_history, save_status_history,
    _read_active_list_file,
)


def maybe_sync_master_from_all_user_data(*, force: bool = False) -> bool:
    """Synk master-register fra alle brugere — throttlet medmindre force=True."""
    if is_master_register_cleared():
        return False
    if not force and not _master_sync_is_stale():
        return False
    sync_master_from_all_user_data()
    _touch_master_sync_stamp()
    return True


def normalize_match_text(value: object) -> str:
    return re.sub(r"\s+", " ", repair_text(value).lower()).strip()


def normalize_match_address(value: object) -> str:
    text = normalize_match_text(value)
    if not text:
        return ""
    text = re.sub(r"\b\d{4}\b", " ", text)
    text = re.sub(r"\b(vej|gade|alle|allé|boulevard|plads|stræde|st\.?)\b", " ", text)
    text = re.sub(r"\b(nr\.?|nummer|etage|sal|stuen|th|tv|mf)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _address_tokens(value: str) -> set[str]:
    return {token for token in value.split() if len(token) >= 2}


def addresses_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    if left in right or right in left:
        return True
    left_tokens = _address_tokens(left)
    right_tokens = _address_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shorter, longer = (left_tokens, right_tokens) if len(left_tokens) <= len(right_tokens) else (right_tokens, left_tokens)
    return shorter.issubset(longer)


def normalize_match_phone(value: object) -> str:
    return normalize_phone(str(value or ""))


def master_field_matches(row_value: object, entry_value: object, field: str) -> bool:
    if field == "Telefonnummer":
        left = normalize_match_phone(row_value)
        right = normalize_match_phone(entry_value)
        if len(left) < 6 or len(right) < 6:
            return False
        return left == right
    if field == "Adresse":
        left = normalize_match_address(row_value)
        right = normalize_match_address(entry_value)
        return addresses_match(left, right)
    left = normalize_match_text(row_value)
    right = normalize_match_text(entry_value)
    if not left or not right:
        return False
    return left == right


def master_match_score(row: pd.Series, entry: dict) -> int:
    score = 0
    if master_field_matches(row["Navn"], entry.get("Navn"), "Navn"):
        score += 1
    if master_field_matches(row["Adresse"], entry.get("Adresse"), "Adresse"):
        score += 1
    if master_field_matches(row["Telefonnummer"], entry.get("Telefonnummer"), "Telefonnummer"):
        score += 1
    return score


def master_register_entry_from_row(row: pd.Series) -> dict[str, str]:
    return {
        "Navn": repair_text(row["Navn"]),
        "Adresse": repair_text(row["Adresse"]),
        "Telefonnummer": repair_text(row["Telefonnummer"]),
        "Status": repair_text(row.get("Status", DEFAULT_STATUS)),
        "Status dato": repair_text(row.get("Status dato", "")),
        "Ring igen dato": repair_text(row.get("Ring igen dato", "")),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _migrate_status_history_to_master_register() -> list[dict]:
    history = load_status_history()
    if not history:
        return []

    register: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in history.values():
        if not isinstance(entry, dict) or entry.get("Status") not in STATUSES:
            continue
        fingerprint = (
            normalize_match_text(entry.get("Navn", "")),
            normalize_match_text(entry.get("Adresse", "")),
            normalize_match_phone(entry.get("Telefonnummer", "")),
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        register.append(
            {
                "Navn": repair_text(entry.get("Navn", "")),
                "Adresse": repair_text(entry.get("Adresse", "")),
                "Telefonnummer": repair_text(entry.get("Telefonnummer", "")),
                "Status": repair_text(entry.get("Status", DEFAULT_STATUS)),
                "Status dato": repair_text(entry.get("Status dato", "")),
                "Ring igen dato": repair_text(entry.get("Ring igen dato", "")),
                "updated_at": repair_text(entry.get("updated_at", ""))
                or datetime.now().isoformat(timespec="seconds"),
            }
        )
    return register


def _parse_master_register_payload(data: object) -> dict[str, object]:
    if isinstance(data, list):
        return {
            "cleared": False,
            "entries": [entry for entry in data if isinstance(entry, dict)],
        }
    if isinstance(data, dict):
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            entries = []
        return {
            "cleared": bool(data.get("cleared", False)),
            "entries": [entry for entry in entries if isinstance(entry, dict)],
        }
    return {"cleared": False, "entries": []}


def load_master_register_state() -> dict[str, object]:
    if MASTER_REFERENCE_REGISTER_PATH.exists():
        data = _load_json_file(MASTER_REFERENCE_REGISTER_PATH, None)
        if data is not None:
            return _parse_master_register_payload(data)

    migrated = _migrate_status_history_to_master_register()
    if migrated:
        save_master_register(migrated, cleared=False)
        return {"cleared": False, "entries": migrated}
    return {"cleared": False, "entries": []}


def _row_has_master_identity(row: pd.Series) -> bool:
    name = normalize_match_text(row.get("Navn", ""))
    address = normalize_match_text(row.get("Adresse", ""))
    phone = normalize_match_phone(row.get("Telefonnummer", ""))
    if name and address:
        return True
    if name and len(phone) >= 6:
        return True
    if address and len(phone) >= 6:
        return True
    return False


def _entry_has_master_identity(entry: dict) -> bool:
    return _row_has_master_identity(
        pd.Series(
            {
                "Navn": entry.get("Navn", ""),
                "Adresse": entry.get("Adresse", ""),
                "Telefonnummer": entry.get("Telefonnummer", ""),
            }
        )
    )


def normalize_master_register(register: list[dict]) -> list[dict]:
    """Fjern ugyldige poster og slå dubletter sammen."""
    normalized: list[dict] = []
    for raw_entry in register:
        if not isinstance(raw_entry, dict) or not _entry_has_master_identity(raw_entry):
            continue
        entry = {
            "Navn": repair_text(raw_entry.get("Navn", "")),
            "Adresse": repair_text(raw_entry.get("Adresse", "")),
            "Telefonnummer": repair_text(raw_entry.get("Telefonnummer", "")),
            "Status": repair_text(raw_entry.get("Status", DEFAULT_STATUS)),
            "Status dato": repair_text(raw_entry.get("Status dato", "")),
            "Ring igen dato": repair_text(raw_entry.get("Ring igen dato", "")),
            "updated_at": repair_text(raw_entry.get("updated_at", ""))
            or datetime.now().isoformat(timespec="seconds"),
        }
        row = pd.Series({**entry, "_id": ""})
        match = find_master_register_match(row, normalized)
        if match is None:
            normalized.append(entry)
            continue
        if _status_entry_timestamp(entry) >= _status_entry_timestamp(match):
            match.update(entry)
    return normalized


def load_master_register() -> list[dict]:
    state = load_master_register_state()
    entries = state["entries"]  # type: ignore[assignment]
    if not isinstance(entries, list):
        return []
    decrypted = [decrypt_dict_pii(entry) for entry in entries if isinstance(entry, dict)]
    normalized = normalize_master_register(decrypted)
    needs_save = len(normalized) != len(decrypted) or any(
        _record_needs_encryption(entry) for entry in entries if isinstance(entry, dict)
    )
    if needs_save:
        save_master_register(normalized, cleared=bool(state["cleared"]))
    return normalized


def is_master_register_cleared() -> bool:
    state = load_master_register_state()
    return bool(state["cleared"])


def save_master_register(register: list[dict], *, cleared: bool = False) -> None:
    encrypted = [encrypt_dict_pii(entry) for entry in register]
    _save_json_file(MASTER_REFERENCE_REGISTER_PATH, {"cleared": cleared, "entries": encrypted})


def clear_master_register() -> None:
    """Slet alt gemt borgerliste-data så appen kan startes helt forfra."""
    from auth import is_admin

    if not is_admin():
        raise PermissionError(t("master_delete_admin_only"))

    if STATUS_HISTORY_PATH.exists():
        STATUS_HISTORY_PATH.unlink()

    for path in (LEGACY_ACTIVE_LIST_PARQUET, LEGACY_ACTIVE_LIST_CSV, LEGACY_ACTIVE_SESSION_PATH):
        if path.exists():
            path.unlink()

    if USER_DATA_ROOT.exists():
        shutil.rmtree(USER_DATA_ROOT)
    USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)

    if DATA_DIR.exists():
        preserved = {
            USERS_PATH.name,
            APP_SETTINGS_PATH.name,
            AUTH_SESSIONS_PATH.name,
            LOGIN_ATTEMPTS_PATH.name,
        }
        for path in DATA_DIR.glob("*.json"):
            if path.name in preserved:
                continue
            path.unlink()

    if AUDIT_LOG_PATH.exists():
        AUDIT_LOG_PATH.unlink()

    save_master_register([], cleared=True)
    clear_active_list()


def find_master_register_match(row: pd.Series, register: list[dict]) -> dict | None:
    best_entry: dict | None = None
    best_score = 0
    best_updated = ""

    for entry in register:
        score = master_match_score(row, entry)
        if score < 2:
            continue
        updated_at = str(entry.get("updated_at", ""))
        if score > best_score or (score == best_score and updated_at > best_updated):
            best_score = score
            best_updated = updated_at
            best_entry = entry

    return best_entry


def _status_entry_timestamp(entry: dict) -> datetime:
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


def upsert_master_register_entry(row: pd.Series, register: list[dict]) -> None:
    if not _row_has_master_identity(row):
        return
    entry = master_register_entry_from_row(row)
    match = find_master_register_match(row, register)
    if match is None:
        register.append(entry)
        return
    if _status_entry_timestamp(entry) >= _status_entry_timestamp(match):
        match.update(entry)


def apply_master_register_statuses(df: pd.DataFrame, register: list[dict]) -> tuple[pd.DataFrame, int]:
    out = df.copy()
    out["_id"] = out.apply(citizen_id, axis=1)
    out["Status"] = DEFAULT_STATUS
    out["Status dato"] = ""
    out["Ring igen dato"] = ""

    matched = 0
    for idx, row in out.iterrows():
        entry = find_master_register_match(row, register)
        if not entry:
            continue
        status = repair_text(entry.get("Status", DEFAULT_STATUS))
        if status not in STATUSES:
            continue
        matched += 1
        out.at[idx, "Status"] = status
        out.at[idx, "Status dato"] = repair_text(entry.get("Status dato", ""))
        out.at[idx, "Ring igen dato"] = repair_text(entry.get("Ring igen dato", ""))

    return out, matched


def merge_master_register_statuses(df: pd.DataFrame, register: list[dict]) -> tuple[pd.DataFrame, int]:
    """Anvend master-status oven på eksisterende rækker uden at nulstille resten."""
    out = df.copy()
    if "_id" not in out.columns:
        out["_id"] = out.apply(citizen_id, axis=1)

    matched = 0
    for idx, row in out.iterrows():
        entry = find_master_register_match(row, register)
        if not entry:
            continue
        status = repair_text(entry.get("Status", DEFAULT_STATUS))
        if status not in STATUSES:
            continue
        matched += 1
        out.at[idx, "Status"] = status
        out.at[idx, "Status dato"] = repair_text(entry.get("Status dato", ""))
        out.at[idx, "Ring igen dato"] = repair_text(entry.get("Ring igen dato", ""))

    return out, matched


def sync_master_register_from_dataframe(df: pd.DataFrame) -> None:
    if is_master_register_cleared():
        return

    register = load_master_register()
    changed = False
    for _, row in df.iterrows():
        if row["Status"] != DEFAULT_STATUS or row.get("Status dato"):
            upsert_master_register_entry(row, register)
            changed = True
    if changed:
        save_master_register(register, cleared=False)


def _row_from_saved_entry(citizen_key: str, entry: dict) -> pd.Series:
    return pd.Series(
        {
            "Navn": repair_text(entry.get("Navn", "")),
            "Adresse": repair_text(entry.get("Adresse", "")),
            "Telefonnummer": repair_text(entry.get("Telefonnummer", "")),
            "Status": repair_text(entry.get("Status", DEFAULT_STATUS)),
            "Status dato": repair_text(entry.get("Status dato", "")),
            "Ring igen dato": repair_text(entry.get("Ring igen dato", "")),
            "_id": citizen_key,
        }
    )


def _sync_dataframe_rows_to_master(df: pd.DataFrame, register: list[dict]) -> bool:
    changed = False
    for _, row in df.iterrows():
        if row["Status"] != DEFAULT_STATUS or row.get("Status dato"):
            upsert_master_register_entry(row, register)
            changed = True
    return changed


def sync_master_from_all_user_data() -> None:
    """Opdater master-registeret med status fra alle brugeres gemte lister."""
    if is_master_register_cleared():
        return

    register = load_master_register()
    changed = False

    if USER_DATA_ROOT.exists():
        for user_dir in USER_DATA_ROOT.iterdir():
            if not user_dir.is_dir():
                continue

            for json_path in user_dir.glob("*.json"):
                if json_path.name in ("active_session.json", "preferences.json"):
                    continue
                try:
                    with json_path.open(encoding="utf-8") as handle:
                        data = json.load(handle)
                    if not isinstance(data, dict):
                        continue
                    for citizen_key, entry in data.items():
                        if not isinstance(entry, dict):
                            continue
                        if not entry.get("Navn") and not entry.get("Adresse"):
                            continue
                        status = repair_text(entry.get("Status", DEFAULT_STATUS))
                        if status == DEFAULT_STATUS and not entry.get("Status dato"):
                            continue
                        row = _row_from_saved_entry(str(citizen_key), entry)
                        upsert_master_register_entry(row, register)
                        changed = True
                except (json.JSONDecodeError, OSError):
                    continue

            active_df = _read_active_list_file(user_dir.name)
            if active_df is not None and not active_df.empty:
                if "_id" not in active_df.columns:
                    active_df = active_df.copy()
                    active_df["_id"] = active_df.apply(citizen_id, axis=1)
                if _sync_dataframe_rows_to_master(active_df, register):
                    changed = True

    if changed:
        save_master_register(register, cleared=False)

