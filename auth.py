from __future__ import annotations
import base64
import hashlib
import html
import json
import os
import secrets
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from config import *  # noqa: F403
from i18n import t
from storage import (
    _chmod_sensitive, _cookie_secure_flag, _load_json_file, _save_json_file, clear_active_list,
    delete_user_data, load_app_settings, public_signup_enabled, save_app_settings,
    configured_session_idle_minutes, session_idle_timeout_seconds,
)


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

    from licensing import build_new_user_license_fields

    salt, password_hash = hash_password(password)
    users = load_users()
    new_user: dict = {
        "username": clean_username,
        "salt": salt,
        "password_hash": password_hash,
        "role": role,
        "active": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    new_user.update(build_new_user_license_fields(role))
    users.append(new_user)
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


def reactivate_user_account(username: str) -> tuple[bool, str]:
    users = load_users()
    changed = False
    for user in users:
        if str(user.get("username", "")).lower() == username.strip().lower():
            if user.get("active", True):
                return False, t("admin_user_already_active", username=username)
            user["active"] = True
            user.pop("deactivated_at", None)
            changed = True
            break
    if not changed:
        return False, t("admin_user_invalid", min=MIN_PASSWORD_LENGTH)
    save_users(users)
    return True, t("admin_user_reactivated", username=username)


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


def update_user_role(username: str, role: str) -> tuple[bool, str]:
    if not is_admin():
        return False, t("master_delete_admin_only")
    clean = username.strip()
    if role not in USER_ROLES:
        return False, t("admin_user_invalid", min=MIN_PASSWORD_LENGTH)
    if clean.lower() == current_username().lower():
        return False, t("admin_cannot_change_own_role")

    users = load_users()
    target: dict | None = None
    for user in users:
        if str(user.get("username", "")).lower() == clean.lower():
            target = user
            break
    if not target or not target.get("active", True):
        return False, t("admin_user_license_not_found")

    old_role = str(target.get("role", "user"))
    if old_role == role:
        return True, t("admin_user_role_updated", username=clean, role=role_label(role))

    if old_role == "admin" and role != "admin":
        active_admins = sum(
            1
            for user in users
            if user.get("active", True) and str(user.get("role", "user")) == "admin"
        )
        if active_admins <= 1:
            return False, t("admin_cannot_demote_last_admin")

    target["role"] = role
    if role == "admin":
        target.pop("is_paid", None)
        target.pop("trial_ends_at", None)
    elif "is_paid" not in target:
        from licensing import build_new_user_license_fields

        target.update(build_new_user_license_fields("user"))

    save_users(users)

    sessions = _load_auth_sessions()
    changed = False
    for entry in sessions.values():
        if str(entry.get("username", "")).lower() == clean.lower():
            entry["role"] = role
            changed = True
    if changed:
        _save_auth_sessions(sessions)

    return True, t("admin_user_role_updated", username=clean, role=role_label(role))


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


def check_auth_rate_limit(*, action: str = "login") -> tuple[bool, int]:
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


def check_login_rate_limit() -> tuple[bool, int]:
    return check_auth_rate_limit(action="login")


def record_failed_auth(*, action: str = "login") -> None:
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


def record_failed_login() -> None:
    record_failed_auth(action="login")


def clear_auth_attempts(*, action: str = "login") -> None:
    client = _client_ip()
    attempts = _load_login_attempts()
    if client in attempts:
        attempts.pop(client, None)
        _save_login_attempts(attempts)


def clear_login_attempts() -> None:
    clear_auth_attempts(action="login")


def verify_admin_master_delete(password: str) -> bool:
    """Kun aktive administratorer kan slette master-register — med egen adgangskode."""
    if not is_admin():
        return False
    user = find_user(current_username())
    if not user or not user.get("active", True) or user.get("role") != "admin":
        return False
    return verify_password(password, str(user.get("salt", "")), str(user.get("password_hash", "")))


def _inject_session_cookie_script(*, action: str, token: str = "") -> None:
    """Sæt eller slet session-cookie uden CookieManager-komponent."""
    signature = f"{action}|{token}"
    if st.session_state.get("_session_cookie_script_sig") == signature:
        return
    st.session_state._session_cookie_script_sig = signature

    name = SESSION_COOKIE_NAME
    if action == "set":
        max_age = session_max_age_seconds()
        secure = _cookie_secure_flag()
        secure_js = "true" if secure else "false"
        script = f"""
        (function() {{
            const name = {json.dumps(name)};
            const value = {json.dumps(token)};
            const maxAge = {max_age};
            const secure = {secure_js};
            let cookie = name + "=" + encodeURIComponent(value) + "; path=/; max-age=" + maxAge + "; SameSite=Lax";
            if (secure) cookie += "; Secure";
            window.parent.document.cookie = cookie;
        }})();
        """
    else:
        script = f"""
        (function() {{
            const name = {json.dumps(name)};
            window.parent.document.cookie = name + "=; path=/; max-age=0; SameSite=Lax";
        }})();
        """
    components.html(f"<script>{script}</script>", height=0, width=0)


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
    if st.session_state.get("_idle_reload_expires_ms") == expires_ms:
        return
    st.session_state._idle_reload_expires_ms = expires_ms
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
        if try_restore_auth_from_cookie():
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


def _canonical_session_token_for_user(username: str, sessions: dict[str, dict]) -> str | None:
    """Seneste gyldige session-token for bruger (nyeste created_at)."""
    needle = username.strip().lower()
    candidates: list[tuple[str, datetime]] = []
    for token, entry in sessions.items():
        if str(entry.get("username", "")).lower() != needle:
            continue
        if _session_is_expired(entry):
            continue
        stamps = _session_timestamps(entry)
        if stamps is None:
            continue
        created, _ = stamps
        candidates.append((token, created))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def _prune_duplicate_user_sessions(sessions: dict[str, dict]) -> bool:
    """Behold kun seneste session pr. bruger."""
    by_user: dict[str, list[str]] = {}
    for token, entry in sessions.items():
        if _session_is_expired(entry):
            continue
        user = str(entry.get("username", "")).lower()
        by_user.setdefault(user, []).append(token)

    changed = False
    for user, tokens in by_user.items():
        if len(tokens) <= 1:
            continue
        canonical = _canonical_session_token_for_user(user, sessions)
        for token in tokens:
            if token != canonical:
                sessions.pop(token, None)
                changed = True
    return changed


def prune_expired_auth_sessions() -> None:
    sessions = _load_auth_sessions()
    changed = False
    for token in list(sessions.keys()):
        if _session_is_expired(sessions[token]):
            sessions.pop(token, None)
            changed = True
    if _prune_duplicate_user_sessions(sessions):
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
    revoke_user_sessions(str(account["username"]))
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

    canonical = _canonical_session_token_for_user(account["username"], sessions)
    if canonical != token:
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
    _inject_session_cookie_script(action="set", token=token)


def clear_persistent_session_cookie() -> None:
    st.session_state.pop("_session_cookie_script_sig", None)
    _inject_session_cookie_script(action="clear")


def _session_cookie_token() -> str | None:
    """Læs session-cookie synkront fra browser-request."""
    try:
        cookies = st.context.cookies
        if cookies and SESSION_COOKIE_NAME in cookies:
            return str(cookies[SESSION_COOKIE_NAME])
    except Exception:
        pass
    return None


def restore_auth_from_cookie_if_needed() -> bool:
    """Gendan login fra cookie når session state mangler auth."""
    if st.session_state.get("authenticated") and st.session_state.get("auth_token"):
        return True
    return try_restore_auth_from_cookie()


def try_restore_auth_from_cookie() -> bool:
    """Gendan login fra cookie når session state er tom (kun kaldt fra main())."""
    token = _session_cookie_token()
    if not token:
        return False

    # validate_persistent_session fjerner udløbne entries — hent ejer før flush.
    entry = _load_auth_sessions().get(str(token))
    cookie_username = None
    if isinstance(entry, dict) and entry.get("username"):
        cookie_username = str(entry["username"])

    account = validate_persistent_session(str(token), touch=True)
    if not account:
        # Idle-/cookie-udløb skal GDPR-flushe listen — ikke kun fjerne cookien.
        logout_user(username=cookie_username, token=str(token))
        st.session_state.session_expired_notice = True
        return False

    st.session_state.authenticated = True
    st.session_state.current_user = account
    st.session_state.auth_token = str(token)
    return True


def ensure_auth_cookie_synced() -> None:
    """Synkroniser browser-cookie efter vellykket login."""
    token = st.session_state.get("auth_token")
    if not token or not st.session_state.get("authenticated"):
        return
    if (
        st.session_state.get("cookie_synced_for_token") == token
        and _session_cookie_token() == str(token)
    ):
        return
    set_persistent_session_cookie(str(token))
    st.session_state.cookie_synced_for_token = token


def logout_user(*, username: str | None = None, token: str | None = None) -> None:
    """Log ud og flush aktiv borgerliste (GDPR).

    Ved idle-reload er session_state ofte tom, mens brugernavn kun findes i
    cookie-sessionen — derfor kan username/token sendes eksplicit.
    """
    owner = username
    if owner is None and current_user():
        owner = current_username()
    if owner == "unknown":
        owner = None

    list_key = st.session_state.get("list_key")
    session_token = token if token is not None else st.session_state.get("auth_token")
    if session_token and not owner:
        entry = _load_auth_sessions().get(str(session_token))
        if isinstance(entry, dict) and entry.get("username"):
            owner = str(entry["username"])

    if session_token:
        revoke_persistent_session(str(session_token))
    clear_persistent_session_cookie()
    clear_active_list(username=owner, list_key=list_key)
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.auth_token = None
    st.session_state.cookie_synced_for_token = None
    st.session_state.pop("_session_cookie_script_sig", None)
    st.session_state.pop("_idle_reload_expires_ms", None)
    st.session_state.active_page = "borgerliste"
    st.session_state.account_tab = "profile"
    st.session_state.user_data_loaded_for = None
    for key in ("page", "tab"):
        if key in st.query_params:
            del st.query_params[key]


def _logo_base64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def _login_logo_html() -> str:
    if not LOGO_PATH.exists():
        return ""
    return (
        f'<div class="login-logo-wrap">'
        f'<img src="data:image/svg+xml;base64,{_logo_base64()}" alt="{html.escape(t("app_title"))}"/>'
        f"</div>"
    )


def _render_login_card_block(*, allowed: bool) -> None:
    st.markdown(
        f'<div class="login-hero">{_login_logo_html()}'
        f'<p class="login-brand-title">{html.escape(t("app_title"))}</p>'
        f'<p class="login-brand-subtitle">{html.escape(t("login_hero_subtitle"))}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if not allowed:
        return

    with st.container(border=True):
        if public_signup_enabled():
            tab_labels = [t("login_tab"), t("signup_tab")]
            active_tab = st.session_state.get("_login_active_tab")
            default_tab = active_tab if active_tab in tab_labels else None
            login_tab, signup_tab = st.tabs(tab_labels, default=default_tab)
            with login_tab:
                _render_login_form(show_heading=True)
            with signup_tab:
                _render_signup_form()
            if active_tab in tab_labels:
                _inject_login_tab_select(active_tab)
                st.session_state.pop("_login_active_tab", None)
        else:
            _render_login_form()


def _process_login_submit(username: str, password: str) -> None:
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
    record_failed_login()
    st.error(t("login_error"))


def _inject_login_tab_select(tab_label: str) -> None:
    """Vælg login/signup-fane efter signup (st.tabs har ikke key i Streamlit 1.50)."""
    label_json = json.dumps(tab_label, ensure_ascii=False)
    components.html(
        f"""<script>
(function () {{
  const targetLabel = {label_json};
  const doc = window.parent.document;
  function selectTab() {{
    for (const tab of doc.querySelectorAll('[data-testid="stTabs"] [role="tab"]')) {{
      if ((tab.textContent || "").trim() !== targetLabel) continue;
      if (tab.getAttribute("aria-selected") === "true") return;
      tab.click();
      return;
    }}
  }}
  selectTab();
  const observer = new MutationObserver(selectTab);
  observer.observe(doc.body, {{ childList: true, subtree: true }});
  window.setTimeout(() => observer.disconnect(), 5000);
}})();
</script>""",
        height=0,
        width=0,
    )


def _render_login_form(*, show_heading: bool = True) -> None:
    if show_heading:
        st.markdown(f"### {t('login_title')}")
        st.caption(t("login_caption"))

    if st.session_state.pop("_signup_success_notice", False):
        st.success(t("signup_success"))

    with st.form("login_form"):
        username = st.text_input(t("login_username"))
        password = st.text_input(t("login_password"), type="password")
        submitted = st.form_submit_button(t("login_submit"), type="primary", use_container_width=True)

    if submitted:
        _process_login_submit(username, password)


def _render_signup_form() -> None:
    st.markdown(f"### {t('signup_title')}")
    st.caption(t("signup_caption"))

    form_version = st.session_state.get("_signup_form_version", 0)
    with st.form(f"signup_form_{form_version}", clear_on_submit=True):
        username = st.text_input(
            t("login_username"),
            help=t("signup_username_requirements"),
        )
        password = st.text_input(
            t("login_password"),
            type="password",
            help=t("signup_password_requirements", min=MIN_PASSWORD_LENGTH),
        )
        confirm_password = st.text_input(t("signup_confirm_password"), type="password")
        submitted = st.form_submit_button(t("signup_submit"), type="primary", use_container_width=True)

    if submitted:
        if not validate_username(username):
            record_failed_auth(action="signup")
            st.error(t("admin_username_invalid"))
            return
        if not validate_password_strength(password):
            record_failed_auth(action="signup")
            st.error(t("admin_password_weak", min=MIN_PASSWORD_LENGTH))
            return
        if password != confirm_password:
            record_failed_auth(action="signup")
            st.error(t("account_password_mismatch"))
            return

        ok, message = create_user_account(username, password, role="user")
        if ok:
            clear_auth_attempts(action="signup")
            st.session_state.pop("session_expired_notice", None)
            st.session_state._signup_success_notice = True
            st.session_state._login_active_tab = t("login_tab")
            st.session_state._signup_form_version = form_version + 1
            st.rerun()
        record_failed_auth(action="signup")
        st.error(message)


def render_login() -> bool:
    ensure_default_admin()

    if st.session_state.get("authenticated"):
        if not st.session_state.get("auth_token"):
            if not try_restore_auth_from_cookie():
                logout_user()
                return False
        if refresh_session_user():
            token = st.session_state.get("auth_token")
            if token:
                account = validate_persistent_session(str(token), touch=True)
                if account is None:
                    logout_user()
                    st.session_state.session_expired_notice = True
                    return False
                st.session_state.current_user = account
            return True
        logout_user()
        return False

    session_expired = st.session_state.pop("session_expired_notice", False)

    if notice := st.session_state.pop("_bootstrap_notice_text", None):
        st.info(notice)

    allowed, minutes = check_login_rate_limit()
    st.markdown('<div id="login-page-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div id="login-card-anchor"></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([0.65, 1, 0.65])
    with center:
        if session_expired:
            st.warning(t("login_session_expired"))

        if not allowed:
            st.error(t("login_locked_out", minutes=minutes))
        else:
            _render_login_card_block(allowed=True)

    return False

