"""
Borgerliste – Streamlit-værktøj til opfølgning på borgerkontakt.
Understøtter lokal kørsel og Docker-server med valgfri adgangskode.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DATA_DIR = Path(os.environ.get("BORGERLISTE_DATA_DIR", Path(__file__).resolve().parent / "data"))
ACTIVE_LIST_PARQUET = DATA_DIR / "active_borgerliste.parquet"
ACTIVE_LIST_CSV = DATA_DIR / "active_borgerliste.csv"
ACTIVE_SESSION_PATH = DATA_DIR / "active_session.json"
STATUS_HISTORY_PATH = DATA_DIR / "status_history.json"
MASTER_REFERENCE_REGISTER_PATH = DATA_DIR / "master_reference_register.json"
USER_PREFERENCES_PATH = DATA_DIR / "user_preferences.json"

STATUSES = [
    "Ikke kontaktet endnu",
    "Accepteret tilbud",
    "Afslået tilbud",
    "Ring igen om 6 måneder",
]
DEFAULT_STATUS = STATUSES[0]
PAGE_SIZE_OPTIONS: list[int | str] = [10, 25, 50, 100, "Alle"]

THEME_OPTIONS = ["Lyst tema", "Mørkt tema", "Browser standard"]
THEME_ICONS = {"Lyst tema": "☀️", "Mørkt tema": "🌙", "Browser standard": "🖥️"}

THEME_PALETTES = {
    "Lyst tema": {
        "bg": "#FAFAF9",
        "bg_secondary": "#F5F5F4",
        "input_bg": "#FFFFFF",
        "card_bg": "#FFFFFF",
        "text": "#1C1917",
        "text_muted": "#57534E",
        "border": "#E7E5E4",
        "color_scheme": "light",
        "card_shadow": "0 1px 3px rgba(0,0,0,0.05)",
        "card_border_subtle": "rgba(0,0,0,0.08)",
    },
    "Mørkt tema": {
        "bg": "#0F172A",
        "bg_secondary": "#1E293B",
        "input_bg": "#1E293B",
        "card_bg": "#1E293B",
        "text": "#F8FAFC",
        "text_muted": "#CBD5E1",
        "border": "#334155",
        "color_scheme": "dark",
        "card_shadow": "0 1px 3px rgba(0,0,0,0.25)",
        "card_border_subtle": "rgba(255,255,255,0.1)",
    },
}

PRIMARY_COLOR = "#2563EB"
PRIMARY_TEXT = "#FFFFFF"

FILTER_ACTIVE_COLORS = {
    "all": "#2563EB",
    "not_contacted": "#64748B",
    "accepted": "#10B981",
    "declined": "#EF4444",
    "call_again": "#F59E0B",
}

FILTER_KEYS = ["all", "not_contacted", "accepted", "declined", "call_again"]
FILTER_MAP = {
    "all": STATUSES,
    "not_contacted": ["Ikke kontaktet endnu"],
    "accepted": ["Accepteret tilbud"],
    "declined": ["Afslået tilbud"],
    "call_again": ["Ring igen om 6 måneder"],
}

STATUS_TO_FILTER = {
    "Ikke kontaktet endnu": "not_contacted",
    "Accepteret tilbud": "accepted",
    "Afslået tilbud": "declined",
    "Ring igen om 6 måneder": "call_again",
}

OVERVIEW_CARDS: list[tuple[str, str | None]] = [
    ("all", None),
    ("not_contacted", "Ikke kontaktet endnu"),
    ("accepted", "Accepteret tilbud"),
    ("declined", "Afslået tilbud"),
    ("call_again", "Ring igen om 6 måneder"),
]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "da": {
        "app_title": "Borgerliste",
        "app_subtitle": "Kontakt og opfølgning på borgere",
        "menu": "Menu",
        "language": "Sprog",
        "theme_light": "Lyst tema",
        "theme_dark": "Mørkt tema",
        "theme_browser": "Følger system (lys/mørk)",
        "gdpr_title": "Om datasikkerhed",
        "gdpr_text": (
            "Borgerdata gemmes kun lokalt på denne enhed eller server. "
            "Del ikke filer med personoplysninger uden for jeres sikre kanaler."
        ),
        "filter_title": "Filtrer borgere",
        "filter_all": "Alle borgere",
        "filter_not_contacted": "Ikke kontaktet",
        "filter_accepted": "Accepteret",
        "filter_declined": "Afslået",
        "filter_call_again": "Ring igen (6 mdr.)",
        "filter_btn_call_again": "Ring igen",
        "export_excel": "Gem opdateret Excel",
        "upload_expander": "📂 Upload borgerliste",
        "upload_expander_change": "📂 Upload / Skift borgerliste",
        "upload_loaded": "{filename} — {count} borgere indlæst",
        "upload_select_new": "Vælg ny fil",
        "upload_hint": "Vælg en Excel- eller CSV-fil med kolonnerne Navn, Adresse og Telefonnummer.",
        "upload_hint_new": "Vælg en ny fil, eller annuller for at beholde nuværende liste.",
        "upload_drag_hint": "Træk en fil hertil, eller klik for at vælge",
        "upload_browse": "Vælg fil",
        "upload_success": "{count} borgere er klar",
        "upload_keep_current": "Behold nuværende liste",
        "upload_error": "Kunne ikke læse filen. Tjek at den har kolonnerne Navn, Adresse og Telefon.",
        "missing_column": "Mangler kolonnen '{column}' i filen.",
        "upload_get_started": "Upload en fil ovenfor for at komme i gang.",
        "overview": "Overblik",
        "overview_filter_hint": "Klik en knap under et kort for at filtrere borgerlisten",
        "filter_apply": "Filtrer",
        "filter_show_all": "Vis alle borgere",
        "search_placeholder": "Navn, adresse eller telefon...",
        "citizens_summary": "{total} borgere i alt · {shown} vises med nuværende filter",
        "citizens_heading": "Borgere",
        "prev": "← Forrige",
        "next": "Næste →",
        "page_empty": "Ingen borgere at vise",
        "page_info": "Side {current} af {total}",
        "page_size_label": "Vis pr. side",
        "page_size_all": "Alle pr. side",
        "page_size_n": "{n} pr. side",
        "change_status": "Skift status",
        "last_updated": "Sidst opdateret: {date}",
        "call_again_date": "Ring igen: {date}",
        "status_saved": "Status gemt",
        "no_citizens_match": "Ingen borgere matcher dit filter. Prøv et andet filter eller søgning.",
        "login_title": "Log ind",
        "login_caption": "Adgangskode kræves for at beskytte borgerdata på netværket.",
        "login_password": "Adgangskode",
        "login_submit": "Log ind",
        "login_error": "Forkert adgangskode.",
        "status_not_contacted": "Ikke kontaktet endnu",
        "status_accepted": "Accepteret tilbud",
        "status_declined": "Afslået tilbud",
        "status_call_again": "Ring igen om 6 måneder",
        "status_short_not_contacted": "Ikke kontaktet",
        "status_short_accepted": "Accepteret",
        "status_short_declined": "Afslået",
        "status_short_call_again": "Ring igen (6 mdr.)",
        "col_name": "Navn",
        "col_address": "Adresse",
        "col_phone": "Telefonnummer",
        "col_status": "Status",
        "col_status_date": "Status dato",
        "col_call_again": "Ring igen dato",
        "sheet_name": "Borgerliste",
        "session_restored": "Indlæst gemt liste fra tidligere session",
        "clear_saved_list": "Ryd gemt liste",
        "master_register_count": "{count} borgere i master-registeret",
        "clear_master_register": "Slet master-register",
        "master_register_cleared": "Master-registeret er slettet.",
        "master_delete_warning": (
            "Dette sletter master-registeret, alle gemte lister og statusser. "
            "Appen starter forfra. Handlingen kan ikke fortrydes."
        ),
        "master_delete_password": "Adgangskode for at slette",
        "master_delete_confirm": "Bekræft sletning",
        "master_delete_password_error": "Forkert adgangskode.",
        "master_delete_password_required": (
            "Sletning kræver adgangskode. Sæt BORGERLISTE_PASSWORD i miljøvariabler."
        ),
        "upload_loaded_with_matches": (
            "Indlæst {count} borgere. Genkendte {matched} borgere fra tidligere "
            "registreringer via 2/3-matching."
        ),
    },
    "en": {
        "app_title": "Citizen list",
        "app_subtitle": "Contact and follow-up on citizens",
        "menu": "Menu",
        "language": "Language",
        "theme_light": "Light theme",
        "theme_dark": "Dark theme",
        "theme_browser": "Follow system (light/dark)",
        "gdpr_title": "Data security",
        "gdpr_text": (
            "Citizen data is stored locally on this device or server only. "
            "Do not share files containing personal data outside your secure channels."
        ),
        "filter_title": "Filter citizens",
        "filter_all": "All citizens",
        "filter_not_contacted": "Not contacted",
        "filter_accepted": "Accepted",
        "filter_declined": "Declined",
        "filter_call_again": "Call again (6 mo.)",
        "filter_btn_call_again": "Call again",
        "export_excel": "Save updated Excel",
        "upload_expander": "📂 Upload citizen list",
        "upload_expander_change": "📂 Upload / Change list",
        "upload_loaded": "{filename} — {count} citizens loaded",
        "upload_select_new": "Choose new file",
        "upload_hint": "Choose an Excel or CSV file with columns Name, Address and Phone number.",
        "upload_hint_new": "Choose a new file, or cancel to keep the current list.",
        "upload_drag_hint": "Drag a file here, or click to browse",
        "upload_browse": "Choose file",
        "upload_success": "{count} citizens ready",
        "upload_keep_current": "Keep current list",
        "upload_error": "Could not read the file. Check that it has Name, Address and Phone columns.",
        "missing_column": "Missing column '{column}' in the file.",
        "upload_get_started": "Upload a file above to get started.",
        "overview": "Overview",
        "overview_filter_hint": "Click a button below a card to filter the citizen list",
        "filter_apply": "Filter",
        "filter_show_all": "Show all citizens",
        "search_placeholder": "Name, address or phone...",
        "citizens_summary": "{total} citizens in total · {shown} shown with current filter",
        "citizens_heading": "Citizens",
        "prev": "← Previous",
        "next": "Next →",
        "page_empty": "No citizens to show",
        "page_info": "Page {current} of {total}",
        "page_size_label": "Rows per page",
        "page_size_all": "All rows",
        "page_size_n": "{n} per page",
        "change_status": "Change status",
        "last_updated": "Last updated: {date}",
        "call_again_date": "Call again: {date}",
        "status_saved": "Status saved",
        "no_citizens_match": "No citizens match your filter. Try another filter or search.",
        "login_title": "Sign in",
        "login_caption": "A password is required to protect citizen data on the network.",
        "login_password": "Password",
        "login_submit": "Sign in",
        "login_error": "Incorrect password.",
        "status_not_contacted": "Not contacted yet",
        "status_accepted": "Offer accepted",
        "status_declined": "Offer declined",
        "status_call_again": "Call again in 6 months",
        "status_short_not_contacted": "Not contacted",
        "status_short_accepted": "Accepted",
        "status_short_declined": "Declined",
        "status_short_call_again": "Call again (6 mo.)",
        "col_name": "Name",
        "col_address": "Address",
        "col_phone": "Phone number",
        "col_status": "Status",
        "col_status_date": "Status date",
        "col_call_again": "Call again date",
        "sheet_name": "Citizen list",
        "session_restored": "Loaded saved list from previous session",
        "clear_saved_list": "Clear saved list",
        "master_register_count": "{count} citizens in master register",
        "clear_master_register": "Delete master register",
        "master_register_cleared": "Master register deleted.",
        "master_delete_warning": (
            "This deletes the master register, all saved lists and statuses. "
            "The app starts fresh. This action cannot be undone."
        ),
        "master_delete_password": "Password to delete",
        "master_delete_confirm": "Confirm deletion",
        "master_delete_password_error": "Incorrect password.",
        "master_delete_password_required": (
            "Deletion requires a password. Set BORGERLISTE_PASSWORD in environment variables."
        ),
        "upload_loaded_with_matches": (
            "Loaded {count} citizens. Matched {matched} citizens from previous "
            "registrations via 2/3 matching."
        ),
    },
}

STATUS_I18N = {
    "Ikke kontaktet endnu": ("status_not_contacted", "status_short_not_contacted"),
    "Accepteret tilbud": ("status_accepted", "status_short_accepted"),
    "Afslået tilbud": ("status_declined", "status_short_declined"),
    "Ring igen om 6 måneder": ("status_call_again", "status_short_call_again"),
}

FILTER_I18N = {
    "all": "filter_all",
    "not_contacted": "filter_not_contacted",
    "accepted": "filter_accepted",
    "declined": "filter_declined",
    "call_again": "filter_call_again",
}

FILTER_BUTTON_I18N = {
    "all": "filter_all",
    "not_contacted": "filter_not_contacted",
    "accepted": "filter_accepted",
    "declined": "filter_declined",
    "call_again": "filter_btn_call_again",
}

STATUS_PILL_CLASS = {
    "Ikke kontaktet endnu": "status-pill--neutral",
    "Accepteret tilbud": "status-pill--accepted",
    "Afslået tilbud": "status-pill--declined",
    "Ring igen om 6 måneder": "status-pill--call-again",
}

COLUMN_ALIASES = {
    "Navn": ["navn", "name", "fulde navn", "borger"],
    "Adresse": ["adresse", "address", "vej", "gade"],
    "Telefonnummer": [
        "telefon", "telefonnummer", "tlf", "mobil", "phone", "telefon nr", "telefon nr.",
    ],
}

DISPLAY_COLUMNS = [
    "Navn", "Adresse", "Telefonnummer", "Status", "Status dato", "Ring igen dato",
]

CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1", "iso-8859-1")
MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "ï¿½", "�")
DANISH_CHARS = set("æøåÆØÅ")


# ---------------------------------------------------------------------------
# Sprog / i18n
# ---------------------------------------------------------------------------


def lang() -> str:
    return st.session_state.get("language", "da")


def t(key: str, **kwargs: object) -> str:
    text = TRANSLATIONS.get(lang(), TRANSLATIONS["da"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def status_label(status: str, short: bool = False) -> str:
    keys = STATUS_I18N.get(status)
    if not keys:
        return status
    return t(keys[1] if short else keys[0])


def filter_label(filter_key: str) -> str:
    return t(FILTER_I18N.get(filter_key, "filter_all"))


def filter_button_label(filter_key: str) -> str:
    return t(FILTER_BUTTON_I18N.get(filter_key, "filter_all"))


def page_size_label(value: int | str) -> str:
    if value == "Alle":
        return t("page_size_all")
    return t("page_size_n", n=value)


def theme_help(theme: str) -> str:
    mapping = {
        "Lyst tema": "theme_light",
        "Mørkt tema": "theme_dark",
        "Browser standard": "theme_browser",
    }
    return t(mapping.get(theme, "theme_light"))


# ---------------------------------------------------------------------------
# Tegnkodning / UTF-8
# ---------------------------------------------------------------------------


def normalize_header(value: object) -> str:
    return repair_text(re.sub(r"\s+", " ", str(value).strip().lower()))


def looks_like_mojibake(text: str) -> bool:
    if not text:
        return False
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        return True
    return "Ã" in text and not any(ch in text for ch in DANISH_CHARS)


def repair_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if not text:
        return text

    fixed = text
    for _ in range(4):
        if not looks_like_mojibake(fixed):
            break
        changed = False
        for encoding in ("latin-1", "cp1252", "iso-8859-1"):
            try:
                candidate = fixed.encode(encoding).decode("utf-8").strip()
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if candidate and candidate != fixed:
                fixed = candidate
                changed = True
                break
        if not changed:
            break
    return fixed


def repair_dataframe_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.select_dtypes(include=["object", "string"]).columns:
        out[column] = out[column].map(repair_text)
    return out


def encoding_quality_score(df: pd.DataFrame) -> float:
    sample = " ".join(
        str(value)
        for column in df.select_dtypes(include=["object", "string"]).columns
        for value in df[column].dropna().head(200)
    )
    if not sample:
        return 0.0
    score = 0.0
    score += sum(3 for ch in DANISH_CHARS if ch in sample)
    score -= sum(5 for marker in MOJIBAKE_MARKERS if marker in sample)
    score -= sample.count("Ã") * 4
    replacement = sample.count("�") + sample.count("ï¿½")
    score -= replacement * 6
    return score


def read_csv_bytes(raw: bytes) -> tuple[pd.DataFrame, str]:
    best_df: pd.DataFrame | None = None
    best_encoding = "utf-8"
    best_score = float("-inf")
    last_error: Exception | None = None

    for encoding in CSV_ENCODINGS:
        try:
            candidate = pd.read_csv(BytesIO(raw), encoding=encoding)
            score = encoding_quality_score(candidate)
            if score > best_score:
                best_score = score
                best_df = candidate
                best_encoding = encoding
        except Exception as exc:
            last_error = exc

    if best_df is None:
        raise ValueError(t("upload_error"))

    return repair_dataframe_text(best_df), best_encoding


def read_uploaded_file(uploaded_file) -> tuple[pd.DataFrame, str]:
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    if name.endswith(".csv"):
        raw = uploaded_file.read()
        df, encoding = read_csv_bytes(raw)
        return df, encoding
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
        return repair_dataframe_text(df), "excel"
    raise ValueError(t("upload_error"))


# ---------------------------------------------------------------------------
# Data / persistence
# ---------------------------------------------------------------------------


def find_column(df: pd.DataFrame, target: str) -> str | None:
    aliases = {normalize_header(alias) for alias in COLUMN_ALIASES[target]}
    for col in df.columns:
        if normalize_header(col) in aliases:
            return col
    return None


def standardize_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    for target in COLUMN_ALIASES:
        source = find_column(raw, target)
        if source is None:
            raise ValueError(t("missing_column", column=target))
        mapping[target] = source

    df = raw[[mapping["Navn"], mapping["Adresse"], mapping["Telefonnummer"]]].copy()
    df.columns = ["Navn", "Adresse", "Telefonnummer"]
    for column in df.columns:
        df[column] = df[column].map(repair_text)
    df = df[df["Navn"].str.len() > 0].reset_index(drop=True)
    return df


def citizen_id(row: pd.Series) -> str:
    key = f"{row['Navn']}|{row['Adresse']}|{row['Telefonnummer']}".lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D+", "", str(phone or ""))


def normalize_match_text(value: object) -> str:
    return re.sub(r"\s+", " ", repair_text(value).lower()).strip()


def normalize_match_phone(value: object) -> str:
    return normalize_phone(str(value or ""))


def master_field_matches(row_value: object, entry_value: object, field: str) -> bool:
    if field == "Telefonnummer":
        left = normalize_match_phone(row_value)
        right = normalize_match_phone(entry_value)
        if len(left) < 6 or len(right) < 6:
            return False
        return left == right
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
        try:
            with MASTER_REFERENCE_REGISTER_PATH.open(encoding="utf-8") as handle:
                data = json.load(handle)
            return _parse_master_register_payload(data)
        except (json.JSONDecodeError, OSError):
            pass

    migrated = _migrate_status_history_to_master_register()
    if migrated:
        save_master_register(migrated, cleared=False)
        return {"cleared": False, "entries": migrated}
    return {"cleared": False, "entries": []}


def load_master_register() -> list[dict]:
    state = load_master_register_state()
    return state["entries"]  # type: ignore[return-value]


def is_master_register_cleared() -> bool:
    state = load_master_register_state()
    return bool(state["cleared"])


def save_master_register(register: list[dict], *, cleared: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"cleared": cleared, "entries": register}
    with MASTER_REFERENCE_REGISTER_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def clear_master_register() -> None:
    """Slet alt gemt borgerliste-data så appen kan startes helt forfra."""
    if STATUS_HISTORY_PATH.exists():
        STATUS_HISTORY_PATH.unlink()

    for path in (ACTIVE_LIST_PARQUET, ACTIVE_LIST_CSV, ACTIVE_SESSION_PATH):
        if path.exists():
            path.unlink()

    if DATA_DIR.exists():
        preserved = {USER_PREFERENCES_PATH.name}
        for path in DATA_DIR.glob("*.json"):
            if path.name in preserved:
                continue
            path.unlink()

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


def upsert_master_register_entry(row: pd.Series, register: list[dict]) -> None:
    entry = master_register_entry_from_row(row)
    match = find_master_register_match(row, register)
    if match is None:
        register.append(entry)
        return
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
    if not STATUS_HISTORY_PATH.exists():
        return {}
    try:
        with STATUS_HISTORY_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_status_history(history: dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with STATUS_HISTORY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(history, handle, ensure_ascii=False, indent=2)


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


def storage_path(key: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{key}.json"


def load_saved_state(key: str) -> dict[str, dict]:
    path = storage_path(key)
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(key: str, state: dict[str, dict]) -> None:
    path = storage_path(key)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)


def load_user_preferences() -> dict:
    if not USER_PREFERENCES_PATH.exists():
        return {}
    try:
        with USER_PREFERENCES_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_user_preferences(**updates: object) -> None:
    prefs = load_user_preferences()
    prefs.update(updates)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with USER_PREFERENCES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(prefs, handle, ensure_ascii=False, indent=2)


def apply_saved_user_preferences() -> None:
    prefs = load_user_preferences()
    theme = prefs.get("theme_choice")
    if theme in THEME_OPTIONS:
        st.session_state.theme_choice = theme
    language = prefs.get("language")
    if language in ("da", "en"):
        st.session_state.language = language


def save_active_session_metadata() -> None:
    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return

    meta = {
        "source_filename": st.session_state.get("source_filename"),
        "list_key": st.session_state.get("list_key"),
        "page_number": st.session_state.get("page_number", 0),
        "page_size": st.session_state.get("page_size", 25),
        "selected_filter": st.session_state.get("selected_filter", "all"),
        "search_query": st.session_state.get("search_query", ""),
        "show_uploader": st.session_state.get("show_uploader", False),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with ACTIVE_SESSION_PATH.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)


def save_active_list(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_df = df.copy()
    for column in ("Navn", "Adresse", "Telefonnummer", "Status", "Status dato", "Ring igen dato"):
        if column in export_df.columns:
            export_df[column] = export_df[column].map(repair_text)

    saved_as_parquet = False
    try:
        export_df.to_parquet(ACTIVE_LIST_PARQUET, index=False)
        saved_as_parquet = True
        if ACTIVE_LIST_CSV.exists():
            ACTIVE_LIST_CSV.unlink()
    except Exception:
        export_df.to_csv(ACTIVE_LIST_CSV, index=False, encoding="utf-8-sig")
        if ACTIVE_LIST_PARQUET.exists():
            ACTIVE_LIST_PARQUET.unlink()

    if saved_as_parquet or ACTIVE_LIST_CSV.exists():
        save_active_session_metadata()


def _read_active_list_file() -> pd.DataFrame | None:
    if ACTIVE_LIST_PARQUET.exists():
        try:
            return pd.read_parquet(ACTIVE_LIST_PARQUET)
        except Exception:
            pass

    if ACTIVE_LIST_CSV.exists():
        try:
            return pd.read_csv(ACTIVE_LIST_CSV, encoding="utf-8-sig")
        except Exception:
            pass

    return None


def _load_active_session_metadata() -> dict:
    if not ACTIVE_SESSION_PATH.exists():
        return {}
    try:
        with ACTIVE_SESSION_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def restore_active_list_if_available() -> bool:
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
    page_size = meta.get("page_size", 25)
    selected_filter = meta.get("selected_filter", meta.get("filter_key", "all"))

    st.session_state.citizens_df = df.reset_index(drop=True)
    st.session_state.list_key = meta.get("list_key")
    st.session_state.source_filename = meta.get("source_filename") or "borgerliste"
    st.session_state.page_number = int(meta.get("page_number", 0))
    st.session_state.page_size = page_size if page_size in PAGE_SIZE_OPTIONS else 25
    st.session_state.selected_filter = selected_filter if selected_filter in FILTER_KEYS else "all"
    st.session_state.search_query = str(meta.get("search_query", ""))
    st.session_state.show_uploader = bool(meta.get("show_uploader", False))
    st.session_state.filter_signature = None
    st.session_state.session_restored = True
    sync_history_from_dataframe(st.session_state.citizens_df)
    return True


def clear_active_list() -> None:
    for path in (ACTIVE_LIST_PARQUET, ACTIVE_LIST_CSV, ACTIVE_SESSION_PATH):
        if path.exists():
            path.unlink()

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


def to_excel_bytes(df: pd.DataFrame) -> bytes:
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
        export_df[column] = export_df[column].map(repair_text)
    export_df["Status"] = export_df["Status"].map(lambda s: status_label(s, short=False))
    export_df = export_df.rename(columns=column_names)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name=t("sheet_name"))
        worksheet = writer.sheets[t("sheet_name")]
        for idx, column in enumerate(export_df.columns, start=1):
            max_len = max([len(str(column))] + [len(str(value)) for value in export_df[column].head(200)])
            col_letter = worksheet.cell(row=1, column=idx).column_letter
            worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)

    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


DEFAULT_MASTER_DELETE_PASSWORD = "Linkin24"


def get_required_password() -> str | None:
    """Valgfri adgangskode til fuld app-login (kun hvis BORGERLISTE_PASSWORD er sat)."""
    env_password = os.environ.get("BORGERLISTE_PASSWORD", "").strip()
    if env_password:
        return env_password
    return None


def get_master_delete_password() -> str:
    """Adgangskode der kræves ved sletning af master-registeret."""
    env_password = os.environ.get("BORGERLISTE_MASTER_DELETE_PASSWORD", "").strip()
    if env_password:
        return env_password
    try:
        secret_password = str(st.secrets.get("master_delete_password", "")).strip()
        if secret_password:
            return secret_password
        secret_password = str(st.secrets.get("password", "")).strip()
        if secret_password:
            return secret_password
    except Exception:
        pass
    return DEFAULT_MASTER_DELETE_PASSWORD


def verify_master_delete_password(password: str) -> bool:
    return password == get_master_delete_password()


def render_login() -> bool:
    required = get_required_password()
    if not required:
        st.session_state.authenticated = True
        return True

    if st.session_state.get("authenticated"):
        return True

    st.markdown(f"## {t('login_title')}")
    st.caption(t("login_caption"))

    with st.form("login_form"):
        password = st.text_input(t("login_password"), type="password")
        submitted = st.form_submit_button(t("login_submit"), type="primary", use_container_width=True)

    if submitted:
        if password == required:
            st.session_state.authenticated = True
            st.rerun()
        st.error(t("login_error"))

    return False


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def status_pill_html(status: str, short: bool = True) -> str:
    pill_class = STATUS_PILL_CLASS.get(status, "status-pill--neutral")
    label = status_label(status, short=short)
    return f'<span class="status-pill {pill_class}">{label}</span>'


def citizen_field_html(label: str, value: object, *, emphasized: bool = False) -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(str(value))
    emphasis_class = " citizen-field-value--emphasis" if emphasized else ""
    return (
        f'<div class="citizen-field">'
        f'<span class="citizen-field-label">{safe_label}</span>'
        f'<span class="citizen-field-value{emphasis_class}">{safe_value}</span>'
        f"</div>"
    )


def _status_pill_css(scheme: str) -> str:
    if scheme == "dark":
        return """
.status-pill {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.status-pill--neutral {
    background: #334155 !important;
    color: #E2E8F0 !important;
    border-color: #64748B !important;
}
.status-pill--accepted {
    background: #14532D !important;
    color: #BBF7D0 !important;
    border-color: #22C55E !important;
}
.status-pill--declined {
    background: #7F1D1D !important;
    color: #FECACA !important;
    border-color: #EF4444 !important;
}
.status-pill--call-again {
    background: #78350F !important;
    color: #FDE68A !important;
    border-color: #F59E0B !important;
}
.status-pill--all {
    background: #312E81 !important;
    color: #E0E7FF !important;
    border-color: #6366F1 !important;
}
"""
    return """
.status-pill {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    border: 1px solid transparent;
}
.status-pill--neutral {
    background: #F1F5F9 !important;
    color: #475569 !important;
    border-color: #CBD5E1 !important;
}
.status-pill--accepted {
    background: #DCFCE7 !important;
    color: #15803D !important;
    border-color: #86EFAC !important;
}
.status-pill--declined {
    background: #FEE2E2 !important;
    color: #B91C1C !important;
    border-color: #FCA5A5 !important;
}
.status-pill--call-again {
    background: #FEF3C7 !important;
    color: #B45309 !important;
    border-color: #FCD34D !important;
}
.status-pill--all {
    background: #EEF2FF !important;
    color: #3730A3 !important;
    border-color: #C7D2FE !important;
}
"""


def _btn_secondary_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button[kind=\"secondary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-secondary\"], "
        f"{prefix}.stButton button[kind=\"secondary\"]"
    )


def _btn_primary_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button[kind=\"primary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-primary\"], "
        f"{prefix}.stButton button[kind=\"primary\"]"
    )


def _btn_any_selector(scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return (
        f"{prefix}.stButton > button, "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-secondary\"], "
        f"{prefix}.stButton button[data-testid=\"stBaseButton-primary\"], "
        f"{prefix}.stButton button[kind=\"secondary\"], "
        f"{prefix}.stButton button[kind=\"primary\"]"
    )


def _overview_columns_selector() -> str:
    return (
        '[data-testid="stElementContainer"]:has(#kpi-overview-anchor) + '
        '[data-testid="stLayoutWrapper"] [data-testid="stColumn"]'
    )


def _overview_filter_button_selector(suffix: str = "") -> str:
    return _btn_any_selector(f"{_overview_columns_selector()}{suffix}")


def _kpi_filter_active_color_rules(theme_prefix: str) -> str:
    rules: list[str] = []
    for index, (_filter_key, color) in enumerate(FILTER_ACTIVE_COLORS.items(), start=1):
        column = f"{_overview_columns_selector()}:nth-child({index})"
        primary_btns = _btn_primary_selector(column)
        rules.append(
            f"""
{theme_prefix} {primary_btns} {{
    background-color: {color} !important;
    color: #FFFFFF !important;
    border: 1px solid {color} !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}
{theme_prefix} {column}:has(button[kind="primary"]) div[data-testid="stVerticalBlockBorderWrapper"],
{theme_prefix} {column}:has(button[data-testid="stBaseButton-primary"]) div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 2px solid {color} !important;
    box-shadow: 0 0 0 3px {color}33 !important;
}}
"""
        )
    return "\n".join(rules)


def _light_theme_overrides_css() -> str:
    col_sel = _overview_columns_selector()
    overview_buttons = _overview_filter_button_selector()
    overview_secondary = _btn_secondary_selector(f".light-theme {col_sel}")
    active_rules = _kpi_filter_active_color_rules(".light-theme")
    return f"""
.light-theme {{
    color-scheme: light !important;
}}

{overview_secondary} {{
    background-color: #FFFFFF !important;
    color: #1F2937 !important;
    border: 1px solid #D1D5DB !important;
    -webkit-text-fill-color: #1F2937 !important;
}}

.light-theme {overview_buttons} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    box-shadow: none !important;
}}

.light-theme div[data-testid="stTextInput"] input,
.light-theme div[data-baseweb="input"] input {{
    background-color: #FFFFFF !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    border: 1px solid #9CA3AF !important;
    caret-color: #111827 !important;
}}

.light-theme div[data-testid="stTextInput"] input::placeholder,
.light-theme div[data-baseweb="input"] input::placeholder {{
    color: #6B7280 !important;
    -webkit-text-fill-color: #6B7280 !important;
    opacity: 1 !important;
}}

{active_rules}
"""


def _light_theme_tooltip_css() -> str:
    return """
div[data-baseweb="tooltip"] > div,
div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) > div,
div[data-baseweb="popover"]:has(.stTooltipContent) > div,
div[role="tooltip"],
div[role="tooltip"] > div {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12) !important;
}

div[data-baseweb="tooltip"],
div[role="tooltip"] {
    color: #111827 !important;
}

[data-testid="stTooltipContent"],
.stTooltipContent,
[data-testid="stTooltipContent"] *,
.stTooltipContent *,
div[data-baseweb="tooltip"] *,
div[role="tooltip"] * {
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}
"""


def _dark_theme_overrides_css() -> str:
    col_sel = _overview_columns_selector()
    overview_buttons = _overview_filter_button_selector()
    overview_secondary = _btn_secondary_selector(f".dark-theme {col_sel}")
    active_rules = _kpi_filter_active_color_rules(".dark-theme")
    return f"""
.dark-theme {{
    color-scheme: dark !important;
}}

{overview_secondary} {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}

.dark-theme {overview_buttons} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    box-shadow: none !important;
}}

{active_rules}
"""


def _theme_dom_script(body: str) -> str:
    return f"""
(function () {{
  const doc = window.parent.document;
  const apply = () => {{
    const root = doc.querySelector(".stApp") || doc.body;
    if (!root) return false;
    {body}
    return true;
  }};
  if (apply()) return;
  const observer = new MutationObserver(() => {{
    if (apply()) observer.disconnect();
  }});
  observer.observe(doc.documentElement, {{ childList: true, subtree: true }});
  window.setTimeout(() => observer.disconnect(), 15000);
}})();
"""


def _theme_class_bootstrap(theme_choice: str) -> str:
    if theme_choice == "Lyst tema":
        return _theme_dom_script("""
    root.classList.remove("dark-theme");
    root.classList.add("light-theme");
""")
    if theme_choice == "Mørkt tema":
        return _theme_dom_script("""
    root.classList.remove("light-theme");
    root.classList.add("dark-theme");
""")
    return _theme_dom_script("""
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.classList.remove("light-theme", "dark-theme");
    root.classList.add(dark ? "dark-theme" : "light-theme");
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    if (!window.__borgerlisteThemeListener) {
      media.addEventListener("change", () => {
        const isDark = media.matches;
        root.classList.remove("light-theme", "dark-theme");
        root.classList.add(isDark ? "dark-theme" : "light-theme");
      });
      window.__borgerlisteThemeListener = true;
    }
""")


def _inject_theme_class(theme_choice: str) -> None:
    script = _theme_class_bootstrap(theme_choice)
    components.html(f"<script>{script}</script>", height=0, width=0)


def _dropdown_css(scheme: str) -> str:
    if scheme == "light":
        return """
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
div[data-baseweb="menu"] ul,
ul[role="listbox"],
li[role="option"] {
    background-color: #FFFFFF !important;
    color: #111827 !important;
}

div[data-baseweb="popover"] span,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] li span,
li[role="option"] span,
li[role="option"] p {
    color: #111827 !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"],
li[role="option"]:focus,
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] li[aria-selected="true"],
div[data-baseweb="menu"] li:focus {
    background-color: #F3F4F6 !important;
    color: #111827 !important;
}

li[role="option"]:hover span,
li[role="option"][aria-selected="true"] span,
div[data-baseweb="menu"] li:hover span,
div[data-baseweb="menu"] li[aria-selected="true"] span {
    color: #111827 !important;
}
"""
    return """
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"],
div[data-baseweb="menu"] ul,
ul[role="listbox"],
li[role="option"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
}

div[data-baseweb="popover"] span,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] li span,
li[role="option"] span,
li[role="option"] p {
    color: #F8FAFC !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"],
li[role="option"]:focus,
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] li[aria-selected="true"],
div[data-baseweb="menu"] li:focus {
    background-color: #334155 !important;
    color: #F8FAFC !important;
}

li[role="option"]:hover span,
li[role="option"][aria-selected="true"] span,
div[data-baseweb="menu"] li:hover span,
div[data-baseweb="menu"] li[aria-selected="true"] span {
    color: #F8FAFC !important;
}
"""


def _wrap_media(css: str, media: str | None) -> str:
    if not media:
        return css
    return f"@media {media} {{\n{css}\n}}"


def _base_css_rules(browse_label: str) -> str:
    """Layout, upload-i18n og diskrete sidebar-knapper — bruges i alle temaer."""
    safe_label = browse_label.replace("\\", "\\\\").replace('"', '\\"')
    return f"""
.block-container {{
    max-width: 920px;
    padding-top: 1.25rem;
    padding-bottom: 2rem;
}}

.status-pill {{
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
}}

.citizen-field {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0.65rem;
    margin: 0.2rem 0 0.55rem 0;
    line-height: 1.45;
}}

.citizen-field-label {{
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--app-text-muted, rgba(255, 255, 255, 0.65));
    min-width: 6.75rem;
    flex: 0 0 auto;
}}

.citizen-field-value {{
    font-size: 0.95rem;
    color: var(--app-text, inherit);
    flex: 1 1 auto;
    word-break: break-word;
}}

.citizen-field-value--emphasis {{
    font-weight: 700;
    font-size: 1.02rem;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 0.5rem 0 1rem 0;
}}

.kpi-card {{
    background: var(--app-card-bg, #FFFFFF);
    border: 1px solid var(--app-card-border-subtle, rgba(0,0,0,0.08));
    box-shadow: var(--app-card-shadow, 0 1px 3px rgba(0,0,0,0.05));
    border-radius: 10px;
    padding: 0.85rem 0.6rem;
    text-align: center;
    min-width: 0;
}}

.kpi-number {{
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    margin: 0.45rem 0 0 0;
    color: var(--app-text, #1C1917);
}}

.kpi-overview-card {{
    text-align: center;
    padding: 0.15rem 0;
}}

.kpi-overview-card .kpi-number {{
    margin-top: 0.45rem;
}}

{_overview_columns_selector()} {{
    min-width: 0;
}}

{_overview_filter_button_selector()} {{
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    padding: 0 0.45rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1.1 !important;
    margin-top: 0.35rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: none !important;
}}

@media (max-width: 1024px) {{
    {_overview_columns_selector()} {{
        flex: 1 1 33% !important;
        min-width: 30% !important;
    }}
}}

@media (max-width: 768px) {{
    .kpi-overview-card .kpi-number {{
        font-size: 1.55rem;
    }}

    {_overview_filter_button_selector()} {{
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        font-size: 0.78rem !important;
    }}
}}

.metric-number {{
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 0;
}}

.page-info {{
    text-align: center;
    padding-top: 0.6rem;
    font-size: 0.95rem;
    line-height: 1.4;
}}

.upload-hint {{
    text-align: center;
    padding: 0.75rem 0 0.25rem 0;
    font-size: 0.92rem;
}}

[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stFileUploader"] small {{
    display: none !important;
}}

[data-testid="stFileUploader"] button {{
    font-size: 0 !important;
}}

[data-testid="stFileUploader"] button::after {{
    content: "{safe_label}";
    font-size: 0.9rem !important;
}}

.theme-mini [data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    gap: 0.2rem !important;
}}

.theme-mini [data-testid="column"] {{
    min-width: 0 !important;
}}

.theme-mini .stButton > button {{
    background: transparent !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    box-shadow: none !important;
    min-height: 2.1rem !important;
    padding: 0.15rem !important;
    font-size: 1rem !important;
    color: var(--app-text, #1C1917) !important;
    opacity: 0.6;
}}

.theme-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.1) !important;
    border-color: {PRIMARY_COLOR} !important;
    opacity: 1;
}}

.lang-mini .stButton > button {{
    min-height: 2.2rem !important;
    font-size: 1.05rem !important;
    background: transparent !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    box-shadow: none !important;
    color: var(--app-text, #1C1917) !important;
}}

.lang-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.1) !important;
    border-color: {PRIMARY_COLOR} !important;
}}

@media (max-width: 1024px) {{
    .kpi-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}

@media (max-width: 768px) {{
    .block-container {{
        padding-left: 0.65rem;
        padding-right: 0.65rem;
    }}

    .kpi-grid {{
        grid-template-columns: 1fr;
        gap: 0.55rem;
    }}

    .kpi-card {{
        padding: 0.75rem 0.65rem;
    }}

    .kpi-number {{
        font-size: 1.65rem;
    }}

    .stButton > button,
    .stDownloadButton > button,
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stTextInput"] input {{
        min-height: 2.85rem !important;
        font-size: 1rem !important;
    }}

    .metric-number {{
        font-size: 1.5rem;
    }}
}}
"""


def _themed_css_rules(
    palette: dict[str, str],
    button_secondary_bg: str,
    media: str | None = None,
) -> str:
    """Nordic Light eller mørkt tema — tilpassede farver og kontraster."""
    card_shadow = palette.get("card_shadow", "none")
    card_border_subtle = palette.get("card_border_subtle", palette["border"])
    btn_secondary = _btn_secondary_selector()
    btn_primary = _btn_primary_selector()
    rules = f"""
:root {{
    color-scheme: {palette["color_scheme"]};
    --app-bg: {palette["bg"]};
    --app-bg-secondary: {palette["bg_secondary"]};
    --app-card-bg: {palette["card_bg"]};
    --app-input-bg: {palette["input_bg"]};
    --app-text: {palette["text"]};
    --app-text-muted: {palette["text_muted"]};
    --app-border: {palette["border"]};
    --app-card-shadow: {card_shadow};
    --app-card-border-subtle: {card_border_subtle};
}}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stHeader"], .block-container {{
    background-color: var(--app-bg) !important;
    color: var(--app-text) !important;
}}

[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {{
    background-color: var(--app-bg-secondary) !important;
    color: var(--app-text) !important;
}}

h1, h2, h3, h4, h5, h6, p, label, li, strong,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp li, .stApp strong,
.stMarkdown, .stMarkdown p, .stCaption,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not(.status-pill), [data-testid="stRadio"] label,
.stApp span:not(.status-pill) {{
    color: var(--app-text) !important;
}}

.metric-number, .page-info, .page-info b, .upload-hint, .kpi-number {{
    color: var(--app-text) !important;
}}

div[data-testid="element-container"] div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"],
.kpi-card {{
    background: var(--app-card-bg) !important;
    border: 1px solid var(--app-card-border-subtle) !important;
    box-shadow: var(--app-card-shadow) !important;
}}

div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stMultiSelect"] div[data-baseweb="select"],
div[data-baseweb="input"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] {{
    background-color: var(--app-input-bg) !important;
    color: var(--app-text) !important;
    border: 1px solid var(--app-border) !important;
}}

{_dropdown_css(palette["color_scheme"])}

{_status_pill_css(palette["color_scheme"])}

{btn_secondary},
[data-testid="stFileUploader"] button {{
    border: 1px solid var(--app-border) !important;
    background-color: {button_secondary_bg} !important;
    color: var(--app-text) !important;
    box-shadow: none !important;
}}

{btn_primary},
.stDownloadButton > button,
div[data-testid="stFormSubmitButton"] > button {{
    background-color: {PRIMARY_COLOR} !important;
    color: {PRIMARY_TEXT} !important;
    border-color: {PRIMARY_COLOR} !important;
    box-shadow: none !important;
}}

.stButton > button:disabled,
.stButton button[data-testid="stBaseButton-secondary"]:disabled,
.stButton button[data-testid="stBaseButton-primary"]:disabled {{
    opacity: 0.45;
}}

section[data-testid="stFileUploaderDropzone"] {{
    background: var(--app-card-bg) !important;
    border: 1px dashed var(--app-border) !important;
}}

[data-testid="stFileUploader"] button::after {{
    color: var(--app-text) !important;
}}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border-color: var(--app-border) !important;
}}

[data-testid="stAlert"],
[data-testid="stNotification"] {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border-color: var(--app-border) !important;
}}

div[data-baseweb="select"] svg {{
    fill: var(--app-text) !important;
}}

.theme-mini .stButton > button,
.lang-mini .stButton > button {{
    background: transparent !important;
    border: 1px solid var(--app-border) !important;
    color: var(--app-text) !important;
}}

.theme-mini .stButton > button[kind="primary"],
.lang-mini .stButton > button[kind="primary"] {{
    background: rgba(37, 99, 235, 0.12) !important;
    border-color: {PRIMARY_COLOR} !important;
    color: var(--app-text) !important;
}}
"""
    return _wrap_media(rules, media)


def inject_styles(theme_choice: str) -> None:
    """Indsprøjter CSS i præcis én <style>-blok — aldrig synlig rå tekst."""
    css_parts = [_base_css_rules(t("upload_browse"))]

    if theme_choice == "Browser standard":
        light = THEME_PALETTES["Lyst tema"]
        dark = THEME_PALETTES["Mørkt tema"]
        css_parts.append(_themed_css_rules(light, light["input_bg"], media=None))
        css_parts.append(_themed_css_rules(dark, dark["input_bg"], media="(prefers-color-scheme: dark)"))
        css_parts.append(_light_theme_overrides_css())
        css_parts.append(_wrap_media(_light_theme_tooltip_css(), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_dark_theme_overrides_css(), "(prefers-color-scheme: dark)"))
    elif theme_choice in THEME_PALETTES:
        palette = THEME_PALETTES[theme_choice]
        is_light = theme_choice == "Lyst tema"
        button_secondary_bg = "#FFFFFF" if is_light else palette["input_bg"]
        css_parts.append(_themed_css_rules(palette, button_secondary_bg))
        if is_light:
            css_parts.append(_light_theme_overrides_css())
            css_parts.append(_light_theme_tooltip_css())
        else:
            css_parts.append(_dark_theme_overrides_css())

    css = "<style>\n" + "\n".join(css_parts) + "\n</style>"
    st.markdown(css, unsafe_allow_html=True)
    _inject_theme_class(theme_choice)


def render_language_settings() -> None:
    st.sidebar.caption(t("language"))
    col_da, col_en = st.sidebar.columns(2)
    current = lang()
    with col_da:
        if st.button("🇩🇰", key="lang_da", use_container_width=True, type="primary" if current == "da" else "secondary"):
            st.session_state.language = "da"
            save_user_preferences(language="da")
            st.rerun()
    with col_en:
        if st.button("🇬🇧", key="lang_en", use_container_width=True, type="primary" if current == "en" else "secondary"):
            st.session_state.language = "en"
            save_user_preferences(language="en")
            st.rerun()


def render_theme_settings() -> None:
    current = st.session_state.get("theme_choice", "Browser standard")
    st.sidebar.markdown('<div class="theme-mini">', unsafe_allow_html=True)
    col1, col2, col3 = st.sidebar.columns(3)
    for col, theme in zip((col1, col2, col3), THEME_OPTIONS):
        with col:
            if st.button(
                THEME_ICONS[theme],
                key=f"theme_btn_{theme}",
                use_container_width=True,
                type="primary" if theme == current else "secondary",
                help=theme_help(theme),
            ):
                st.session_state.theme_choice = theme
                save_user_preferences(theme_choice=theme)
                st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "list_key": None,
        "source_filename": None,
        "citizens_df": None,
        "page_number": 0,
        "page_size": 25,
        "selected_filter": "all",
        "search_query": "",
        "filter_signature": None,
        "show_uploader": True,
        "session_restored": False,
        "last_upload_match_count": None,
        "theme_choice": "Browser standard",
        "language": "da",
        "preferences_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.preferences_loaded:
        apply_saved_user_preferences()
        st.session_state.preferences_loaded = True

    if st.session_state.citizens_df is None:
        restore_active_list_if_available()


def filter_dataframe(df: pd.DataFrame, filter_key: str, search: str) -> pd.DataFrame:
    selected = FILTER_MAP.get(filter_key, STATUSES)
    filtered = df[df["Status"].isin(selected)].copy()
    if search.strip():
        needle = search.strip().lower()
        filtered = filtered[
            filtered["Navn"].str.lower().str.contains(needle, na=False)
            | filtered["Adresse"].str.lower().str.contains(needle, na=False)
            | filtered["Telefonnummer"].str.lower().str.contains(needle, na=False)
        ]
    return filtered.reset_index(drop=True)


def kpi_card_label(filter_value: str, status: str | None) -> str:
    if status:
        return status_label(status, short=True)
    return filter_label("all")


def render_overview_kpi_card(
    filter_value: str,
    status: str | None,
    count: int,
    selected: str,
) -> None:
    is_active = selected == filter_value
    with st.container(border=True):
        st.markdown('<div class="kpi-overview-card">', unsafe_allow_html=True)
        if status:
            st.markdown(status_pill_html(status, short=True), unsafe_allow_html=True)
        else:
            st.markdown(
                f'<span class="status-pill status-pill--all">{filter_label("all")}</span>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<p class="kpi-number">{count}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button(
        filter_button_label(filter_value),
        key=f"kpi_filter_{filter_value}",
        use_container_width=True,
        type="primary" if is_active else "secondary",
        help=t("overview_filter_hint"),
    ):
        if is_active and filter_value != "all":
            set_selected_filter("all")
        elif not is_active:
            set_selected_filter(filter_value)
        st.rerun()


def render_status_metrics(df: pd.DataFrame) -> None:
    counts = count_by_status(df)
    selected = st.session_state.get("selected_filter", "all")

    st.markdown(f"#### {t('overview')}")
    st.caption(t("overview_filter_hint"))
    st.markdown('<div id="kpi-overview-anchor"></div>', unsafe_allow_html=True)

    card_counts = {
        "all": len(df),
        **{STATUS_TO_FILTER[status]: counts[status] for status in STATUSES},
    }

    cols = st.columns(len(OVERVIEW_CARDS))
    for col, (filter_value, status) in zip(cols, OVERVIEW_CARDS):
        with col:
            render_overview_kpi_card(
                filter_value,
                status,
                card_counts[filter_value],
                selected,
            )


def handle_file_upload(uploaded) -> bool:
    try:
        raw_df, _detected_encoding = read_uploaded_file(uploaded)
        base_df = standardize_dataframe(raw_df)
        key = list_storage_key(uploaded.name, base_df)

        register = load_master_register()
        full_df, matched_count = apply_master_register_statuses(base_df, register)
        list_state = load_saved_state(key)
        if list_state:
            full_df = apply_saved_statuses(full_df, list_state)
        sync_master_register_from_dataframe(full_df)

        st.session_state.list_key = key
        st.session_state.source_filename = uploaded.name
        st.session_state.citizens_df = full_df
        st.session_state.last_upload_match_count = matched_count
        st.session_state.page_number = 0
        st.session_state.page_size = 25
        st.session_state.selected_filter = "all"
        st.session_state.search_query = ""
        st.session_state.filter_signature = None
        st.session_state.show_uploader = False
        st.session_state.session_restored = False
        save_state(key, dataframe_to_state(full_df))
        save_active_list(full_df)
        return True
    except Exception:
        st.error(t("upload_error"))
        return False


def render_upload_section() -> None:
    list_loaded = st.session_state.citizens_df is not None and not st.session_state.citizens_df.empty
    expanded = not list_loaded or st.session_state.show_uploader
    label = t("upload_expander_change") if list_loaded else t("upload_expander")

    with st.expander(label, expanded=expanded):
        if list_loaded and not st.session_state.show_uploader:
            matched = st.session_state.get("last_upload_match_count")
            if matched is not None:
                st.success(
                    t(
                        "upload_loaded_with_matches",
                        count=len(st.session_state.citizens_df),
                        matched=matched,
                    )
                )
            else:
                st.success(
                    t("upload_loaded", filename=st.session_state.source_filename, count=len(st.session_state.citizens_df))
                )
            if st.button(t("upload_select_new"), use_container_width=True):
                st.session_state.show_uploader = True
                st.rerun()
        else:
            st.caption(t("upload_hint_new") if list_loaded else t("upload_hint"))
            st.markdown(f"<p class='upload-hint'>{t('upload_drag_hint')}</p>", unsafe_allow_html=True)

            uploaded = st.file_uploader(
                t("upload_browse"),
                type=["csv", "xlsx", "xls"],
                label_visibility="collapsed",
            )
            if uploaded is not None and handle_file_upload(uploaded):
                st.success(t("upload_success", count=len(st.session_state.citizens_df)))
                st.rerun()

            if list_loaded and st.button(t("upload_keep_current"), use_container_width=True):
                st.session_state.show_uploader = False
                st.rerun()


def render_sidebar_settings() -> None:
    st.sidebar.divider()
    st.sidebar.markdown('<div class="lang-mini">', unsafe_allow_html=True)
    render_language_settings()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    render_theme_settings()


def render_master_register_sidebar() -> None:
    register = load_master_register()
    st.sidebar.caption(t("master_register_count", count=len(register)))

    with st.sidebar.expander(t("clear_master_register"), expanded=False):
        st.caption(t("master_delete_warning"))

        with st.form("master_delete_form", clear_on_submit=True):
            password = st.text_input(t("master_delete_password"), type="password")
            submitted = st.form_submit_button(t("master_delete_confirm"), use_container_width=True)
            if submitted:
                if verify_master_delete_password(password):
                    clear_master_register()
                    st.toast(t("master_register_cleared"), icon="✅")
                    st.rerun()
                else:
                    st.error(t("master_delete_password_error"))


def render_sidebar_content() -> None:
    with st.sidebar.expander(t("gdpr_title"), expanded=False):
        st.markdown(t("gdpr_text"))

    st.sidebar.divider()
    render_master_register_sidebar()

    list_loaded = st.session_state.citizens_df is not None and not st.session_state.citizens_df.empty
    if not list_loaded:
        return

    if st.session_state.get("session_restored"):
        st.sidebar.caption(t("session_restored"))
        st.session_state.session_restored = False

    if st.sidebar.button(t("clear_saved_list"), use_container_width=True):
        clear_active_list()
        st.rerun()

    st.sidebar.divider()
    export_name = Path(st.session_state.source_filename or "borgerliste").stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.sidebar.download_button(
        label=t("export_excel"),
        data=to_excel_bytes(st.session_state.citizens_df),
        file_name=f"{export_name}_opdateret_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def resolve_page_size(selected: int | str, total_rows: int) -> int:
    if selected == "Alle":
        return max(total_rows, 1)
    return int(selected)


def render_pagination_bar(total_rows: int, page_size: int, page_number: int) -> tuple[int, int, int]:
    total_pages = max(1, (total_rows + page_size - 1) // page_size) if total_rows else 1
    page_number = min(max(page_number, 0), total_pages - 1)
    start = page_number * page_size
    end = min(start + page_size, total_rows)

    if total_pages > 1:
        nav_prev, nav_info, nav_next = st.columns([1, 2.2, 1])

        with nav_prev:
            if st.button(t("prev"), disabled=page_number <= 0, use_container_width=True):
                st.session_state.page_number = max(page_number - 1, 0)
                st.rerun()

        with nav_info:
            st.markdown(
                f"<div class='page-info'>{t('page_info', current=page_number + 1, total=total_pages)}</div>",
                unsafe_allow_html=True,
            )

        with nav_next:
            if st.button(t("next"), disabled=page_number >= total_pages - 1, use_container_width=True):
                st.session_state.page_number = min(page_number + 1, total_pages - 1)
                st.rerun()

    size_cols = st.columns([1, 1.2, 1])
    with size_cols[1]:
        page_size_choice = st.selectbox(
            t("page_size_label"),
            PAGE_SIZE_OPTIONS,
            index=PAGE_SIZE_OPTIONS.index(st.session_state.page_size)
            if st.session_state.page_size in PAGE_SIZE_OPTIONS
            else 1,
            format_func=page_size_label,
        )
        if page_size_choice != st.session_state.page_size:
            st.session_state.page_size = page_size_choice
            st.session_state.page_number = 0
            st.rerun()

    st.session_state.page_number = page_number
    return start, end, page_number


def render_citizen_card(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(status_pill_html(row["Status"], short=True), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_name"), row["Navn"], emphasized=True), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_address"), row["Adresse"]), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_phone"), row["Telefonnummer"]), unsafe_allow_html=True)

        current_index = STATUSES.index(row["Status"]) if row["Status"] in STATUSES else 0
        new_status = st.selectbox(
            t("change_status"),
            STATUSES,
            index=current_index,
            key=f"status_{row['_id']}",
            format_func=lambda s: status_label(s, short=True),
        )

        if row["Status dato"]:
            st.caption(t("last_updated", date=row["Status dato"]))
        if row["Ring igen dato"]:
            st.caption(t("call_again_date", date=row["Ring igen dato"]))

        if new_status != row["Status"]:
            updated = update_citizen_status(st.session_state.citizens_df, row["_id"], new_status)
            st.session_state.citizens_df = updated
            save_state(st.session_state.list_key, dataframe_to_state(updated))
            updated_row = updated[updated["_id"] == row["_id"]].iloc[0]
            register = load_master_register()
            upsert_master_register_entry(updated_row, register)
            save_master_register(register, cleared=False)
            history = load_status_history()
            upsert_history_entry(updated_row, history)
            save_status_history(history)
            save_active_list(updated)
            st.toast(t("status_saved"), icon="✅")
            st.rerun()


def render_citizen_list(page_slice: pd.DataFrame) -> None:
    if page_slice.empty:
        st.info(t("no_citizens_match"))
        return

    for _, row in page_slice.iterrows():
        render_citizen_card(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    init_session_state()
    st.set_page_config(
        page_title=t("app_title"),
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="auto",
    )
    inject_styles(st.session_state.get("theme_choice", "Browser standard"))

    st.sidebar.title(t("menu"))

    if not render_login():
        render_sidebar_settings()
        return

    render_sidebar_content()
    render_sidebar_settings()

    df = st.session_state.citizens_df
    if df is None or df.empty:
        st.title(t("app_title"))
        st.caption(t("app_subtitle"))
        render_upload_section()
        st.info(t("upload_get_started"))
        return

    st.title(t("app_title"))
    render_upload_section()

    render_status_metrics(df)

    st.markdown("---")
    search = st.text_input(
        t("search_placeholder"),
        key="search_query",
        placeholder=t("search_placeholder"),
        label_visibility="collapsed",
    )
    selected_filter = st.session_state.get("selected_filter", "all")
    filtered_df = filter_dataframe(df, selected_filter, search)
    st.caption(t("citizens_summary", total=len(df), shown=len(filtered_df)))

    filter_signature = f"{selected_filter}|{search.strip().lower()}"
    if st.session_state.filter_signature != filter_signature:
        st.session_state.filter_signature = filter_signature
        st.session_state.page_number = 0

    st.markdown(f"#### {t('citizens_heading')}")
    page_size = resolve_page_size(st.session_state.page_size, len(filtered_df))
    start, end, _page_number = render_pagination_bar(len(filtered_df), page_size, st.session_state.page_number)

    render_citizen_list(filtered_df.iloc[start:end])
    save_active_session_metadata()


if __name__ == "__main__":
    main()
