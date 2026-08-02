from __future__ import annotations
import os
import re
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("BORGERLISTE_DATA_DIR", APP_ROOT / "data"))
LOGO_PATH = APP_ROOT / "assets" / "borgerliste-logo.svg"
STATUS_HISTORY_PATH = DATA_DIR / "status_history.json"
MASTER_REFERENCE_REGISTER_PATH = DATA_DIR / "master_reference_register.json"
USER_PREFERENCES_PATH = DATA_DIR / "user_preferences.json"
USERS_PATH = DATA_DIR / "users.json"
AUDIT_LOG_PATH = DATA_DIR / "audit_log.json"
FEEDBACK_PATH = DATA_DIR / "feedback.json"
USER_DATA_ROOT = DATA_DIR / "user_data"
LEGACY_ACTIVE_LIST_PARQUET = DATA_DIR / "active_borgerliste.parquet"
LEGACY_ACTIVE_LIST_CSV = DATA_DIR / "active_borgerliste.csv"
LEGACY_ACTIVE_SESSION_PATH = DATA_DIR / "active_session.json"
USER_ROLES = ("admin", "user")
MAX_AUDIT_ENTRIES = 10000
MAX_FEEDBACK_ENTRIES = 5000
MAX_FEEDBACK_TITLE_LENGTH = 120
MAX_FEEDBACK_MESSAGE_LENGTH = 4000
FEEDBACK_KINDS = ("bug", "suggestion")
FEEDBACK_STATUSES = ("open", "closed", "implemented", "rejected")
DEFAULT_FEEDBACK_STATUS = "open"
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
DATA_LOCK_TIMEOUT_SECONDS = 15
MASTER_SYNC_STAMP_PATH = DATA_DIR / ".master_sync_at"
MASTER_SYNC_INTERVAL_SECONDS = 60
APP_VERSION = "1.5.26"
DEFAULT_TRIAL_DAYS = 14
DEFAULT_PUBLIC_SIGNUP_ENABLED = True
MIN_TRIAL_DAYS = 1
MAX_TRIAL_DAYS = 365
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
PAGE_SIZE_OPTIONS: list[int | str] = [1, 10, 25, 50, 100, "Alle"]
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
        "card_shadow": "0 2px 8px rgba(0,0,0,0.08)",
        "card_border_subtle": "rgba(0,0,0,0.08)",
        "card_border": "#D6D3D1",
        "card_border_width": "1px",
        "card_gap": "1rem",
        "card_accent_width": "4px",
    },
    "Mørkt tema": {
        "bg": "#0F172A",
        "bg_secondary": "#1E293B",
        "input_bg": "#1E293B",
        "card_bg": "#1A2332",
        "text": "#F8FAFC",
        "text_muted": "#CBD5E1",
        "border": "#334155",
        "color_scheme": "dark",
        "card_shadow": "0 4px 16px rgba(0,0,0,0.35)",
        "card_border_subtle": "rgba(255,255,255,0.1)",
        "card_border": "#475569",
        "card_border_width": "2px",
        "card_gap": "1.25rem",
        "card_accent_width": "4px",
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
        "app_title": "Borgerflow",
        "app_subtitle": "Kontakt og opfølgning på borgere",
        "menu": "Menu",
        "language": "Sprog",
        "theme_light": "Lyst tema",
        "theme_dark": "Mørkt tema",
        "theme_browser": "Følger system (lys/mørk)",
        "gdpr_title": "Privatliv og datasikkerhed i Borgerflow",
        "gdpr_text": (
            "Borgerflow hjælper os med at holde styr på borgerkontakt på en tryg og overskuelig måde. "
            "Denne side forklarer i et sprog, der er til at forstå, hvordan vi passer på borgerens "
            "oplysninger, og hvad du som bruger skal være opmærksom på."
        ),
        "gdpr_section_roles": (
            "### 1. Hvem har ansvaret? (Roller & GDPR)\n\n"
            "- **Dataansvarlig:** Det er vores organisation, der har ansvaret for borgerens data "
            "og for at have hjemmel (lovligt grundlag) til kontakten.\n"
            "- **Systemets rolle:** Borgerflow er alene det digitale arbejdsredskab. "
            "Appen spørger ikke borgeren om samtykke — det håndteres af organisationen."
        ),
        "gdpr_section_data": (
            "### 2. Hvilke oplysninger gemmer vi (og hvad gemmer vi IKKE)?\n\n"
            "- **Persondata:** Navn, adresse og telefonnummer (gemmes krypteret).\n"
            "- **Kontakthistorik:** Status (fx *Ikke kontaktet*, *Accepteret*, *Ring igen*) "
            "samt dato og historik for opkald.\n"
            "- **CPR-numre gemmes ALDRIG:** Hvis en uploadet fil indeholder CPR-nummer, bruges det "
            "kun i et splintsekund under selve uploadet til at kontrollere dubletter. "
            "Det gemmes aldrig på serveren eller i databasen."
        ),
        "gdpr_section_security": (
            "### 3. Hvor sikkert er systemet? (Teknikken kort fortalt)\n\n"
            "- **Lokal og krypteret lagring:** Data gemmes på organisationens egen lukkede server "
            "(Docker-volume) og sendes aldrig til eksterne cloud-tjenester eller ud af landet. "
            "Persondata er krypteret i hvile (Fernet).\n"
            "- **Personligt login:** Alle har eget login med et stærkt, hashet kodeord (PBKDF2). "
            "Du bliver automatisk logget ud ved inaktivitet.\n"
            "- **Sporbarhed (Audit-log):** For at overholde reglerne om dokumentation gemmer systemet "
            "en log over, hvem der ændrer en borgerstatus og hvornår."
        ),
        "gdpr_section_rights": (
            "### 4. Sletning og borgerens rettigheder (Audit & Retention)\n\n"
            "- **Automatisk oprydning:** Borgere, der har været inaktive i en valgt periode "
            "(standard 24 mdr.), slettes automatisk.\n"
            "- **Retten til at blive glemt & Indsigt:** Administratorer kan med få klik eksportere "
            "en borgers data (JSON) eller slette borgeren permanent.\n"
            "- **Behandlingsfortegnelse (Art. 30):** Administratorer har adgang til en færdig oversigt "
            "over databehandlingen, som kan fremvises ved tilsyn."
        ),
        "gdpr_section_checklist": (
            "### 5. Tjekliste til dig som bruger (Sikker adfærd)\n\n"
            "- 🔒 Tjek at adresselinjen viser HTTPS (hængelås).\n"
            "- 🔑 Del aldrig dit password med kolleger — alle skal have deres eget login.\n"
            "- 📁 Slet Excel-filer fra din egen computer, når du har uploadet dem til Borgerflow.\n"
            "- 💾 Husk at IT/driftsansvarlig skal tage regelmæssig, krypteret backup "
            "af serverens `/data`-mappe."
        ),
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
        "admin_retention_help": (
            "Borgere uden opdateringer eller statusændringer i den valgte periode "
            "slettes automatisk fra systemet. Sæt til 0 for at deaktivere automatisk sletning."
        ),
        "admin_retention_saved": "Opbevaringsperiode gemt.",
        "admin_retention_invalid": "Angiv et helt tal mellem {min} og {max}.",
        "admin_retention_current": "Nuværende: {months} måneder (0 = deaktiveret).",
        "admin_retention_disabled": "Automatisk sletning er deaktiveret.",
        "admin_retention_purged": "{count} inaktive borgere blev slettet ved login.",
        "admin_deactivate_delete_data": "Slet brugerens gemte data",
        "admin_user_deactivated_data_deleted": "Bruger {username} deaktiveret og data slettet.",
        "admin_audit_col_id": "Borger-ID",
        "admin_gdpr_processing_title": "Behandlingsfortegnelse (Art. 30)",
        "admin_gdpr_retention_active": "Automatisk sletning efter {months} måneder uden aktivitet",
        "admin_gdpr_retention_disabled": "Deaktiveret (0 mdr.)",
        "admin_gdpr_processing_body": (
            "| Punkt | Beskrivelse |\n"
            "|---|---|\n"
            "| Behandlingsaktivitet | Opfølgning på borgerkontakt |\n"
            "| Kategorier af registrerede | Borgere på kontaktliste |\n"
            "| Kategorier af personoplysninger | Navn, adresse, telefon, kontaktstatus "
            "(CPR behandles kun midlertidigt i upload-sessionen og gemmes ikke) |\n"
            "| Modtagere | Autoriserede app-brugere i organisationen |\n"
            "| Overførsler til tredjelande | Ingen |\n"
            "| Opbevaring | {retention} |\n"
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
        "page_info_one": "Borger {current} af {total}",
        "page_size_label": "Vis pr. side",
        "page_size_all": "Alle pr. side",
        "page_size_one": "Én ad gangen",
        "page_size_n": "{n} pr. side",
        "change_status": "Skift status",
        "last_updated": "Sidst opdateret: {date}",
        "call_again_date": "Ring igen: {date}",
        "status_saved": "Status gemt",
        "status_save_error": "Kunne ikke gemme status. Prøv igen.",
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
        "nav_about": "Om Borgerflow",
        "nav_feedback": "Feedback",
        "sidebar_pin": "Fastgør menuen, så den ikke lukker automatisk",
        "sidebar_unpin": "Menu fastgjort — klik for at frigøre",
        "account_title": "Min konto",
        "about_title": "Om Borgerflow",
        "about_lead": "Denne applikation er skabt til at gøre opfølgning på borgere hurtig, enkel og overskuelig. I stedet for manuelle lister og Excel-ark giver appen dig et samlet digitalt arbejdsredskab til din borgerkontakt.",
        "about_bullet_1": "**Holde hurtigt overblik:** Se præcis hvilke borgere der mangler afklaring, har takket ja/nej eller skal ringes op igen.",
        "about_bullet_2": "**Registrere opkald med ét klik:** Gem status og noter med det samme, så du og dine kolleger aldrig ringer forgæves eller dobbelt.",
        "about_bullet_3": "**Sikre et smidigt borgerforløb:** Bevar overblikket over genopkald og aftaler uden risiko for, at borgere overses.",
        "feedback_title": "Feedback",
        "feedback_lead": "Har du fundet en fejl, eller har du et forslag til forbedring? Send det her — vi læser alle indsendelser.",
        "feedback_kind_label": "Type",
        "feedback_kind_bug": "Fejlrapport",
        "feedback_kind_suggestion": "Forbedringsforslag",
        "feedback_status_label": "Status",
        "feedback_title_label": "Titel",
        "feedback_message_label": "Beskrivelse",
        "feedback_submit": "Send feedback",
        "feedback_success": "Tak — din feedback er sendt.",
        "feedback_error_title": "Angiv en titel (maks. {max} tegn).",
        "feedback_error_message": "Angiv en beskrivelse (maks. {max} tegn).",
        "feedback_error_kind": "Vælg type.",
        "feedback_status_open": "Åben",
        "feedback_status_closed": "Lukket",
        "feedback_status_implemented": "Implementeret",
        "feedback_status_rejected": "Afvist",
        "feedback_mine_title": "Mine indsendelser",
        "feedback_mine_caption": "Status på din feedback opdateres, når en administrator behandler den.",
        "feedback_mine_empty": "Du har ikke sendt feedback endnu.",
        "account_profile_tab": "Profil",
        "account_admin_users_tab": "Brugere",
        "account_admin_master_tab": "Master-register",
        "account_admin_audit_tab": "Status-log",
        "account_admin_feedback_tab": "Feedback",
        "admin_feedback_title": "Brugerfeedback",
        "admin_feedback_caption": "Fejlrapporter og forbedringsforslag fra brugere.",
        "admin_feedback_empty": "Ingen feedback endnu.",
        "admin_feedback_all_kinds": "Alle typer",
        "admin_feedback_all_users": "Alle brugere",
        "admin_feedback_all_statuses": "Alle statusser",
        "admin_feedback_filter_kind": "Filtrer type",
        "admin_feedback_filter_user": "Filtrer bruger",
        "admin_feedback_filter_status": "Filtrer status",
        "admin_feedback_status_label": "Sæt status",
        "admin_feedback_status_saved": "Status opdateret.",
        "admin_feedback_status_error": "Kunne ikke opdatere status.",
        "admin_feedback_status_denied": "Kun administratorer kan ændre feedback-status.",
        "admin_feedback_col_time": "Tidspunkt",
        "admin_feedback_col_user": "Bruger",
        "admin_feedback_col_kind": "Type",
        "admin_feedback_col_title": "Titel",
        "admin_feedback_col_message": "Beskrivelse",
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
        "admin_create_user_btn": "+ Opret ny bruger",
        "admin_edit_user": "Rediger",
        "admin_edit_user_title": "Rediger bruger",
        "admin_users_col_username": "Bruger",
        "admin_users_col_role": "Rolle",
        "admin_users_col_municipalities": "Kommuner",
        "admin_users_col_license": "Licens",
        "admin_users_col_created": "Oprettet",
        "admin_users_col_actions": "Handlinger",
        "admin_edit_section_role": "Rolle & kommune",
        "admin_edit_section_license": "Licens & prøveforlængelse",
        "admin_edit_section_password": "Nulstil adgangskode",
        "admin_edit_section_danger": "Deaktiver konto",
        "admin_municipalities_none": "—",
        "admin_municipalities_coming_soon": "Kommune-tildeling er ikke tilgængelig endnu.",
        "admin_dialog_close": "Luk",
        "admin_create_user": "Opret bruger",
        "admin_new_username": "Brugernavn",
        "admin_new_password": "Adgangskode",
        "admin_new_role": "Rolle",
        "admin_create_submit": "Opret",
        "admin_users_list": "Eksisterende brugere",
        "admin_no_users": "Ingen brugere endnu.",
        "admin_deactivate": "Deaktiver",
        "admin_reactivate": "Aktiver igen",
        "admin_user_reactivated": "Bruger {username} er aktiveret igen.",
        "admin_user_already_active": "Bruger {username} er allerede aktiv.",
        "admin_user_deactivated_at": "Deaktiveret: {date}",
        "admin_cannot_deactivate_self": "Du kan ikke deaktivere din egen konto.",
        "admin_change_role": "Rolle",
        "admin_change_role_submit": "Gem rolle",
        "admin_user_role_updated": "Rolle for {username} er ændret til {role}.",
        "admin_cannot_change_own_role": "Du kan ikke ændre din egen rolle.",
        "admin_cannot_demote_last_admin": "Der skal være mindst én aktiv administrator.",
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
        "admin_trial_title": "Prøveperiode og licens",
        "admin_trial_enabled_label": "Trial-system aktiveret",
        "admin_trial_enabled_help": "Når slået fra, deaktiveres trial-validering for alle brugere.",
        "admin_trial_days_label": "Standard prøveperiode (dage)",
        "admin_trial_days_help": "Gælder nye brugere med rollen Bruger.",
        "admin_trial_days_saved": "Trial-indstillinger gemt.",
        "admin_trial_days_invalid": "Angiv et helt tal mellem {min} og {max} dage.",
        "admin_trial_current": "Trial-system: {status}. Standard prøveperiode: {days} dage.",
        "admin_trial_status_on": "aktiveret",
        "admin_trial_status_off": "deaktiveret",
        "account_license_title": "Licens og prøveperiode",
        "account_license_status": "Status",
        "account_license_expires": "Udløber",
        "account_license_days_remaining": "Dage tilbage",
        "account_license_days_value": "{days} dage",
        "account_license_expired_on": "Udløbet den {date}",
        "license_status_paid": "Købt / betalt licens",
        "license_status_trial": "Prøveperiode",
        "license_status_expired": "Prøveperiode udløbet",
        "license_status_admin": "Administrator",
        "sidebar_license_trial": "Prøve · {days} dage",
        "sidebar_license_expired": "Prøve udløbet",
        "trial_expired_title": "Prøveperiode udløbet",
        "trial_expired_body": (
            "Din prøveperiode udløb **{date}**. Du kan stadig logge ind, men adgang til "
            "borgerlisten er midlertidigt blokeret."
        ),
        "trial_expired_contact": "Kontakt en administrator for at opgradere til betalt licens.",
        "trial_expired_go_account": "Gå til Min konto",
        "admin_user_license_title": "Licens",
        "admin_user_is_paid": "Betalt licens",
        "admin_user_trial_ends": "Prøveperiode udløber",
        "admin_user_extend_trial": "Forlæng prøveperiode",
        "admin_user_extend_days": "+{days} dage",
        "admin_user_license_saved": "Licens opdateret for {username}.",
        "admin_user_license_not_found": "Bruger ikke fundet.",
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
        "login_tab": "Log ind",
        "login_hero_subtitle": "Effektiv borgerkontakt og opfølgning",
        "login_caption": "Sikker adgang til borger- og kontaktadministration",
        "login_password": "Adgangskode",
        "login_submit": "Log ind",
        "login_error": "Forkert brugernavn eller adgangskode.",
        "signup_tab": "Opret konto",
        "signup_title": "Opret konto",
        "signup_caption": "Start din gratis prøveperiode.",
        "signup_username_requirements": "Brugernavn: 2–32 tegn. Kun bogstaver, tal, _ og -.",
        "signup_password_requirements": "Adgangskode: mindst {min} tegn.",
        "signup_confirm_password": "Bekræft adgangskode",
        "signup_submit": "Opret konto",
        "signup_success": "Konto oprettet! Du kan nu logge ind.",
        "admin_public_signup_label": "Selvbetjent brugeroprettelse",
        "admin_public_signup_help": "Tillad besøgende at oprette en brugerkonto fra login-siden.",
        "admin_public_signup_saved": "Indstilling for brugeroprettelse gemt.",
        "admin_public_signup_current": "Selvbetjent brugeroprettelse: {status}.",
        "admin_public_signup_status_on": "aktiveret",
        "admin_public_signup_status_off": "deaktiveret",
        "status_not_contacted": "Ikke kontaktet endnu",
        "status_accepted": "Accepteret tilbud",
        "status_declined": "Afslået tilbud",
        "status_call_again": "Ring igen om 6 måneder",
        "status_short_not_contacted": "Ikke kontaktet",
        "status_short_accepted": "Accepteret",
        "status_short_declined": "Afslået",
        "status_short_call_again": "Ring igen (6 mdr.)",
        "col_name": "Navn",
        "col_personnummer": "Personnummer",
        "col_indsats_navn": "Indsats navn",
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
        "data_lock_timeout": (
            "Datalageret er låst af en anden proces (timeout efter {seconds}s). "
            "Stop andre Streamlit-/Docker-instanser og genstart appen."
        ),
    },
    "en": {
        "app_title": "Borgerflow",
        "app_subtitle": "Contact and follow-up on citizens",
        "menu": "Menu",
        "language": "Language",
        "theme_light": "Light theme",
        "theme_dark": "Dark theme",
        "theme_browser": "Follow system (light/dark)",
        "gdpr_title": "Privacy and data security in Borgerflow",
        "gdpr_text": (
            "Borgerflow helps us keep track of citizen contact in a safe and clear way. "
            "This page explains, in plain language, how we protect citizens' information "
            "and what you as a user need to be aware of."
        ),
        "gdpr_section_roles": (
            "### 1. Who is responsible? (Roles & GDPR)\n\n"
            "- **Data controller:** Our organisation is responsible for the citizen's data "
            "and for having a lawful basis for the contact.\n"
            "- **The system's role:** Borgerflow is only the digital work tool. "
            "The app does not ask the citizen for consent — that is handled by the organisation."
        ),
        "gdpr_section_data": (
            "### 2. What information do we store (and what do we NOT store)?\n\n"
            "- **Personal data:** Name, address and phone number (stored encrypted).\n"
            "- **Contact history:** Status (e.g. *Not contacted*, *Accepted*, *Call again*) "
            "as well as date and call history.\n"
            "- **National ID (CPR) is NEVER stored:** If an uploaded file contains a CPR number, "
            "it is used only for a split second during the upload itself to check for duplicates. "
            "It is never stored on the server or in the database."
        ),
        "gdpr_section_security": (
            "### 3. How secure is the system? (The tech in brief)\n\n"
            "- **Local and encrypted storage:** Data is stored on the organisation's own closed server "
            "(Docker volume) and is never sent to external cloud services or outside the country. "
            "Personal data is encrypted at rest (Fernet).\n"
            "- **Personal login:** Everyone has their own login with a strong, hashed password (PBKDF2). "
            "You are automatically logged out after inactivity.\n"
            "- **Traceability (audit log):** To meet documentation requirements, the system keeps a log "
            "of who changes a citizen status and when."
        ),
        "gdpr_section_rights": (
            "### 4. Erasure and citizens' rights (Audit & Retention)\n\n"
            "- **Automatic clean-up:** Citizens who have been inactive for a chosen period "
            "(default 24 months) are deleted automatically.\n"
            "- **Right to be forgotten & access:** Administrators can export a citizen's data (JSON) "
            "or permanently delete the citizen in a few clicks.\n"
            "- **Records of processing (Art. 30):** Administrators have access to a ready-made overview "
            "of the processing, which can be presented at an audit."
        ),
        "gdpr_section_checklist": (
            "### 5. Checklist for you as a user (Safe behaviour)\n\n"
            "- 🔒 Check that the address bar shows HTTPS (padlock).\n"
            "- 🔑 Never share your password with colleagues — everyone must have their own login.\n"
            "- 📁 Delete Excel files from your own computer once you have uploaded them to Borgerflow.\n"
            "- 💾 Remember that IT/operations must take regular, encrypted backups "
            "of the server's `/data` folder."
        ),
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
        "admin_retention_help": (
            "Citizens with no updates or status changes during the selected period "
            "are automatically deleted from the system. Set to 0 to disable automatic deletion."
        ),
        "admin_retention_saved": "Retention period saved.",
        "admin_retention_invalid": "Enter a whole number between {min} and {max}.",
        "admin_retention_current": "Current: {months} months (0 = disabled).",
        "admin_retention_disabled": "Automatic deletion is disabled.",
        "admin_retention_purged": "{count} inactive citizens were deleted at login.",
        "admin_deactivate_delete_data": "Delete user's stored data",
        "admin_user_deactivated_data_deleted": "User {username} deactivated and data deleted.",
        "admin_audit_col_id": "Citizen ID",
        "admin_gdpr_processing_title": "Processing record (Art. 30)",
        "admin_gdpr_retention_active": "Automatic deletion after {months} months without activity",
        "admin_gdpr_retention_disabled": "Disabled (0 mo.)",
        "admin_gdpr_processing_body": (
            "| Item | Description |\n"
            "|---|---|\n"
            "| Processing activity | Citizen contact follow-up |\n"
            "| Data subject categories | Citizens on contact list |\n"
            "| Personal data categories | Name, address, phone, contact status "
            "(CPR is only processed temporarily in the upload session and is not stored) |\n"
            "| Recipients | Authorised app users in the organisation |\n"
            "| Transfers to third countries | None |\n"
            "| Retention | {retention} |\n"
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
        "page_info_one": "Citizen {current} of {total}",
        "page_size_label": "Rows per page",
        "page_size_all": "All rows",
        "page_size_one": "One at a time",
        "page_size_n": "{n} per page",
        "change_status": "Change status",
        "last_updated": "Last updated: {date}",
        "call_again_date": "Call again: {date}",
        "status_saved": "Status saved",
        "status_save_error": "Could not save status. Please try again.",
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
        "nav_about": "About Borgerflow",
        "nav_feedback": "Feedback",
        "sidebar_pin": "Pin menu to keep it open",
        "sidebar_unpin": "Menu pinned — click to unpin",
        "account_title": "My account",
        "about_title": "About Borgerflow",
        "about_lead": "This application is designed to make citizen follow-up fast, simple and clear. Instead of manual lists and Excel spreadsheets, the app gives you a unified digital tool for your citizen contact.",
        "about_bullet_1": "**Keep a quick overview:** See exactly which citizens need clarification, have said yes/no, or need to be called again.",
        "about_bullet_2": "**Log calls with one click:** Save status and notes instantly, so you and your colleagues never call in vain or twice.",
        "about_bullet_3": "**Ensure a smooth citizen journey:** Keep track of callbacks and appointments without risking that citizens are overlooked.",
        "feedback_title": "Feedback",
        "feedback_lead": "Found a bug, or have an idea for improvement? Send it here — we read every submission.",
        "feedback_kind_label": "Type",
        "feedback_kind_bug": "Bug report",
        "feedback_kind_suggestion": "Improvement suggestion",
        "feedback_status_label": "Status",
        "feedback_title_label": "Title",
        "feedback_message_label": "Description",
        "feedback_submit": "Send feedback",
        "feedback_success": "Thank you — your feedback has been sent.",
        "feedback_error_title": "Please enter a title (max {max} characters).",
        "feedback_error_message": "Please enter a description (max {max} characters).",
        "feedback_error_kind": "Please select a type.",
        "feedback_status_open": "Open",
        "feedback_status_closed": "Closed",
        "feedback_status_implemented": "Implemented",
        "feedback_status_rejected": "Rejected",
        "feedback_mine_title": "My submissions",
        "feedback_mine_caption": "The status of your feedback updates when an administrator reviews it.",
        "feedback_mine_empty": "You have not submitted any feedback yet.",
        "account_profile_tab": "Profile",
        "account_admin_users_tab": "Users",
        "account_admin_master_tab": "Master register",
        "account_admin_audit_tab": "Status log",
        "account_admin_feedback_tab": "Feedback",
        "admin_feedback_title": "User feedback",
        "admin_feedback_caption": "Bug reports and improvement suggestions from users.",
        "admin_feedback_empty": "No feedback yet.",
        "admin_feedback_all_kinds": "All types",
        "admin_feedback_all_users": "All users",
        "admin_feedback_all_statuses": "All statuses",
        "admin_feedback_filter_kind": "Filter type",
        "admin_feedback_filter_user": "Filter user",
        "admin_feedback_filter_status": "Filter status",
        "admin_feedback_status_label": "Set status",
        "admin_feedback_status_saved": "Status updated.",
        "admin_feedback_status_error": "Could not update status.",
        "admin_feedback_status_denied": "Only administrators can change feedback status.",
        "admin_feedback_col_time": "Time",
        "admin_feedback_col_user": "User",
        "admin_feedback_col_kind": "Type",
        "admin_feedback_col_title": "Title",
        "admin_feedback_col_message": "Description",
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
        "admin_create_user_btn": "+ Create new user",
        "admin_edit_user": "Edit",
        "admin_edit_user_title": "Edit user",
        "admin_users_col_username": "User",
        "admin_users_col_role": "Role",
        "admin_users_col_municipalities": "Municipalities",
        "admin_users_col_license": "Licence",
        "admin_users_col_created": "Created",
        "admin_users_col_actions": "Actions",
        "admin_edit_section_role": "Role & municipality",
        "admin_edit_section_license": "Licence & trial extension",
        "admin_edit_section_password": "Reset password",
        "admin_edit_section_danger": "Deactivate account",
        "admin_municipalities_none": "—",
        "admin_municipalities_coming_soon": "Municipality assignment is not available yet.",
        "admin_dialog_close": "Close",
        "admin_create_user": "Create user",
        "admin_new_username": "Username",
        "admin_new_password": "Password",
        "admin_new_role": "Role",
        "admin_create_submit": "Create",
        "admin_users_list": "Existing users",
        "admin_no_users": "No users yet.",
        "admin_deactivate": "Deactivate",
        "admin_reactivate": "Reactivate",
        "admin_user_reactivated": "User {username} has been reactivated.",
        "admin_user_already_active": "User {username} is already active.",
        "admin_user_deactivated_at": "Deactivated: {date}",
        "admin_cannot_deactivate_self": "You cannot deactivate your own account.",
        "admin_change_role": "Role",
        "admin_change_role_submit": "Save role",
        "admin_user_role_updated": "Role for {username} changed to {role}.",
        "admin_cannot_change_own_role": "You cannot change your own role.",
        "admin_cannot_demote_last_admin": "At least one active administrator is required.",
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
        "admin_trial_title": "Trial and licence",
        "admin_trial_enabled_label": "Trial system enabled",
        "admin_trial_enabled_help": "When disabled, trial validation is turned off for all users.",
        "admin_trial_days_label": "Default trial period (days)",
        "admin_trial_days_help": "Applies to new users with the User role.",
        "admin_trial_days_saved": "Trial settings saved.",
        "admin_trial_days_invalid": "Enter a whole number between {min} and {max} days.",
        "admin_trial_current": "Trial system: {status}. Default trial period: {days} days.",
        "admin_trial_status_on": "enabled",
        "admin_trial_status_off": "disabled",
        "account_license_title": "Licence and trial",
        "account_license_status": "Status",
        "account_license_expires": "Expires",
        "account_license_days_remaining": "Days remaining",
        "account_license_days_value": "{days} days",
        "account_license_expired_on": "Expired on {date}",
        "license_status_paid": "Paid licence",
        "license_status_trial": "Trial period",
        "license_status_expired": "Trial expired",
        "license_status_admin": "Administrator",
        "sidebar_license_trial": "Trial · {days} days",
        "sidebar_license_expired": "Trial expired",
        "trial_expired_title": "Trial period expired",
        "trial_expired_body": (
            "Your trial period expired on **{date}**. You can still sign in, but access to "
            "the citizen list is temporarily blocked."
        ),
        "trial_expired_contact": "Contact an administrator to upgrade to a paid licence.",
        "trial_expired_go_account": "Go to My account",
        "admin_user_license_title": "Licence",
        "admin_user_is_paid": "Paid licence",
        "admin_user_trial_ends": "Trial expires",
        "admin_user_extend_trial": "Extend trial",
        "admin_user_extend_days": "+{days} days",
        "admin_user_license_saved": "Licence updated for {username}.",
        "admin_user_license_not_found": "User not found.",
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
        "login_tab": "Sign in",
        "login_hero_subtitle": "Effective citizen contact and follow-up",
        "login_caption": "Secure access to citizen and contact administration",
        "login_password": "Password",
        "login_submit": "Sign in",
        "login_error": "Incorrect username or password.",
        "signup_tab": "Create account",
        "signup_title": "Create account",
        "signup_caption": "Start your free trial.",
        "signup_username_requirements": "Username: 2–32 characters. Letters, numbers, _ and - only.",
        "signup_password_requirements": "Password: at least {min} characters.",
        "signup_confirm_password": "Confirm password",
        "signup_submit": "Create account",
        "signup_success": "Account created! You can now sign in.",
        "admin_public_signup_label": "Self-service sign-up",
        "admin_public_signup_help": "Allow visitors to create a user account from the sign-in page.",
        "admin_public_signup_saved": "Sign-up setting saved.",
        "admin_public_signup_current": "Self-service sign-up: {status}.",
        "admin_public_signup_status_on": "enabled",
        "admin_public_signup_status_off": "disabled",
        "status_not_contacted": "Not contacted yet",
        "status_accepted": "Offer accepted",
        "status_declined": "Offer declined",
        "status_call_again": "Call again in 6 months",
        "status_short_not_contacted": "Not contacted",
        "status_short_accepted": "Accepted",
        "status_short_declined": "Declined",
        "status_short_call_again": "Call again (6 mo.)",
        "col_name": "Name",
        "col_personnummer": "National ID (CPR)",
        "col_indsats_navn": "Intervention name",
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
        "data_lock_timeout": (
            "The data store is locked by another process (timeout after {seconds}s). "
            "Stop other Streamlit/Docker instances and restart the app."
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
    "Adresse": ["adresse", "address", "vej", "gade", "by", "by/adresse", "byen"],
    "Telefonnummer": [
        "telefon", "telefonnummer", "tlf", "tlfnr", "mobil", "phone", "telefon nr", "telefon nr.",
    ],
}
TRANSIENT_COLUMN_ALIASES = {
    "Personnummer": [
        "personnummer", "cpr", "cpr-nr.", "cpr-nr", "cpr nr", "cpr nr.",
    ],
    "Indsats navn": [
        "indsats navn", "indsats_navn", "indsatsnavn",
    ],
}
TRANSIENT_COLUMNS = ("Personnummer", "Indsats navn")
DISPLAY_COLUMNS = [
    "Navn", "Adresse", "Telefonnummer", "Status", "Status dato", "Ring igen dato",
]
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1", "iso-8859-1")
MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "ï¿½", "�")
DANISH_CHARS = set("æøåÆØÅ")
