"""
Borgerliste – Streamlit-værktøj til opfølgning på borgerkontakt.
Understøtter lokal kørsel og Docker-server med valgfri adgangskode.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import html
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

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet, InvalidToken

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("BORGERLISTE_DATA_DIR", APP_ROOT / "data"))
LOGO_PATH = APP_ROOT / "assets" / "borgerliste-logo.svg"
STATUS_HISTORY_PATH = DATA_DIR / "status_history.json"
MASTER_REFERENCE_REGISTER_PATH = DATA_DIR / "master_reference_register.json"
USER_PREFERENCES_PATH = DATA_DIR / "user_preferences.json"
USERS_PATH = DATA_DIR / "users.json"
AUDIT_LOG_PATH = DATA_DIR / "audit_log.json"
USER_DATA_ROOT = DATA_DIR / "user_data"
LEGACY_ACTIVE_LIST_PARQUET = DATA_DIR / "active_borgerliste.parquet"
LEGACY_ACTIVE_LIST_CSV = DATA_DIR / "active_borgerliste.csv"
LEGACY_ACTIVE_SESSION_PATH = DATA_DIR / "active_session.json"
USER_ROLES = ("admin", "user")
MAX_AUDIT_ENTRIES = 10000
DEFAULT_ADMIN_USERNAME = "admin"
MIN_PASSWORD_LENGTH = 12
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{2,32}$")
LOGIN_ATTEMPTS_PATH = DATA_DIR / "login_attempts.json"
BOOTSTRAP_ADMIN_PATH = DATA_DIR / ".admin_bootstrap.txt"
AUTH_SESSIONS_PATH = DATA_DIR / "auth_sessions.json"
APP_SETTINGS_PATH = DATA_DIR / "app_settings.json"
SESSION_COOKIE_NAME = "borgerliste_session"
DEFAULT_SESSION_IDLE_MINUTES = 24 * 60
DEFAULT_SESSION_MAX_DAYS = 30
MIN_SESSION_IDLE_MINUTES = 1
MAX_SESSION_IDLE_MINUTES = 168 * 60
COOKIE_MANAGER_KEY = "borgerliste_cookie_manager"
COOKIE_MANAGER_INSTANCE_KEY = "_borgerliste_cookie_manager_instance"
DATA_LOCK_PATH = DATA_DIR / ".data.lock"
MASTER_SYNC_STAMP_PATH = DATA_DIR / ".master_sync_at"
MASTER_SYNC_INTERVAL_SECONDS = 60
APP_VERSION = "1.2.1"
SIDEBAR_AUTO_COLLAPSE_SECONDS = 10
PASSWORD_HASH_ITERATIONS = 120_000
PII_FIELDS = ("Navn", "Adresse", "Telefonnummer")
PII_ENC_PREFIX = "enc:v1:"
ENCRYPTION_KEY_PATH = DATA_DIR / ".encryption_key"
DEFAULT_RETENTION_MONTHS = 24
MIN_RETENTION_MONTHS = 0
MAX_RETENTION_MONTHS = 120

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
        "gdpr_title": "Privatliv og datasikkerhed",
        "gdpr_text": (
            "Borgerdata gemmes krypteret lokalt på denne enhed eller server. "
            "Del ikke filer med personoplysninger uden for jeres sikre kanaler."
        ),
        "gdpr_purpose": "**Formål:** Opfølgning på borgerkontakt (navn, adresse, telefon og kontaktstatus).",
        "gdpr_legal_basis": (
            "**Behandlingsgrundlag:** Behandles af den dataansvarlige organisation "
            "(typisk offentlig opgave eller legitim interesse). Appen indsamler ikke samtykke direkte fra borgere."
        ),
        "gdpr_data_types": "**Data:** Navn, adresse, telefonnummer og kontaktstatus. CPR behandles ikke.",
        "gdpr_rights": (
            "**Dine rettigheder:** Indsigt, berigtigelse, sletning og dataportabilitet kan håndteres "
            "via eksport/sletning pr. borger og kontakt til jeres dataansvarlige."
        ),
        "gdpr_retention_info": "**Opbevaring:** Borgerdata slettes automatisk efter den konfigurerede periode uden aktivitet.",
        "gdpr_security_info": (
            "**Sikkerhed:** Adgangskontrol, kryptering i hvile, sessionsstyring og audit-log. "
            "Brug HTTPS i produktion (`BORGERLISTE_COOKIE_SECURE=true`)."
        ),
        "gdpr_shared_register": (
            "**Delt statusregister:** Autoriserede brugere deler kontaktstatus via et fælles master-register "
            "for at genkende borgere på tværs af lister."
        ),
        "gdpr_contact": "**Kontakt:** Henvendelser om persondata rettes til jeres dataansvarlige organisation.",
        "gdpr_citizen_title": "Borgerrettigheder",
        "gdpr_erase_citizen": "Slet borger",
        "gdpr_erase_confirm": "Bekræft sletning",
        "gdpr_erase_cancel": "Annuller",
        "gdpr_erase_warning": "Sletter permanent alle data om denne borger. Kan ikke fortrydes.",
        "gdpr_erase_done": "Borger slettet.",
        "gdpr_export_citizen": "Eksporter data (JSON)",
        "gdpr_export_filename": "borger_{citizen_id}.json",
        "account_activity_tab": "Min aktivitet",
        "account_admin_gdpr_tab": "GDPR",
        "admin_retention_title": "Dataopbevaring",
        "admin_retention_label": "Slet inaktive borgere efter (måneder)",
        "admin_retention_help": "0 = deaktiveret. Standard: 24 måneder uden statusaktivitet.",
        "admin_retention_saved": "Opbevaringsperiode gemt.",
        "admin_retention_invalid": "Angiv et helt tal mellem {min} og {max}.",
        "admin_retention_current": "Nuværende: {months} måneder (0 = deaktiveret).",
        "admin_retention_disabled": "Automatisk sletning er deaktiveret.",
        "admin_retention_purged": "{count} inaktive borgere blev slettet ved login.",
        "admin_deactivate_delete_data": "Slet brugerens gemte data",
        "admin_user_deactivated_data_deleted": "Bruger {username} deaktiveret og data slettet.",
        "admin_audit_col_id": "Borger-ID",
        "admin_gdpr_processing_title": "Behandlingsfortegnelse (Art. 30)",
        "admin_gdpr_processing_body": (
            "| Punkt | Beskrivelse |\n"
            "|---|---|\n"
            "| Behandlingsaktivitet | Opfølgning på borgerkontakt |\n"
            "| Kategorier af registrerede | Borgere på kontaktliste |\n"
            "| Kategorier af personoplysninger | Navn, adresse, telefon, kontaktstatus |\n"
            "| Modtagere | Autoriserede app-brugere i organisationen |\n"
            "| Overførsler til tredjelande | Ingen |\n"
            "| Opbevaring | Konfigurerbar (standard 24 mdr.) |\n"
            "| Tekniske foranstaltninger | Login, kryptering, adgangskontrol, audit-log |"
        ),
        "user_audit_title": "Min aktivitet",
        "user_audit_caption": "Dine seneste statusændringer.",
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

        "login_username": "Brugernavn",
        "login_locked_out": "For mange mislykkede forsøg. Prøv igen om {minutes} min.",
        "login_session_expired": "Din session er udløbet. Log ind igen.",
        "session_valid_for": "Session aktiv i op til {minutes} min. ved inaktivitet.",
        "bootstrap_admin_notice": "Første admin er oprettet. Se {path} for midlertidig adgangskode.",
        "upload_too_large": "Filen er for stor (maks. {max_mb} MB).",
        "role_admin": "Administrator",
        "role_user": "Bruger",
        "logout": "Log ud",
        "logged_in_as": "Logget ind som {username} ({role})",
        "changed_by": "Sidst ændret af {username} ({timestamp})",
        "nav_borgerliste": "Borgerliste",
        "nav_account": "Min konto",
        "nav_privacy": "Privatliv og datasikkerhed",
        "sidebar_pin": "Fastgør menuen, så den ikke lukker automatisk",
        "sidebar_unpin": "Menu fastgjort — klik for at frigøre",
        "account_title": "Min konto",
        "account_profile_tab": "Profil",
        "account_admin_users_tab": "Brugere",
        "account_admin_master_tab": "Master-register",
        "account_admin_audit_tab": "Status-log",
        "account_username_label": "Brugernavn",
        "account_role_label": "Rolle",
        "account_created_label": "Oprettet",
        "account_change_password_title": "Skift adgangskode",
        "account_password_hint": "Adgangskoden skal være mindst {min} tegn.",
        "account_current_password": "Nuværende adgangskode",
        "account_new_password": "Ny adgangskode",
        "account_confirm_password": "Bekræft ny adgangskode",
        "account_password_submit": "Gem ny adgangskode",
        "account_password_mismatch": "Adgangskoderne matcher ikke.",
        "account_password_wrong": "Forkert nuværende adgangskode.",
        "account_password_updated": "Adgangskode opdateret.",
        "admin_users_title": "Brugere",
        "admin_create_user": "Opret bruger",
        "admin_new_username": "Brugernavn",
        "admin_new_password": "Adgangskode",
        "admin_new_role": "Rolle",
        "admin_create_submit": "Opret",
        "admin_users_list": "Eksisterende brugere",
        "admin_no_users": "Ingen brugere endnu.",
        "admin_deactivate": "Deaktiver",
        "admin_cannot_deactivate_self": "Du kan ikke deaktivere din egen konto.",
        "admin_user_created": "Bruger {username} er oprettet.",
        "admin_user_deactivated": "Bruger {username} er deaktiveret.",
        "admin_user_exists": "Brugernavnet findes allerede.",
        "admin_user_invalid": "Udfyld brugernavn og adgangskode (min. {min} tegn).",
        "admin_username_invalid": "Brugernavn skal være 2–32 tegn og må kun indeholde bogstaver, tal, _ og -.",
        "admin_password_weak": "Adgangskoden skal være mindst {min} tegn.",
        "admin_reset_password": "Nulstil adgangskode",
        "admin_reset_password_for": "Ny adgangskode for {username}",
        "admin_password_reset_done": "Adgangskode nulstillet for {username}.",
        "account_admin_settings_tab": "Indstillinger",
        "admin_session_title": "Session og inaktivitet",
        "admin_session_idle_label": "Log ud efter inaktivitet (minutter)",
        "admin_session_idle_help": (
            "Brugere logges automatisk ud efter denne periode uden aktivitet i appen. "
            "Gælder alle brugere."
        ),
        "admin_session_idle_saved": "Session-indstilling gemt.",
        "admin_session_idle_invalid": "Angiv et helt tal mellem {min} og {max} minutter.",
        "admin_session_current": "Nuværende grænse: {minutes} min. ved inaktivitet.",
        "admin_session_save": "Gem indstilling",
        "admin_audit_title": "Status-log",
        "admin_audit_caption": "Seneste statusændringer på tværs af brugere.",
        "admin_audit_empty": "Ingen logposter endnu.",
        "admin_audit_all_users": "Alle brugere",
        "admin_audit_filter_user": "Filtrer bruger",
        "admin_audit_filter_citizen": "Filtrer borger",
        "admin_audit_col_time": "Tidspunkt",
        "admin_audit_col_user": "Bruger",
        "admin_audit_col_citizen": "Borger",
        "admin_audit_col_from": "Fra",
        "admin_audit_col_to": "Til",
        "master_admin_description": "Master-registeret samler statusser fra alle brugeres lister.",
        "master_delete_admin_only": "Kun administratorer kan slette master-registeret.",
        "master_delete_not_configured": "Kun administratorer kan slette master-registeret.",
        "login_title": "Log ind",
        "login_caption": "Log ind for at beskytte borgerdata.",
        "login_password": "Adgangskode",
        "login_submit": "Log ind",
        "login_error": "Forkert brugernavn eller adgangskode.",
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
            "Kun administratorer kan udføre dette. Det sletter master-registeret, alle brugeres "
            "gemte lister og statusser. Appen starter forfra. Handlingen kan ikke fortrydes."
        ),
        "master_delete_password": "Bekræft med din admin-adgangskode",
        "master_delete_confirm": "Bekræft sletning",
        "master_delete_password_error": "Forkert admin-adgangskode.",
        "master_delete_password_required": (
            "Kun administratorer kan slette master-registeret."
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
        "gdpr_title": "Privacy and data security",
        "gdpr_text": (
            "Citizen data is stored encrypted locally on this device or server only. "
            "Do not share files containing personal data outside your secure channels."
        ),
        "gdpr_purpose": "**Purpose:** Follow-up on citizen contact (name, address, phone and contact status).",
        "gdpr_legal_basis": (
            "**Legal basis:** Processed by the data controller organisation "
            "(typically public task or legitimate interest). The app does not collect consent directly from citizens."
        ),
        "gdpr_data_types": "**Data:** Name, address, phone number and contact status. National ID (CPR) is not processed.",
        "gdpr_rights": (
            "**Your rights:** Access, rectification, erasure and portability can be handled "
            "via per-citizen export/erase and contact with your data controller."
        ),
        "gdpr_retention_info": "**Retention:** Citizen data is automatically deleted after the configured inactivity period.",
        "gdpr_security_info": (
            "**Security:** Access control, encryption at rest, session management and audit log. "
            "Use HTTPS in production (`BORGERLISTE_COOKIE_SECURE=true`)."
        ),
        "gdpr_shared_register": (
            "**Shared status register:** Authorised users share contact status via a common master register "
            "to recognise citizens across lists."
        ),
        "gdpr_contact": "**Contact:** Personal data enquiries should be directed to your data controller organisation.",
        "gdpr_citizen_title": "Citizen rights",
        "gdpr_erase_citizen": "Delete citizen",
        "gdpr_erase_confirm": "Confirm deletion",
        "gdpr_erase_cancel": "Cancel",
        "gdpr_erase_warning": "Permanently deletes all data about this citizen. Cannot be undone.",
        "gdpr_erase_done": "Citizen deleted.",
        "gdpr_export_citizen": "Export data (JSON)",
        "gdpr_export_filename": "citizen_{citizen_id}.json",
        "account_activity_tab": "My activity",
        "account_admin_gdpr_tab": "GDPR",
        "admin_retention_title": "Data retention",
        "admin_retention_label": "Delete inactive citizens after (months)",
        "admin_retention_help": "0 = disabled. Default: 24 months without status activity.",
        "admin_retention_saved": "Retention period saved.",
        "admin_retention_invalid": "Enter a whole number between {min} and {max}.",
        "admin_retention_current": "Current: {months} months (0 = disabled).",
        "admin_retention_disabled": "Automatic deletion is disabled.",
        "admin_retention_purged": "{count} inactive citizens were deleted at login.",
        "admin_deactivate_delete_data": "Delete user's stored data",
        "admin_user_deactivated_data_deleted": "User {username} deactivated and data deleted.",
        "admin_audit_col_id": "Citizen ID",
        "admin_gdpr_processing_title": "Processing record (Art. 30)",
        "admin_gdpr_processing_body": (
            "| Item | Description |\n"
            "|---|---|\n"
            "| Processing activity | Citizen contact follow-up |\n"
            "| Data subject categories | Citizens on contact list |\n"
            "| Personal data categories | Name, address, phone, contact status |\n"
            "| Recipients | Authorised app users in the organisation |\n"
            "| Transfers to third countries | None |\n"
            "| Retention | Configurable (default 24 mo.) |\n"
            "| Technical measures | Login, encryption, access control, audit log |"
        ),
        "user_audit_title": "My activity",
        "user_audit_caption": "Your recent status changes.",
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

        "login_username": "Username",
        "login_locked_out": "Too many failed attempts. Try again in {minutes} min.",
        "login_session_expired": "Your session has expired. Please sign in again.",
        "session_valid_for": "Session stays active for up to {minutes} min. of inactivity.",
        "bootstrap_admin_notice": "First admin created. See {path} for temporary password.",
        "upload_too_large": "File is too large (max {max_mb} MB).",
        "role_admin": "Administrator",
        "role_user": "User",
        "logout": "Sign out",
        "logged_in_as": "Signed in as {username} ({role})",
        "changed_by": "Last changed by {username} ({timestamp})",
        "nav_borgerliste": "Citizen list",
        "nav_account": "My account",
        "nav_privacy": "Privacy and data security",
        "sidebar_pin": "Pin menu to keep it open",
        "sidebar_unpin": "Menu pinned — click to unpin",
        "account_title": "My account",
        "account_profile_tab": "Profile",
        "account_admin_users_tab": "Users",
        "account_admin_master_tab": "Master register",
        "account_admin_audit_tab": "Status log",
        "account_username_label": "Username",
        "account_role_label": "Role",
        "account_created_label": "Created",
        "account_change_password_title": "Change password",
        "account_password_hint": "Password must be at least {min} characters.",
        "account_current_password": "Current password",
        "account_new_password": "New password",
        "account_confirm_password": "Confirm new password",
        "account_password_submit": "Save new password",
        "account_password_mismatch": "Passwords do not match.",
        "account_password_wrong": "Incorrect current password.",
        "account_password_updated": "Password updated.",
        "admin_users_title": "Users",
        "admin_create_user": "Create user",
        "admin_new_username": "Username",
        "admin_new_password": "Password",
        "admin_new_role": "Role",
        "admin_create_submit": "Create",
        "admin_users_list": "Existing users",
        "admin_no_users": "No users yet.",
        "admin_deactivate": "Deactivate",
        "admin_cannot_deactivate_self": "You cannot deactivate your own account.",
        "admin_user_created": "User {username} created.",
        "admin_user_deactivated": "User {username} deactivated.",
        "admin_user_exists": "Username already exists.",
        "admin_user_invalid": "Enter username and password (min. {min} characters).",
        "admin_username_invalid": "Username must be 2–32 characters and contain only letters, numbers, _ and -.",
        "admin_password_weak": "Password must be at least {min} characters.",
        "admin_reset_password": "Reset password",
        "admin_reset_password_for": "New password for {username}",
        "admin_password_reset_done": "Password reset for {username}.",
        "account_admin_settings_tab": "Settings",
        "admin_session_title": "Session and inactivity",
        "admin_session_idle_label": "Sign out after inactivity (minutes)",
        "admin_session_idle_help": (
            "Users are automatically signed out after this period without activity in the app. "
            "Applies to all users."
        ),
        "admin_session_idle_saved": "Session setting saved.",
        "admin_session_idle_invalid": "Enter a whole number between {min} and {max} minutes.",
        "admin_session_current": "Current limit: {minutes} min. of inactivity.",
        "admin_session_save": "Save setting",
        "admin_audit_title": "Status log",
        "admin_audit_caption": "Recent status changes across users.",
        "admin_audit_empty": "No log entries yet.",
        "admin_audit_all_users": "All users",
        "admin_audit_filter_user": "Filter user",
        "admin_audit_filter_citizen": "Filter citizen",
        "admin_audit_col_time": "Time",
        "admin_audit_col_user": "User",
        "admin_audit_col_citizen": "Citizen",
        "admin_audit_col_from": "From",
        "admin_audit_col_to": "To",
        "master_admin_description": "The master register collects statuses from all users' lists.",
        "master_delete_admin_only": "Only administrators can delete the master register.",
        "master_delete_not_configured": "Only administrators can delete the master register.",
        "login_title": "Sign in",
        "login_caption": "Sign in to protect citizen data.",
        "login_password": "Password",
        "login_submit": "Sign in",
        "login_error": "Incorrect username or password.",
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
            "Administrators only. This deletes the master register, all users' saved lists and "
            "statuses. The app starts fresh. This action cannot be undone."
        ),
        "master_delete_password": "Confirm with your admin password",
        "master_delete_confirm": "Confirm deletion",
        "master_delete_password_error": "Incorrect admin password.",
        "master_delete_password_required": (
            "Only administrators can delete the master register."
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
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        raw = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))
        df, encoding = read_csv_bytes(raw)
        return df, encoding
    if name.endswith((".xlsx", ".xls")):
        raw = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))
        df = pd.read_excel(BytesIO(raw))
        return repair_dataframe_text(df), "excel"
    raise ValueError(t("upload_error"))


# ---------------------------------------------------------------------------
# Atomic JSON persistence (file lock + replace)
# ---------------------------------------------------------------------------

JsonT = TypeVar("JsonT")


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


# ---------------------------------------------------------------------------
# PII encryption at rest (GDPR Art. 32)
# ---------------------------------------------------------------------------


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


def maybe_sync_master_from_all_user_data(*, force: bool = False) -> bool:
    """Synk master-register fra alle brugere — throttlet medmindre force=True."""
    if is_master_register_cleared():
        return False
    if not force and not _master_sync_is_stale():
        return False
    sync_master_from_all_user_data()
    _touch_master_sync_stamp()
    return True


def _cookie_secure_flag() -> bool | None:
    raw = os.environ.get("BORGERLISTE_COOKIE_SECURE", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return None


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


def _read_json_raw(path: Path, default: JsonT) -> JsonT:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


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
        preserved = {USERS_PATH.name, APP_SETTINGS_PATH.name}
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
    name = safe_username(username or current_username())
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
    if not current_user():
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
    if not st.session_state.get("authenticated") or not current_user():
        return
    username = current_username()
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
    if not current_user():
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
    owner = username or (current_username() if current_user() else None)
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
    if not current_user():
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
    if owner is None and current_user():
        owner = current_username()

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


# ---------------------------------------------------------------------------
# Auth & users
# ---------------------------------------------------------------------------


def role_label(role: str) -> str:
    if role == "admin":
        return t("role_admin")
    return t("role_user")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return salt, digest.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate = hash_password(password, salt)
    return secrets.compare_digest(candidate, password_hash)


def _chmod_sensitive(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_users() -> list[dict]:
    data = _load_json_file(USERS_PATH, None)
    if data is None:
        return []
    if isinstance(data, dict) and isinstance(data.get("users"), list):
        return [entry for entry in data["users"] if isinstance(entry, dict)]
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    return []


def save_users(users: list[dict]) -> None:
    _save_json_file(USERS_PATH, {"users": users})
    _chmod_sensitive(USERS_PATH)


def validate_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.match(username.strip()))


def validate_password_strength(password: str) -> bool:
    return len(password) >= MIN_PASSWORD_LENGTH


def get_default_admin_password() -> str | None:
    env_password = os.environ.get("BORGERLISTE_ADMIN_PASSWORD", "").strip()
    if env_password:
        return env_password
    legacy_password = os.environ.get("BORGERLISTE_PASSWORD", "").strip()
    if legacy_password:
        return legacy_password
    try:
        secret_password = str(st.secrets.get("admin_password", "")).strip()
        if secret_password:
            return secret_password
    except Exception:
        pass
    return None


def ensure_default_admin() -> None:
    users = load_users()
    if users:
        return

    username = os.environ.get("BORGERLISTE_ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME).strip() or DEFAULT_ADMIN_USERNAME
    password = get_default_admin_password()
    bootstrap_password = False
    if not password:
        password = secrets.token_urlsafe(16)
        bootstrap_password = True

    salt, password_hash = hash_password(password)
    save_users(
        [
            {
                "username": username,
                "salt": salt,
                "password_hash": password_hash,
                "role": "admin",
                "active": True,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        ]
    )

    if bootstrap_password:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BOOTSTRAP_ADMIN_PATH.write_text(
            f"Username: {username}\nTemporary password: {password}\n",
            encoding="utf-8",
        )
        _chmod_sensitive(BOOTSTRAP_ADMIN_PATH)
        st.session_state["_bootstrap_notice_text"] = t("bootstrap_admin_notice", path=str(BOOTSTRAP_ADMIN_PATH))


def find_user(username: str) -> dict | None:
    needle = username.strip().lower()
    for user in load_users():
        if str(user.get("username", "")).lower() == needle:
            return user
    return None


def get_user_record(username: str) -> dict | None:
    return find_user(username)


def authenticate_user(username: str, password: str) -> dict | None:
    user = find_user(username)
    if not user or not user.get("active", True):
        return None
    if not verify_password(password, str(user.get("salt", "")), str(user.get("password_hash", ""))):
        return None
    return {
        "username": str(user["username"]),
        "role": user.get("role", "user"),
    }


def create_user_account(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    clean_username = username.strip()
    if not validate_username(clean_username):
        return False, t("admin_username_invalid")
    if not validate_password_strength(password):
        return False, t("admin_password_weak", min=MIN_PASSWORD_LENGTH)
    if role not in USER_ROLES:
        role = "user"
    if find_user(clean_username):
        return False, t("admin_user_exists")

    salt, password_hash = hash_password(password)
    users = load_users()
    users.append(
        {
            "username": clean_username,
            "salt": salt,
            "password_hash": password_hash,
            "role": role,
            "active": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_users(users)
    return True, t("admin_user_created", username=clean_username)


def deactivate_user_account(username: str, *, delete_data: bool = False) -> tuple[bool, str]:
    if username.strip().lower() == current_username().lower():
        return False, t("admin_cannot_deactivate_self")
    users = load_users()
    changed = False
    for user in users:
        if str(user.get("username", "")).lower() == username.strip().lower():
            user["active"] = False
            user["deactivated_at"] = datetime.now().isoformat(timespec="seconds")
            changed = True
            break
    if not changed:
        return False, t("admin_user_invalid", min=MIN_PASSWORD_LENGTH)
    save_users(users)
    revoke_user_sessions(username)
    if delete_data:
        delete_user_data(username)
        return True, t("admin_user_deactivated_data_deleted", username=username)
    return True, t("admin_user_deactivated", username=username)


def update_user_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
    user = find_user(username)
    if not user or not user.get("active", True):
        return False, t("account_password_wrong")
    if not verify_password(current_password, str(user.get("salt", "")), str(user.get("password_hash", ""))):
        return False, t("account_password_wrong")
    if not validate_password_strength(new_password):
        return False, t("admin_password_weak", min=MIN_PASSWORD_LENGTH)

    salt, password_hash = hash_password(new_password)
    users = load_users()
    for entry in users:
        if str(entry.get("username", "")).lower() == username.strip().lower():
            entry["salt"] = salt
            entry["password_hash"] = password_hash
            entry["password_updated_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_users(users)
    revoke_user_sessions(username)
    return True, t("account_password_updated")


def admin_reset_user_password(username: str, new_password: str) -> tuple[bool, str]:
    if not is_admin():
        return False, t("master_delete_admin_only")
    if not validate_password_strength(new_password):
        return False, t("admin_password_weak", min=MIN_PASSWORD_LENGTH)
    user = find_user(username)
    if not user or not user.get("active", True):
        return False, t("admin_user_invalid", min=MIN_PASSWORD_LENGTH)

    salt, password_hash = hash_password(new_password)
    users = load_users()
    for entry in users:
        if str(entry.get("username", "")).lower() == username.strip().lower():
            entry["salt"] = salt
            entry["password_hash"] = password_hash
            entry["password_updated_at"] = datetime.now().isoformat(timespec="seconds")
            break
    save_users(users)
    revoke_user_sessions(username)
    return True, t("admin_password_reset_done", username=username)


def current_user() -> dict | None:
    user = st.session_state.get("current_user")
    return user if isinstance(user, dict) else None


def current_username() -> str:
    user = current_user()
    return str(user["username"]) if user else "unknown"


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "admin")


def refresh_session_user() -> bool:
    """Genindlæs bruger fra disk og log ud hvis konto er deaktiveret."""
    if not st.session_state.get("authenticated"):
        return False

    session_user = current_user()
    if not session_user:
        logout_user()
        return False

    record = find_user(str(session_user.get("username", "")))
    if not record or not record.get("active", True):
        logout_user()
        return False

    st.session_state.current_user = {
        "username": str(record["username"]),
        "role": record.get("role", "user"),
    }
    return True


def _client_ip() -> str:
    trust_proxy = os.environ.get("BORGERLISTE_TRUST_PROXY", "").strip().lower() in ("1", "true", "yes")
    if not trust_proxy:
        return "local"
    try:
        headers = st.context.headers
        if headers:
            forwarded = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for")
            if forwarded:
                return str(forwarded).split(",")[0].strip()[:64]
            remote = headers.get("X-Real-Ip") or headers.get("x-real-ip")
            if remote:
                return str(remote).strip()[:64]
    except Exception:
        pass
    return "local"


def _load_login_attempts() -> dict[str, dict]:
    data = _load_json_file(LOGIN_ATTEMPTS_PATH, {})
    return data if isinstance(data, dict) else {}


def _save_login_attempts(data: dict[str, dict]) -> None:
    _save_json_file(LOGIN_ATTEMPTS_PATH, data)
    _chmod_sensitive(LOGIN_ATTEMPTS_PATH)


def check_login_rate_limit() -> tuple[bool, int]:
    client = _client_ip()
    attempts = _load_login_attempts()
    entry = attempts.get(client, {})
    locked_until = float(entry.get("locked_until", 0))
    now = datetime.now().timestamp()
    if locked_until > now:
        return False, max(1, int((locked_until - now + 59) // 60))
    if locked_until and locked_until <= now:
        attempts.pop(client, None)
        _save_login_attempts(attempts)
    return True, 0


def record_failed_login() -> None:
    client = _client_ip()
    attempts = _load_login_attempts()
    entry = attempts.get(client, {"count": 0})
    count = int(entry.get("count", 0)) + 1
    payload: dict[str, object] = {"count": count, "last_failed": datetime.now().isoformat(timespec="seconds")}
    if count >= LOGIN_MAX_ATTEMPTS:
        payload["locked_until"] = datetime.now().timestamp() + LOGIN_LOCKOUT_SECONDS
        payload["count"] = 0
    attempts[client] = payload
    _save_login_attempts(attempts)


def clear_login_attempts() -> None:
    client = _client_ip()
    attempts = _load_login_attempts()
    if client in attempts:
        attempts.pop(client, None)
        _save_login_attempts(attempts)


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
        "username": current_username(),
        "role": current_user().get("role", "user") if current_user() else "user",
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
    if not isinstance(entry, dict):
        return False
    decoded = decrypt_dict_pii(entry)
    return master_match_score(row, decoded) >= 2


def _register_entry_matches_row(entry: dict, row: pd.Series) -> bool:
    decoded = decrypt_dict_pii(entry) if any(str(entry.get(field, "")).startswith(PII_ENC_PREFIX) for field in PII_FIELDS) else entry
    return master_match_score(row, decoded) >= 2


def delete_user_data(username: str) -> None:
    user_dir = USER_DATA_ROOT / safe_username(username)
    if user_dir.exists():
        shutil.rmtree(user_dir)


def erase_citizen_data(row: pd.Series) -> None:
    """Fjern én borger fra alle lagre (Art. 17 — ret til sletning)."""
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


def verify_admin_master_delete(password: str) -> bool:
    """Kun aktive administratorer kan slette master-register — med egen adgangskode."""
    if not is_admin():
        return False
    user = find_user(current_username())
    if not user or not user.get("active", True) or user.get("role") != "admin":
        return False
    return verify_password(password, str(user.get("salt", "")), str(user.get("password_hash", "")))


def get_cookie_manager() -> stx.CookieManager:
    """Én CookieManager pr. Streamlit-run — instance-key må ikke matche widget-key."""
    if COOKIE_MANAGER_INSTANCE_KEY not in st.session_state:
        st.session_state[COOKIE_MANAGER_INSTANCE_KEY] = stx.CookieManager(key=COOKIE_MANAGER_KEY)
    return st.session_state[COOKIE_MANAGER_INSTANCE_KEY]


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


SESSION_IDLE_POLL_SECONDS = 15


def current_session_expires_at() -> datetime | None:
    """Tidspunkt hvor den aktuelle session udløber (inaktivitet eller max-alder)."""
    token = st.session_state.get("auth_token")
    if not token or not st.session_state.get("authenticated"):
        return None
    entry = _load_auth_sessions().get(str(token))
    if not entry:
        return None
    stamps = _session_timestamps(entry)
    if stamps is None:
        return None
    created, last_activity = stamps
    idle_deadline = last_activity + timedelta(seconds=session_idle_timeout_seconds())
    max_deadline = created + timedelta(seconds=session_max_age_seconds())
    return min(idle_deadline, max_deadline)


def inject_session_idle_reload_watch(expires_at: datetime) -> None:
    """Genindlæs siden når session udløber — uden Streamlit-fragment polling."""
    expires_ms = int(expires_at.timestamp() * 1000)
    poll_ms = SESSION_IDLE_POLL_SECONDS * 1000
    components.html(
        f"""
        <script>
        (function () {{
            const win = window.parent;
            const expiresAt = {expires_ms};
            const pollMs = {poll_ms};
            if (win.__borgerlisteIdleReloadTimer) {{
                win.clearInterval(win.__borgerlisteIdleReloadTimer);
            }}
            win.__borgerlisteIdleReloadTimer = win.setInterval(function () {{
                if (Date.now() >= expiresAt) {{
                    win.clearInterval(win.__borgerlisteIdleReloadTimer);
                    win.__borgerlisteIdleReloadTimer = null;
                    win.location.reload();
                }}
            }}, pollMs);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def ensure_authenticated_session() -> bool:
    """Validér session ved hver fuld sidevisning. Returnerer False hvis brugeren er logget ud."""
    if not st.session_state.get("authenticated"):
        return True
    token = st.session_state.get("auth_token")
    if not token:
        logout_user()
        st.session_state.session_expired_notice = True
        return False
    account = validate_persistent_session(str(token), touch=True)
    if account is None:
        logout_user()
        st.session_state.session_expired_notice = True
        return False
    st.session_state.current_user = account
    return True


def session_max_age_seconds() -> int:
    raw = os.environ.get("BORGERLISTE_SESSION_MAX_DAYS", str(DEFAULT_SESSION_MAX_DAYS)).strip()
    try:
        days = float(raw)
    except ValueError:
        days = float(DEFAULT_SESSION_MAX_DAYS)
    return max(1, int(days * 86400))


def _load_auth_sessions() -> dict[str, dict]:
    data = _load_json_file(AUTH_SESSIONS_PATH, None)
    if not isinstance(data, dict):
        return {}
    sessions = data.get("sessions")
    if not isinstance(sessions, dict):
        return {}
    return {key: value for key, value in sessions.items() if isinstance(value, dict)}


def _save_auth_sessions(sessions: dict[str, dict]) -> None:
    _save_json_file(AUTH_SESSIONS_PATH, {"sessions": sessions})
    _chmod_sensitive(AUTH_SESSIONS_PATH)


def _session_timestamps(entry: dict) -> tuple[datetime, datetime] | None:
    try:
        created = datetime.fromisoformat(str(entry.get("created_at", "")))
        last_activity = datetime.fromisoformat(str(entry.get("last_activity", "")))
    except ValueError:
        return None
    return created, last_activity


def _session_is_expired(entry: dict, *, now: datetime | None = None) -> bool:
    stamps = _session_timestamps(entry)
    if stamps is None:
        return True
    created, last_activity = stamps
    current = now or datetime.now()
    idle_seconds = (current - last_activity).total_seconds()
    age_seconds = (current - created).total_seconds()
    return idle_seconds > session_idle_timeout_seconds() or age_seconds > session_max_age_seconds()


def prune_expired_auth_sessions() -> None:
    sessions = _load_auth_sessions()
    changed = False
    for token in list(sessions.keys()):
        if _session_is_expired(sessions[token]):
            sessions.pop(token, None)
            changed = True
    if changed:
        _save_auth_sessions(sessions)


def revoke_persistent_session(token: str) -> None:
    if not token:
        return
    sessions = _load_auth_sessions()
    if token in sessions:
        sessions.pop(token, None)
        _save_auth_sessions(sessions)


def revoke_user_sessions(username: str) -> None:
    needle = username.strip().lower()
    sessions = _load_auth_sessions()
    changed = False
    for token, entry in list(sessions.items()):
        if str(entry.get("username", "")).lower() == needle:
            sessions.pop(token, None)
            changed = True
    if changed:
        _save_auth_sessions(sessions)


def create_persistent_session(account: dict, *, sync_cookie: bool = False) -> str:
    """Opret persistent session-token i auth_sessions.json."""
    prune_expired_auth_sessions()
    token = secrets.token_urlsafe(32)
    now = datetime.now().isoformat(timespec="seconds")
    sessions = _load_auth_sessions()
    sessions[token] = {
        "username": account["username"],
        "role": account.get("role", "user"),
        "created_at": now,
        "last_activity": now,
    }
    _save_auth_sessions(sessions)
    if sync_cookie:
        set_persistent_session_cookie(token)
    return token


def _account_from_session_entry(entry: dict) -> dict | None:
    user = find_user(str(entry.get("username", "")))
    if not user or not user.get("active", True):
        return None
    return {
        "username": str(user["username"]),
        "role": user.get("role", "user"),
    }


def validate_persistent_session(token: str, *, touch: bool = True) -> dict | None:
    if not token or len(token) > 128:
        return None
    sessions = _load_auth_sessions()
    entry = sessions.get(token)
    if not entry:
        return None
    if _session_is_expired(entry):
        sessions.pop(token, None)
        _save_auth_sessions(sessions)
        return None

    account = _account_from_session_entry(entry)
    if not account:
        sessions.pop(token, None)
        _save_auth_sessions(sessions)
        return None

    if touch:
        entry["last_activity"] = datetime.now().isoformat(timespec="seconds")
        entry["role"] = account["role"]
        sessions[token] = entry
        _save_auth_sessions(sessions)
    return account


def set_persistent_session_cookie(token: str) -> None:
    expires_at = datetime.now() + timedelta(seconds=session_max_age_seconds())
    cookie_kwargs: dict[str, object] = {
        "expires_at": expires_at,
        "same_site": "lax",
        "key": "set_session_cookie",
    }
    secure = _cookie_secure_flag()
    if secure is not None:
        cookie_kwargs["secure"] = secure
    get_cookie_manager().set(SESSION_COOKIE_NAME, token, **cookie_kwargs)


def clear_persistent_session_cookie() -> None:
    try:
        manager = get_cookie_manager()
        manager.cookie_manager(
            method="delete",
            cookie=SESSION_COOKIE_NAME,
            key="clear_session_cookie",
            default=False,
        )
        manager.cookies.pop(SESSION_COOKIE_NAME, None)
    except Exception:
        pass


def _session_cookie_token() -> str | None:
    """Læs session-cookie — foretræk Streamlit context (synkront ved page load)."""
    try:
        cookies = st.context.cookies
        if cookies and SESSION_COOKIE_NAME in cookies:
            return str(cookies[SESSION_COOKIE_NAME])
    except Exception:
        pass
    raw = get_cookie_manager().get(SESSION_COOKIE_NAME)
    return str(raw) if raw else None


def prepare_cookie_reading() -> None:
    """Mount CookieManager én gang før restore (kun for uloggede besøg)."""
    if st.session_state.get("authenticated"):
        return
    if st.session_state.get("_cookie_init_done"):
        return
    get_cookie_manager().get_all()
    st.session_state._cookie_init_done = True


def try_restore_auth_from_cookie() -> bool:
    """Gendan login fra cookie når session state er tom (kun kaldt fra main())."""
    token = _session_cookie_token()
    if not token:
        return False

    account = validate_persistent_session(str(token), touch=True)
    if not account:
        clear_persistent_session_cookie()
        revoke_persistent_session(str(token))
        st.session_state.session_expired_notice = True
        return False

    st.session_state.authenticated = True
    st.session_state.current_user = account
    st.session_state.auth_token = str(token)
    return True


def ensure_auth_cookie_synced() -> None:
    """Synkroniser browser-cookie én gang efter vellykket login."""
    token = st.session_state.get("auth_token")
    if not token or not st.session_state.get("authenticated"):
        return
    if st.session_state.get("cookie_synced_for_token") == token:
        return
    try:
        set_persistent_session_cookie(str(token))
        st.session_state.cookie_synced_for_token = token
    except Exception:
        pass


def logout_user() -> None:
    username = current_username() if current_user() else None
    list_key = st.session_state.get("list_key")
    token = st.session_state.get("auth_token")
    if token:
        revoke_persistent_session(str(token))
    clear_persistent_session_cookie()
    clear_active_list(username=username, list_key=list_key)
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.auth_token = None
    st.session_state.cookie_synced_for_token = None
    st.session_state._cookie_init_done = False
    st.session_state.active_page = "borgerliste"
    st.session_state.user_data_loaded_for = None


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def _login_page_css() -> str:
    return """
html:has(#login-page-anchor) [data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}

html:has(#login-page-anchor) .block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

.login-hero {
    text-align: center;
    margin: 0 auto 1.75rem;
    max-width: 26rem;
}

.login-logo-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 1.1rem;
}

.login-logo-wrap img,
.login-logo-wrap svg {
    width: 6.5rem;
    height: 6.5rem;
    filter: drop-shadow(0 10px 24px rgba(37, 99, 235, 0.28));
}

.login-brand-title {
    font-size: 2.15rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0 0 0.35rem 0;
    color: var(--app-text, #1C1917);
}

.login-brand-subtitle {
    font-size: 1.02rem;
    line-height: 1.45;
    margin: 0;
    color: var(--app-text-muted, #64748B);
}

html:has(#login-page-anchor) [data-testid="stFormSubmitButton"] > button {
    margin-top: 0.35rem;
    min-height: 2.75rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}

@media (max-width: 768px) {
    html:has(#login-page-anchor) .block-container {
        padding-top: 1.5rem;
    }

    .login-brand-title {
        font-size: 1.75rem;
    }
}
"""


def render_login() -> bool:
    ensure_default_admin()

    if st.session_state.get("authenticated"):
        if refresh_session_user():
            token = st.session_state.get("auth_token")
            if token:
                validate_persistent_session(str(token), touch=True)
            return True
        logout_user()
        return False

    if st.session_state.pop("session_expired_notice", False):
        st.warning(t("login_session_expired"))

    if notice := st.session_state.pop("_bootstrap_notice_text", None):
        st.info(notice)

    allowed, minutes = check_login_rate_limit()
    st.markdown('<div id="login-page-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div id="login-card-anchor"></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([0.65, 1, 0.65])
    with center:
        logo_html = ""
        if LOGO_PATH.exists():
            logo_html = (
                f'<div class="login-logo-wrap">'
                f'<img src="data:image/svg+xml;base64,{_logo_base64()}" alt="{html.escape(t("app_title"))}"/>'
                f"</div>"
            )

        st.markdown(
            f'<div class="login-hero">{logo_html}'
            f'<p class="login-brand-title">{html.escape(t("app_title"))}</p>'
            f'<p class="login-brand-subtitle">{html.escape(t("app_subtitle"))}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )

        if not allowed:
            st.error(t("login_locked_out", minutes=minutes))
            return False

        with st.container(border=True):
            st.markdown(f"### {t('login_title')}")
            st.caption(t("login_caption"))
            st.caption(t("session_valid_for", minutes=configured_session_idle_minutes()))

            with st.form("login_form"):
                username = st.text_input(t("login_username"))
                password = st.text_input(t("login_password"), type="password")
                submitted = st.form_submit_button(t("login_submit"), type="primary", use_container_width=True)

            if submitted:
                account = authenticate_user(username, password)
                if account:
                    clear_login_attempts()
                    token = create_persistent_session(account, sync_cookie=False)
                    st.session_state.auth_token = token
                    st.session_state.authenticated = True
                    st.session_state.current_user = account
                    if BOOTSTRAP_ADMIN_PATH.exists() and username.strip().lower() == account["username"].lower():
                        try:
                            BOOTSTRAP_ADMIN_PATH.unlink()
                        except OSError:
                            pass
                    st.rerun()
                else:
                    record_failed_login()
                    st.error(t("login_error"))

    return False


def render_sidebar_pin_bridge() -> None:
    """Skjult Streamlit-knap i sidebar som header-pin udløser."""
    with st.sidebar:
        if st.button(
            "\u200b",
            key="borgerliste_pin_bridge",
            help="borgerliste-pin-bridge",
            type="secondary",
        ):
            st.session_state.sidebar_pinned = not bool(st.session_state.get("sidebar_pinned"))
            save_user_preferences(sidebar_pinned=st.session_state.sidebar_pinned)
            st.rerun()


def finalize_sidebar_controls(*, show_pin: bool) -> None:
    inject_sidebar_controls(
        pinned=bool(st.session_state.get("sidebar_pinned")),
        show_pin=show_pin,
        pin_label=t("sidebar_pin"),
        unpin_label=t("sidebar_unpin"),
    )


def finish_page(*, show_pin: bool) -> None:
    finalize_sidebar_controls(show_pin=show_pin)
    if st.session_state.get("authenticated"):
        expires_at = current_session_expires_at()
        if expires_at is not None:
            inject_session_idle_reload_watch(expires_at)


def render_page_navigation() -> None:
    render_sidebar_pin_bridge()
    current_page = st.session_state.get("active_page", "borgerliste")
    st.sidebar.markdown(f'<p class="sidebar-menu-label">{html.escape(t("menu"))}</p>', unsafe_allow_html=True)
    if st.sidebar.button(
        t("nav_borgerliste"),
        use_container_width=True,
        type="primary" if current_page == "borgerliste" else "secondary",
        key="nav_borgerliste",
    ):
        st.session_state.active_page = "borgerliste"
        st.rerun()
    if st.sidebar.button(
        t("nav_account"),
        use_container_width=True,
        type="primary" if current_page == "account" else "secondary",
        key="nav_account",
    ):
        st.session_state.active_page = "account"
        st.rerun()
    if st.sidebar.button(
        t("nav_privacy"),
        use_container_width=True,
        type="primary" if current_page == "privacy" else "secondary",
        key="nav_privacy",
    ):
        st.session_state.active_page = "privacy"
        st.rerun()
    st.sidebar.markdown('<div class="sidebar-divider-spacer"></div>', unsafe_allow_html=True)


def render_profile_section() -> None:
    user = current_user()
    if not user:
        return

    record = get_user_record(user["username"]) or {}
    col1, col2 = st.columns(2)
    with col1:
        st.text_input(t("account_username_label"), value=user["username"], disabled=True)
    with col2:
        st.text_input(t("account_role_label"), value=role_label(str(user.get("role", "user"))), disabled=True)
    if record.get("created_at"):
        st.caption(f"{t('account_created_label')}: {record['created_at']}")

    st.markdown(f"#### {t('account_change_password_title')}")
    st.caption(t("account_password_hint", min=MIN_PASSWORD_LENGTH))
    with st.form("change_password_form", clear_on_submit=True):
        current_password = st.text_input(t("account_current_password"), type="password")
        new_password = st.text_input(t("account_new_password"), type="password")
        confirm_password = st.text_input(t("account_confirm_password"), type="password")
        submitted = st.form_submit_button(t("account_password_submit"), type="primary", use_container_width=True)
        if submitted:
            if new_password != confirm_password:
                st.error(t("account_password_mismatch"))
            else:
                ok, message = update_user_password(user["username"], current_password, new_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


def render_admin_settings_section() -> None:
    st.markdown(f"#### {t('admin_session_title')}")
    current_minutes = configured_session_idle_minutes()
    st.caption(t("admin_session_current", minutes=current_minutes))
    st.caption(t("admin_session_idle_help"))

    with st.form("admin_session_settings_form"):
        idle_minutes = st.number_input(
            t("admin_session_idle_label"),
            min_value=MIN_SESSION_IDLE_MINUTES,
            max_value=MAX_SESSION_IDLE_MINUTES,
            value=current_minutes,
            step=1,
        )
        submitted = st.form_submit_button(t("admin_session_save"), use_container_width=True)
        if submitted:
            try:
                minutes = int(idle_minutes)
            except (TypeError, ValueError):
                minutes = -1
            if not MIN_SESSION_IDLE_MINUTES <= minutes <= MAX_SESSION_IDLE_MINUTES:
                st.error(
                    t(
                        "admin_session_idle_invalid",
                        min=MIN_SESSION_IDLE_MINUTES,
                        max=MAX_SESSION_IDLE_MINUTES,
                    )
                )
            else:
                save_app_settings(session_idle_minutes=minutes, session_idle_hours=None)
                st.success(t("admin_session_idle_saved"))
                st.rerun()


def render_admin_users_section() -> None:
    st.markdown(f"#### {t('admin_users_title')}")

    with st.expander(t("admin_create_user"), expanded=False):
        with st.form("create_user_form", clear_on_submit=True):
            username = st.text_input(t("admin_new_username"))
            password = st.text_input(t("admin_new_password"), type="password")
            role = st.selectbox(t("admin_new_role"), USER_ROLES, format_func=role_label)
            submitted = st.form_submit_button(t("admin_create_submit"), use_container_width=True)
            if submitted:
                ok, message = create_user_account(username, password, role)
                if ok:
                    st.success(message)
                    st.rerun()
                st.error(message)

    users = load_users()
    if not users:
        st.info(t("admin_no_users"))
        return

    for user in users:
        username = str(user.get("username", ""))
        active = bool(user.get("active", True))
        status = "✅" if active else "⛔"
        with st.container(border=True):
            st.markdown(f"{status} **{html.escape(username)}** · {role_label(str(user.get('role', 'user')))}")
            if user.get("created_at"):
                st.caption(f"{t('account_created_label')}: {user['created_at']}")

            if active and username != current_username():
                with st.expander(t("admin_reset_password"), expanded=False):
                    with st.form(f"reset_password_{username}", clear_on_submit=True):
                        new_password = st.text_input(
                            t("admin_reset_password_for", username=username),
                            type="password",
                            key=f"reset_pw_{username}",
                        )
                        if st.form_submit_button(t("admin_reset_password"), use_container_width=True):
                            ok, message = admin_reset_user_password(username, new_password)
                            if ok:
                                st.success(message)
                            else:
                                st.error(message)

                delete_data = st.checkbox(
                    t("admin_deactivate_delete_data"),
                    key=f"delete_data_{username}",
                )
                if st.button(
                    t("admin_deactivate"),
                    key=f"deactivate_{username}",
                    use_container_width=True,
                    type="secondary",
                ):
                    ok, message = deactivate_user_account(username, delete_data=delete_data)
                    if ok:
                        st.toast(message, icon="✅")
                        st.rerun()
                    st.error(message)
            elif active and username == current_username():
                st.caption(t("admin_cannot_deactivate_self"))


def render_admin_master_section() -> None:
    maybe_sync_master_from_all_user_data(force=True)
    register = load_master_register()
    st.caption(t("master_admin_description"))
    st.metric("Master", len(register))
    st.caption(t("master_register_count", count=len(register)))

    with st.expander(t("clear_master_register"), expanded=False):
        st.caption(t("master_delete_warning"))

        with st.form("master_delete_form", clear_on_submit=True):
            password = st.text_input(t("master_delete_password"), type="password")
            submitted = st.form_submit_button(t("master_delete_confirm"), use_container_width=True)
            if submitted:
                if verify_admin_master_delete(password):
                    clear_master_register()
                    st.session_state.user_data_loaded_for = None
                    st.toast(t("master_register_cleared"), icon="✅")
                    st.rerun()
                st.error(t("master_delete_password_error"))


def render_gdpr_privacy_section() -> None:
    st.markdown(t("gdpr_text"))
    st.markdown(t("gdpr_purpose"))
    st.markdown(t("gdpr_legal_basis"))
    st.markdown(t("gdpr_data_types"))
    st.markdown(t("gdpr_rights"))
    st.markdown(t("gdpr_retention_info"))
    st.markdown(t("gdpr_security_info"))
    st.markdown(t("gdpr_shared_register"))
    st.markdown(t("gdpr_contact"))


def render_user_activity_section() -> None:
    st.markdown(f"#### {t('user_audit_title')}")
    st.caption(t("user_audit_caption"))
    username = current_username()
    entries = [entry for entry in load_audit_log() if entry.get("username") == username]
    if not entries:
        st.info(t("admin_audit_empty"))
        return

    labels = build_citizen_label_map()
    rows = []
    for entry in reversed(entries[-500:]):
        citizen_id = str(entry.get("citizen_id", ""))
        rows.append(
            {
                t("admin_audit_col_time"): entry.get("timestamp", ""),
                t("admin_audit_col_citizen"): labels.get(citizen_id, citizen_id),
                t("admin_audit_col_from"): status_label(str(entry.get("old_status", "")), short=True),
                t("admin_audit_col_to"): status_label(str(entry.get("new_status", "")), short=True),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_admin_gdpr_section() -> None:
    st.markdown(f"#### {t('admin_retention_title')}")
    current_months = configured_retention_months()
    if current_months <= 0:
        st.caption(t("admin_retention_disabled"))
    else:
        st.caption(t("admin_retention_current", months=current_months))

    with st.form("admin_retention_form"):
        months = st.number_input(
            t("admin_retention_label"),
            min_value=MIN_RETENTION_MONTHS,
            max_value=MAX_RETENTION_MONTHS,
            value=current_months,
            step=1,
            help=t("admin_retention_help"),
        )
        submitted = st.form_submit_button(t("admin_session_save"), use_container_width=True)
        if submitted:
            try:
                value = int(months)
            except (TypeError, ValueError):
                value = -1
            if not MIN_RETENTION_MONTHS <= value <= MAX_RETENTION_MONTHS:
                st.error(t("admin_retention_invalid", min=MIN_RETENTION_MONTHS, max=MAX_RETENTION_MONTHS))
            else:
                save_app_settings(data_retention_months=value)
                st.session_state.retention_applied = False
                st.success(t("admin_retention_saved"))
                st.rerun()

    st.markdown(f"#### {t('admin_gdpr_processing_title')}")
    st.markdown(t("admin_gdpr_processing_body"))


def render_audit_log_section(*, admin_view: bool = True) -> None:
    st.markdown(f"#### {t('admin_audit_title')}")
    st.caption(t("admin_audit_caption"))
    entries = load_audit_log()
    if not entries:
        st.info(t("admin_audit_empty"))
        return

    filter_cols = st.columns(2)
    usernames = sorted({str(entry.get("username", "")) for entry in entries if entry.get("username")})
    with filter_cols[0]:
        filter_user = st.selectbox(
            t("admin_audit_filter_user"),
            [t("admin_audit_all_users"), *usernames],
        )
    with filter_cols[1]:
        filter_citizen = st.text_input(t("admin_audit_filter_citizen"))

    filtered = entries
    if filter_user != t("admin_audit_all_users"):
        filtered = [entry for entry in filtered if entry.get("username") == filter_user]
    labels = build_citizen_label_map()
    if filter_citizen.strip():
        needle = filter_citizen.strip().lower()
        filtered = [
            entry
            for entry in filtered
            if needle in labels.get(str(entry.get("citizen_id", "")), "").lower()
            or needle in str(entry.get("citizen_id", "")).lower()
        ]

    rows = []
    for entry in reversed(filtered[-500:]):
        citizen_id = str(entry.get("citizen_id", ""))
        rows.append(
            {
                t("admin_audit_col_time"): entry.get("timestamp", ""),
                t("admin_audit_col_user"): entry.get("username", ""),
                t("admin_audit_col_citizen"): labels.get(citizen_id, citizen_id),
                t("admin_audit_col_from"): status_label(str(entry.get("old_status", "")), short=True),
                t("admin_audit_col_to"): status_label(str(entry.get("new_status", "")), short=True),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_privacy_page() -> None:
    st.title(t("gdpr_title"))
    render_gdpr_privacy_section()


def render_account_page() -> None:
    st.title(t("account_title"))
    if purged := st.session_state.pop("retention_purged_count", None):
        st.info(t("admin_retention_purged", count=purged))

    tab_labels = [t("account_profile_tab"), t("account_activity_tab")]
    if is_admin():
        tab_labels.extend(
            [
                t("account_admin_users_tab"),
                t("account_admin_settings_tab"),
                t("account_admin_master_tab"),
                t("account_admin_audit_tab"),
                t("account_admin_gdpr_tab"),
            ]
        )

    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_profile_section()
    with tabs[1]:
        render_user_activity_section()
    if is_admin():
        with tabs[2]:
            render_admin_users_section()
        with tabs[3]:
            render_admin_settings_section()
        with tabs[4]:
            render_admin_master_section()
        with tabs[5]:
            render_audit_log_section()
        with tabs[6]:
            render_admin_gdpr_section()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def status_pill_html(status: str, short: bool = True) -> str:
    pill_class = STATUS_PILL_CLASS.get(status, "status-pill--neutral")
    label = status_label(status, short=short)
    return f'<span class="status-pill {pill_class}">{html.escape(label)}</span>'


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


def _light_theme_field_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-testid="stTextInput"] input,
{sp}div[data-baseweb="input"] input,
{sp}div[data-testid="stSelectbox"] [data-baseweb="select"],
{sp}div[data-testid="stSelectbox"] div[data-baseweb="select"],
{sp}div[data-testid="stMultiSelect"] div[data-baseweb="select"],
{sp}div[data-baseweb="select"] > div,
{sp}div[data-baseweb="select"] {{
    background-color: #FFFFFF !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    border: 1px solid #9CA3AF !important;
    caret-color: #111827 !important;
}}

{sp}div[data-testid="stSelectbox"] [data-baseweb="select"] *,
{sp}div[data-baseweb="select"] div,
{sp}div[data-baseweb="select"] span {{
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}}

{sp}div[data-baseweb="select"] svg {{
    fill: #111827 !important;
}}

{sp}div[data-testid="stTextInput"] input::placeholder,
{sp}div[data-baseweb="input"] input::placeholder {{
    color: #6B7280 !important;
    -webkit-text-fill-color: #6B7280 !important;
    opacity: 1 !important;
}}
"""


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

{_light_theme_field_css(".light-theme")}

{active_rules}
"""


def _light_theme_tooltip_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-baseweb="tooltip"] > div,
{sp}div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) > div,
{sp}div[data-baseweb="popover"]:has(.stTooltipContent) > div,
{sp}div[role="tooltip"],
{sp}div[role="tooltip"] > div {{
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12) !important;
}}

{sp}div[data-baseweb="tooltip"],
{sp}div[role="tooltip"] {{
    color: #111827 !important;
}}

{sp}[data-testid="stTooltipContent"],
{sp}.stTooltipContent,
{sp}[data-testid="stTooltipContent"] *,
{sp}.stTooltipContent *,
{sp}div[data-baseweb="tooltip"] *,
{sp}div[role="tooltip"] * {{
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}}
"""


def _dark_theme_field_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-testid="stTextInput"] input,
{sp}div[data-baseweb="input"] input,
{sp}div[data-testid="stSelectbox"] [data-baseweb="select"],
{sp}div[data-testid="stSelectbox"] div[data-baseweb="select"],
{sp}div[data-testid="stMultiSelect"] div[data-baseweb="select"],
{sp}div[data-baseweb="select"] > div,
{sp}div[data-baseweb="select"] {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    caret-color: #F8FAFC !important;
}}

{sp}div[data-testid="stSelectbox"] [data-baseweb="select"] *,
{sp}div[data-baseweb="select"] div,
{sp}div[data-baseweb="select"] span {{
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}

{sp}div[data-baseweb="select"] svg {{
    fill: #F8FAFC !important;
}}

{sp}div[data-testid="stTextInput"] input::placeholder,
{sp}div[data-baseweb="input"] input::placeholder {{
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    opacity: 1 !important;
}}
"""


def _toast_shell_css(
    scope: str,
    *,
    bg: str,
    text: str,
    border: str,
    shadow: str,
    button: str,
) -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}[data-testid="stToast"],
{sp}.stToast {{
    background-color: {bg} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    box-shadow: {shadow} !important;
    border-radius: 0.65rem !important;
    overflow: hidden !important;
}}

{sp}[data-testid="stToast"] > div,
{sp}[data-testid="stToast"] div,
{sp}.stToast > div,
{sp}.stToast div {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}

{sp}[data-testid="stToast"] *,
{sp}.stToast * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

{sp}[data-testid="stToast"] button,
{sp}.stToast button {{
    color: {button} !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
"""


def _light_theme_toast_css(scope: str = "") -> str:
    return _toast_shell_css(
        scope,
        bg="#FFFFFF",
        text="#1C1917",
        border="#E7E5E4",
        shadow="0 10px 28px rgba(15, 23, 42, 0.12)",
        button="#64748B",
    )


def _dark_theme_toast_css(scope: str = "") -> str:
    return _toast_shell_css(
        scope,
        bg="#1E293B",
        text="#F8FAFC",
        border="#334155",
        shadow="0 10px 28px rgba(0, 0, 0, 0.42)",
        button="#94A3B8",
    )


def _dark_theme_tooltip_css(scope: str = "") -> str:
    sp = f"{scope} " if scope else ""
    return f"""
{sp}div[data-baseweb="tooltip"] > div,
{sp}div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) > div,
{sp}div[data-baseweb="popover"]:has(.stTooltipContent) > div,
{sp}div[role="tooltip"],
{sp}div[role="tooltip"] > div {{
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
}}

{sp}div[data-baseweb="tooltip"],
{sp}div[role="tooltip"] {{
    color: #F8FAFC !important;
}}

{sp}[data-testid="stTooltipContent"],
{sp}.stTooltipContent,
{sp}[data-testid="stTooltipContent"] *,
{sp}.stTooltipContent *,
{sp}div[data-baseweb="tooltip"] *,
{sp}div[role="tooltip"] * {{
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
}}
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

{_dark_theme_field_css(".dark-theme")}

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

#login-card-anchor + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--app-card-bg, #FFFFFF) !important;
    border: 1px solid var(--app-border, #E7E5E4) !important;
    border-radius: 18px !important;
    padding: 1.15rem 1.35rem 0.85rem !important;
    box-shadow: 0 16px 48px rgba(15, 23, 42, 0.08) !important;
}}

html:has(.dark-theme) #login-card-anchor + [data-testid="stElementContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
    box-shadow: 0 18px 52px rgba(0, 0, 0, 0.38) !important;
}}

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

[data-testid="stSidebar"] {{
    box-shadow: 10px 0 36px rgba(15, 23, 42, 0.07);
    border-right: 1px solid var(--app-border, #E7E5E4);
}}

[data-testid="stSidebar"] > div:first-child {{
    padding: 0.9rem 0.8rem 1.35rem !important;
    background: linear-gradient(
        180deg,
        var(--app-bg-secondary, #F5F5F4) 0%,
        var(--app-bg, #FAFAF9) 100%
    ) !important;
}}

html:has(.dark-theme) [data-testid="stSidebar"] {{
    box-shadow: 10px 0 40px rgba(0, 0, 0, 0.35);
}}

.sidebar-menu-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--app-text-muted, #64748B);
    margin: 0 0 0.35rem 0.2rem;
    line-height: 1.2;
}}

.sidebar-user-pill {{
    display: flex;
    flex-direction: column;
    gap: 0.12rem;
    padding: 0.62rem 0.72rem;
    margin: 0.15rem 0 0.65rem;
    border-radius: 12px;
    background: rgba(37, 99, 235, 0.07);
    border: 1px solid rgba(37, 99, 235, 0.14);
}}

.sidebar-user-name {{
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--app-text, #1C1917);
    line-height: 1.25;
}}

.sidebar-user-role {{
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--app-text-muted, #64748B);
    letter-spacing: 0.02em;
}}

.sidebar-divider-spacer {{
    height: 0.55rem;
}}

.sidebar-settings-panel {{
    margin-top: 0.15rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--app-border, #E7E5E4);
}}

[data-testid="stSidebar"] .stButton > button {{
    border-radius: 10px !important;
    min-height: 2.4rem !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}}

[data-testid="stSidebar"] .stButton > button[kind="secondary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"] {{
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--app-text-muted, #64748B) !important;
}}

[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"]:hover {{
    background: rgba(37, 99, 235, 0.06) !important;
    border-color: rgba(37, 99, 235, 0.12) !important;
    color: var(--app-text, #1C1917) !important;
}}

[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {{
    background: rgba(37, 99, 235, 0.12) !important;
    border: 1px solid rgba(37, 99, 235, 0.28) !important;
    color: {PRIMARY_COLOR} !important;
    font-weight: 700 !important;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    margin-bottom: 0.25rem;
}}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--app-text-muted, #64748B) !important;
    opacity: 0.85;
}}

[data-testid="stSidebar"] [data-testid="stExpander"] {{
    border: 1px solid var(--app-border, #E7E5E4) !important;
    border-radius: 10px !important;
    overflow: hidden;
    background: transparent !important;
}}

[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.45rem 0.55rem !important;
}}

[data-testid="stSidebar"] hr {{
    margin: 0.5rem 0 !important;
    opacity: 0.25;
}}

.borgerliste-pin-bridge {{
    display: none !important;
}}

[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge {{
    position: fixed !important;
    left: -10000px !important;
    top: 0 !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    z-index: -1 !important;
    clip: rect(0, 0, 0, 0) !important;
}}

[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge [data-testid="stButton"] > button {{
    min-height: 0 !important;
    height: 1px !important;
    width: 1px !important;
    padding: 0 !important;
    font-size: 0 !important;
    line-height: 0 !important;
    border: none !important;
    background: transparent !important;
}}

.borgerliste-pin-host {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.2rem !important;
    vertical-align: middle !important;
}}

.borgerliste-header-pin {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
    color: inherit;
    cursor: pointer;
    opacity: 0.72;
    flex: 0 0 auto;
    line-height: 1;
    pointer-events: auto;
    transition: background 0.15s ease, opacity 0.15s ease, color 0.15s ease;
}}

.borgerliste-header-pin:hover {{
    opacity: 1;
    background: rgba(128, 131, 145, 0.14);
}}

.borgerliste-header-pin.is-pinned {{
    opacity: 1;
    color: {PRIMARY_COLOR};
}}

.borgerliste-header-pin svg {{
    display: block;
    width: 1.125rem;
    height: 1.125rem;
    fill: currentColor;
}}

[data-testid="stAppViewContainer"] iframe[height="0"] {{
    pointer-events: none !important;
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

[data-testid="stToast"],
.stToast {{
    background-color: var(--app-card-bg) !important;
    color: var(--app-text) !important;
    border: 1px solid var(--app-border) !important;
    border-radius: 0.65rem !important;
    overflow: hidden !important;
}}

[data-testid="stToast"] > div,
[data-testid="stToast"] div,
.stToast > div,
.stToast div {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}

[data-testid="stToast"] *,
.stToast * {{
    color: var(--app-text) !important;
    -webkit-text-fill-color: var(--app-text) !important;
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
    css_parts = [_base_css_rules(t("upload_browse")), _login_page_css()]

    if theme_choice == "Browser standard":
        light = THEME_PALETTES["Lyst tema"]
        dark = THEME_PALETTES["Mørkt tema"]
        css_parts.append(_themed_css_rules(light, light["input_bg"], media="(prefers-color-scheme: light)"))
        css_parts.append(_themed_css_rules(dark, dark["input_bg"], media="(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_light_theme_overrides_css(), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_field_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_tooltip_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_light_theme_toast_css("html:has(.stApp.light-theme)"), "(prefers-color-scheme: light)"))
        css_parts.append(_wrap_media(_dark_theme_overrides_css(), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_field_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_tooltip_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
        css_parts.append(_wrap_media(_dark_theme_toast_css("html:has(.stApp.dark-theme)"), "(prefers-color-scheme: dark)"))
    elif theme_choice in THEME_PALETTES:
        palette = THEME_PALETTES[theme_choice]
        is_light = theme_choice == "Lyst tema"
        button_secondary_bg = "#FFFFFF" if is_light else palette["input_bg"]
        css_parts.append(_themed_css_rules(palette, button_secondary_bg))
        if is_light:
            css_parts.append(_light_theme_overrides_css())
            css_parts.append(_light_theme_field_css())
            css_parts.append(_light_theme_tooltip_css())
            css_parts.append(_light_theme_toast_css())
        else:
            css_parts.append(_dark_theme_overrides_css())
            css_parts.append(_dark_theme_field_css())
            css_parts.append(_dark_theme_tooltip_css())
            css_parts.append(_dark_theme_toast_css())
            css_parts.append(_dark_theme_toast_css(".dark-theme"))

    css = "<style>\n" + "\n".join(css_parts) + "\n</style>"
    st.markdown(css, unsafe_allow_html=True)
    _inject_theme_class(theme_choice)


def inject_sidebar_controls(
    delay_seconds: int = SIDEBAR_AUTO_COLLAPSE_SECONDS,
    *,
    pinned: bool = False,
    show_pin: bool = False,
    pin_label: str = "",
    unpin_label: str = "",
) -> None:
    """Header-pin ved sidebar-toggle + auto-luk (letvægts, uden DOM-overvågning)."""
    delay_ms = max(1, int(delay_seconds)) * 1000
    pinned_js = "true" if pinned else "false"
    show_pin_js = "true" if show_pin else "false"
    pin_svg = (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path d="M16 9V4h1c.55 0 1-.45 1-1s-.45-1-1-1H7c-.55 0-1 .45-1 1s.45 1 1 1h1v5c0 1.66-1.34 3-3 3v2h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/>'
        "</svg>"
    )
    components.html(
        f"""
        <script>
        (function() {{
            const win = window.parent;
            const doc = win.document;
            const cfg = win.__borgerlisteSidebar || (win.__borgerlisteSidebar = {{}});
            if (cfg.pinObserver) {{
                cfg.pinObserver.disconnect();
                delete cfg.pinObserver;
            }}
            cfg.delay = {delay_ms};
            cfg.pinned = {pinned_js};
            cfg.showPin = {show_pin_js};
            cfg.pinLabel = {json.dumps(pin_label)};
            cfg.unpinLabel = {json.dumps(unpin_label)};
            cfg.pinIcon = {json.dumps(pin_svg)};

            if (!cfg.ready) {{
                cfg.ready = true;

                cfg.isSidebarExpanded = function() {{
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    return !!sidebar && sidebar.getBoundingClientRect().width > 48;
                }};

                cfg.findSidebarToggleButton = function() {{
                    const pickToggle = (root) => Array.from(root.querySelectorAll('button')).find((btn) => {{
                        if (btn.id === 'borgerliste-sidebar-pin') return false;
                        const label = (btn.getAttribute('aria-label') || btn.textContent || '').toLowerCase();
                        return (
                            label.includes('keyboard_double_arrow_left')
                            || label.includes('keyboard_double_arrow_right')
                            || label.includes('collapse')
                            || label.includes('expand')
                        );
                    }}) || null;

                    const collapsed = doc.querySelector('[data-testid="collapsedControl"] button');
                    if (collapsed) return collapsed;

                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (sidebar) {{
                        const inSidebar = pickToggle(sidebar);
                        if (inSidebar) return inSidebar;
                    }}

                    const header = doc.querySelector('[data-testid="stHeader"]');
                    if (header) return pickToggle(header);
                    return null;
                }};

                cfg.findSidebarButton = function(kind) {{
                    return Array.from(doc.querySelectorAll('button')).find((btn) => {{
                        const label = (btn.getAttribute('aria-label') || btn.textContent || '').toLowerCase();
                        return label.includes(kind);
                    }}) || null;
                }};

                cfg.triggerPinToggle = function() {{
                    const bridge = doc.querySelector('.st-key-borgerliste_pin_bridge button')
                        || doc.querySelector('[data-testid="stSidebar"] .st-key-borgerliste_pin_bridge button');
                    if (bridge) {{
                        bridge.click();
                        return;
                    }}
                    win.setTimeout(() => {{
                        doc.querySelector('.st-key-borgerliste_pin_bridge button')?.click();
                    }}, 120);
                }};

                cfg.syncPinButtonSize = function(toggleBtn, pinBtn) {{
                    if (!toggleBtn || !pinBtn) return;
                    const rect = toggleBtn.getBoundingClientRect();
                    if (rect.width > 0) {{
                        pinBtn.style.width = `${{rect.width}}px`;
                        pinBtn.style.height = `${{rect.height}}px`;
                        pinBtn.style.minWidth = `${{rect.width}}px`;
                        pinBtn.style.minHeight = `${{rect.height}}px`;
                    }}
                    const toggleStyle = win.getComputedStyle(toggleBtn);
                    pinBtn.style.borderRadius = toggleStyle.borderRadius;
                }};

                cfg.updatePinButton = function() {{
                    const oldRow = doc.getElementById('borgerliste-header-pin-row');
                    if (oldRow?.parentElement) {{
                        while (oldRow.firstChild) {{
                            oldRow.parentElement.insertBefore(oldRow.firstChild, oldRow);
                        }}
                        oldRow.remove();
                    }}

                    if (!cfg.showPin) {{
                        doc.getElementById('borgerliste-sidebar-pin')?.remove();
                        return;
                    }}

                    const toggleBtn = cfg.findSidebarToggleButton();
                    if (!toggleBtn?.parentElement) return;

                    toggleBtn.parentElement.classList.add('borgerliste-pin-host');

                    let pinBtn = doc.getElementById('borgerliste-sidebar-pin');
                    if (!pinBtn) {{
                        pinBtn = doc.createElement('button');
                        pinBtn.id = 'borgerliste-sidebar-pin';
                        pinBtn.type = 'button';
                        pinBtn.className = 'borgerliste-header-pin';
                        pinBtn.addEventListener('click', (event) => {{
                            event.preventDefault();
                            event.stopPropagation();
                            cfg.triggerPinToggle();
                        }});
                        toggleBtn.parentElement.insertBefore(pinBtn, toggleBtn);
                    }} else if (pinBtn.nextElementSibling !== toggleBtn) {{
                        toggleBtn.parentElement.insertBefore(pinBtn, toggleBtn);
                    }}

                    pinBtn.innerHTML = cfg.pinIcon;
                    pinBtn.classList.toggle('is-pinned', cfg.pinned);
                    pinBtn.setAttribute('aria-label', cfg.pinned ? cfg.unpinLabel : cfg.pinLabel);
                    pinBtn.setAttribute('title', cfg.pinned ? cfg.unpinLabel : cfg.pinLabel);
                    cfg.syncPinButtonSize(toggleBtn, pinBtn);
                }};

                cfg.collapseSidebar = function() {{
                    if (cfg.pinned || !cfg.isSidebarExpanded()) return;
                    const btn = cfg.findSidebarButton('keyboard_double_arrow_left') || cfg.findSidebarButton('collapse');
                    if (btn) btn.click();
                }};

                cfg.expandSidebar = function() {{
                    if (!cfg.pinned || cfg.isSidebarExpanded()) return;
                    const btn = cfg.findSidebarButton('keyboard_double_arrow_right') || cfg.findSidebarButton('expand');
                    if (btn) btn.click();
                }};

                cfg.scheduleCollapse = function() {{
                    if (cfg.pinned) {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                        cfg.timer = null;
                        return;
                    }}
                    if (cfg.timer) win.clearTimeout(cfg.timer);
                    if (!cfg.isSidebarExpanded()) return;
                    cfg.timer = win.setTimeout(() => cfg.collapseSidebar(), cfg.delay);
                }};

                cfg.bindSidebarOnce = function() {{
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (!sidebar || sidebar.dataset.autoCollapseBound === '1') return;
                    sidebar.dataset.autoCollapseBound = '1';
                    sidebar.addEventListener('mouseenter', () => {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                    }});
                    sidebar.addEventListener('mouseleave', () => cfg.scheduleCollapse());
                    sidebar.addEventListener('focusin', () => {{
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                    }});
                    sidebar.addEventListener('focusout', () => cfg.scheduleCollapse());
                }};

                cfg.refresh = function() {{
                    cfg.updatePinButton();
                    if (cfg.pinned) {{
                        cfg.expandSidebar();
                        if (cfg.timer) win.clearTimeout(cfg.timer);
                        cfg.timer = null;
                        return;
                    }}
                    cfg.bindSidebarOnce();
                    cfg.scheduleCollapse();
                }};
            }}

            cfg.refresh();
            win.setTimeout(() => cfg.refresh(), 180);
        }})();
        </script>
        """,
        height=0,
    )


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
        "current_user": None,
        "auth_token": None,
        "cookie_synced_for_token": None,
        "active_page": "borgerliste",
        "user_data_loaded_for": None,
        "session_expired_notice": False,
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
        "sidebar_pinned": False,
        "retention_applied": False,
        "retention_purged_count": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.preferences_loaded:
        apply_saved_user_preferences()
        st.session_state.preferences_loaded = True


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



def sync_session_df_with_master() -> bool:
    """Opdater den aktive liste med seneste master-status fra alle brugere."""
    if st.session_state.pop("_skip_master_sync_once", False):
        return False

    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return False

    maybe_sync_master_from_all_user_data()
    register = load_master_register()
    updated, _matched = merge_master_register_statuses(df, register)

    status_cols = ["Status", "Status dato", "Ring igen dato"]
    if all(updated[col].equals(df[col]) for col in status_cols if col in df.columns and col in updated.columns):
        return False

    st.session_state.citizens_df = updated.reset_index(drop=True)
    list_key = st.session_state.get("list_key")
    if list_key:
        save_state(list_key, dataframe_to_state(st.session_state.citizens_df))
    save_active_list(st.session_state.citizens_df)
    return True


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
        full_df, _master_merged = merge_master_register_statuses(full_df, register)
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
        st.session_state.pop("_sidebar_excel_key", None)
        st.session_state.pop("_sidebar_excel_bytes", None)
        save_state(key, dataframe_to_state(full_df))
        save_active_list(full_df)
        maybe_sync_master_from_all_user_data(force=True)
        return True
    except Exception as exc:
        st.session_state._upload_error_detail = str(exc)
        st.error(t("upload_error"))
        return False


def _upload_signature(uploaded) -> str:
    size = getattr(uploaded, "size", None)
    if size is None:
        try:
            uploaded.seek(0, os.SEEK_END)
            size = uploaded.tell()
            uploaded.seek(0)
        except Exception:
            size = 0
    return f"{uploaded.name}:{size}"


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
                key="borgerliste_file_uploader",
            )
            if uploaded is None:
                uploaded = st.session_state.get("borgerliste_file_uploader")
            if uploaded is not None:
                signature = _upload_signature(uploaded)
                needs_upload = st.session_state.get("_last_upload_sig") != signature
                if not needs_upload and (
                    st.session_state.citizens_df is None or st.session_state.citizens_df.empty
                ):
                    st.session_state.pop("_last_upload_sig", None)
                    needs_upload = True
                if needs_upload:
                    if handle_file_upload(uploaded):
                        st.session_state._last_upload_sig = signature
                        st.rerun()
                    else:
                        st.session_state.pop("_last_upload_sig", None)
            else:
                st.session_state.pop("_last_upload_sig", None)
                st.session_state.pop("_upload_error_detail", None)

            if detail := st.session_state.get("_upload_error_detail"):
                st.caption(detail)

            if list_loaded and st.button(t("upload_keep_current"), use_container_width=True):
                st.session_state.show_uploader = False
                st.rerun()


def render_sidebar_settings() -> None:
    st.sidebar.markdown('<div class="sidebar-divider-spacer"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-settings-panel">', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lang-mini">', unsafe_allow_html=True)
    render_language_settings()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    render_theme_settings()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)



def render_sidebar_content() -> None:
    user = current_user()
    if user:
        st.sidebar.markdown(
            f'<div class="sidebar-user-pill">'
            f'<span class="sidebar-user-name">{html.escape(user["username"])}</span>'
            f'<span class="sidebar-user-role">{html.escape(role_label(str(user.get("role", "user"))))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.sidebar.button(t("logout"), use_container_width=True, key="sidebar_logout"):
            logout_user()
            st.rerun()
        st.sidebar.markdown('<div class="sidebar-divider-spacer"></div>', unsafe_allow_html=True)

    list_loaded = st.session_state.citizens_df is not None and not st.session_state.citizens_df.empty
    if not list_loaded:
        return

    if st.session_state.get("session_restored"):
        st.sidebar.caption(t("session_restored"))
        st.session_state.session_restored = False

    if st.sidebar.button(t("clear_saved_list"), use_container_width=True, key="sidebar_clear_list"):
        clear_active_list()
        st.rerun()

    st.sidebar.markdown('<div class="sidebar-divider-spacer"></div>', unsafe_allow_html=True)
    export_name = Path(st.session_state.source_filename or "borgerliste").stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    st.sidebar.download_button(
        label=t("export_excel"),
        data=sidebar_excel_bytes(),
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


def persist_citizen_status_change(
    *,
    updated: pd.DataFrame,
    updated_row: pd.Series,
    old_status: str,
    list_key: str | None,
) -> None:
    """Gem statusændring i én låst transaktion (liste, master, history, audit)."""
    audit_entry = {
        "id": secrets.token_hex(8),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "username": current_username(),
        "role": current_user().get("role", "user") if current_user() else "user",
        "citizen_id": str(updated_row["_id"]),
        "old_status": old_status,
        "new_status": str(updated_row["Status"]),
        "list_key": list_key,
    }

    with _data_file_lock(shared=False):
        if list_key:
            key = _safe_storage_key(list_key)
            _write_text_atomic(
                storage_path(key),
                json.dumps(dataframe_to_state(updated), ensure_ascii=False, indent=2) + "\n",
            )

        register_payload = _read_json_raw(MASTER_REFERENCE_REGISTER_PATH, {"cleared": False, "entries": []})
        register_state = _parse_master_register_payload(register_payload)
        register = list(register_state["entries"])  # type: ignore[arg-type]
        upsert_master_register_entry(updated_row, register)
        _write_text_atomic(
            MASTER_REFERENCE_REGISTER_PATH,
            json.dumps({"cleared": False, "entries": register}, ensure_ascii=False, indent=2) + "\n",
        )

        history = _read_json_raw(STATUS_HISTORY_PATH, {})
        if not isinstance(history, dict):
            history = {}
        upsert_history_entry(updated_row, history)
        _write_text_atomic(
            STATUS_HISTORY_PATH,
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        )

        audit_payload = _read_json_raw(AUDIT_LOG_PATH, {"entries": []})
        if isinstance(audit_payload, dict) and isinstance(audit_payload.get("entries"), list):
            entries = [entry for entry in audit_payload["entries"] if isinstance(entry, dict)]
        elif isinstance(audit_payload, list):
            entries = [entry for entry in audit_payload if isinstance(entry, dict)]
        else:
            entries = []
        entries.append(audit_entry)
        _write_text_atomic(
            AUDIT_LOG_PATH,
            json.dumps({"entries": entries[-MAX_AUDIT_ENTRIES:]}, ensure_ascii=False, indent=2) + "\n",
        )

    save_active_list(updated)
    _touch_master_sync_stamp()


def handle_citizen_status_change(citizen_id: str) -> None:
    widget_key = f"status_{citizen_id}"
    new_status = st.session_state.get(widget_key)
    if new_status is None:
        return

    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return

    mask = df["_id"] == citizen_id
    if not mask.any():
        return

    old_status = df.loc[mask, "Status"].iloc[0]
    if new_status == old_status:
        return

    updated = update_citizen_status(df, citizen_id, new_status)
    st.session_state.citizens_df = updated
    updated_row = updated[updated["_id"] == citizen_id].iloc[0]
    persist_citizen_status_change(
        updated=updated,
        updated_row=updated_row,
        old_status=str(old_status),
        list_key=st.session_state.get("list_key"),
    )
    st.session_state._skip_master_sync_once = True
    st.toast(t("status_saved"), icon="✅")


def _citizen_status_change_handler(citizen_id: str):
    def _handler() -> None:
        handle_citizen_status_change(citizen_id)

    return _handler


def render_citizen_card(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(status_pill_html(row["Status"], short=True), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_name"), row["Navn"], emphasized=True), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_address"), row["Adresse"]), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_phone"), row["Telefonnummer"]), unsafe_allow_html=True)

        current_index = STATUSES.index(row["Status"]) if row["Status"] in STATUSES else 0
        st.selectbox(
            t("change_status"),
            STATUSES,
            index=current_index,
            key=f"status_{row['_id']}",
            format_func=lambda s: status_label(s, short=True),
            on_change=_citizen_status_change_handler(row["_id"]),
        )

        if row["Status dato"]:
            st.caption(t("last_updated", date=row["Status dato"]))
        if row["Ring igen dato"]:
            st.caption(t("call_again_date", date=row["Ring igen dato"]))

        with st.expander(t("gdpr_citizen_title"), expanded=False):
            export_payload = collect_citizen_data_export(row)
            st.download_button(
                t("gdpr_export_citizen"),
                data=json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=t("gdpr_export_filename", citizen_id=str(row["_id"])),
                mime="application/json",
                key=f"export_{row['_id']}",
                use_container_width=True,
            )
            confirm_key = f"erase_confirm_{row['_id']}"
            if st.session_state.get(confirm_key):
                st.warning(t("gdpr_erase_warning"))
                col_cancel, col_confirm = st.columns(2)
                with col_cancel:
                    if st.button(t("gdpr_erase_cancel"), key=f"erase_cancel_{row['_id']}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with col_confirm:
                    if st.button(t("gdpr_erase_confirm"), key=f"erase_confirm_btn_{row['_id']}", use_container_width=True):
                        erase_citizen_data(row)
                        st.session_state.pop(confirm_key, None)
                        st.toast(t("gdpr_erase_done"), icon="✅")
                        st.rerun()
            elif st.button(t("gdpr_erase_citizen"), key=f"erase_{row['_id']}", use_container_width=True):
                st.session_state[confirm_key] = True
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
        initial_sidebar_state="collapsed",
    )
    inject_styles(st.session_state.get("theme_choice", "Browser standard"))

    if not st.session_state.get("authenticated"):
        prepare_cookie_reading()
        try_restore_auth_from_cookie()

    if not render_login():
        with st.sidebar:
            st.markdown(f"**{t('app_title')}**")
            st.caption(t("app_subtitle"))
        render_sidebar_settings()
        finish_page(show_pin=False)
        return

    if not ensure_authenticated_session():
        st.rerun()
        return

    ensure_auth_cookie_synced()

    ensure_user_data_loaded()
    if purged := st.session_state.pop("retention_purged_count", None):
        st.toast(t("admin_retention_purged", count=purged), icon="ℹ️")
    sync_session_df_with_master()

    render_page_navigation()

    df = st.session_state.citizens_df
    if st.session_state.get("active_page") not in ("account", "privacy") and (df is None or df.empty):
        st.title(t("app_title"))
        st.caption(t("app_subtitle"))
        render_upload_section()
        df = st.session_state.citizens_df
        if df is not None and not df.empty:
            st.rerun()
        render_sidebar_content()
        render_sidebar_settings()
        st.info(t("upload_get_started"))
        finish_page(show_pin=True)
        return

    render_sidebar_content()
    render_sidebar_settings()

    if st.session_state.get("active_page") == "account":
        render_account_page()
        save_active_session_metadata()
        finish_page(show_pin=True)
        return

    if st.session_state.get("active_page") == "privacy":
        render_privacy_page()
        finish_page(show_pin=True)
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
    finish_page(show_pin=True)


if __name__ == "__main__":
    main()
