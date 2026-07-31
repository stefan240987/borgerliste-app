from __future__ import annotations

from datetime import datetime, timedelta

from storage import configured_trial_days, trial_system_enabled


def effective_is_paid(user: dict) -> bool:
    if str(user.get("role", "user")) == "admin":
        return True
    if not trial_system_enabled():
        return True
    if "is_paid" not in user:
        return True
    return bool(user.get("is_paid"))


def parse_trial_ends_at(user: dict) -> datetime | None:
    raw = user.get("trial_ends_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def is_trial_expired(user: dict) -> bool:
    if not trial_system_enabled():
        return False
    if str(user.get("role", "user")) == "admin":
        return False
    if effective_is_paid(user):
        return False
    ends_at = parse_trial_ends_at(user)
    if ends_at is None:
        return False
    return datetime.now() >= ends_at


def trial_days_remaining(user: dict) -> int | None:
    if str(user.get("role", "user")) == "admin":
        return None
    if not trial_system_enabled():
        return None
    if effective_is_paid(user):
        return None
    ends_at = parse_trial_ends_at(user)
    if ends_at is None:
        return None
    remaining = (ends_at.date() - datetime.now().date()).days
    return max(0, remaining)


def format_trial_end_date(user: dict) -> str:
    ends_at = parse_trial_ends_at(user)
    if ends_at is None:
        return "—"
    return ends_at.strftime("%d-%m-%Y")


def build_new_user_license_fields(role: str) -> dict:
    if role == "admin":
        return {}
    now = datetime.now()
    days = configured_trial_days()
    return {
        "is_paid": False,
        "trial_ends_at": (now + timedelta(days=days)).isoformat(timespec="seconds"),
    }


def license_status_key(user: dict) -> str:
    if str(user.get("role", "user")) == "admin":
        return "license_status_admin"
    if effective_is_paid(user):
        return "license_status_paid"
    if is_trial_expired(user):
        return "license_status_expired"
    return "license_status_trial"


def should_show_license_badge(user: dict) -> bool:
    if str(user.get("role", "user")) == "admin":
        return False
    if not trial_system_enabled():
        return False
    return not effective_is_paid(user)


def sidebar_license_badge_text(user: dict) -> str | None:
    if not should_show_license_badge(user):
        return None
    from i18n import t

    if is_trial_expired(user):
        return t("sidebar_license_expired")
    days = trial_days_remaining(user)
    if days is None:
        return None
    return t("sidebar_license_trial", days=days)


def update_user_license(
    username: str,
    *,
    is_paid: bool | None = None,
    trial_ends_at: datetime | None = None,
) -> tuple[bool, str]:
    from auth import find_user, load_users, save_users
    from i18n import t

    user = find_user(username)
    if not user:
        return False, t("admin_user_license_not_found")

    users = load_users()
    changed = False
    for entry in users:
        if str(entry.get("username", "")).lower() != username.strip().lower():
            continue
        if is_paid is not None:
            entry["is_paid"] = is_paid
            changed = True
        if trial_ends_at is not None:
            entry["trial_ends_at"] = trial_ends_at.isoformat(timespec="seconds")
            changed = True
        break

    if not changed:
        return False, t("admin_user_license_not_found")

    save_users(users)
    return True, t("admin_user_license_saved", username=username)


def extend_user_trial(username: str, days: int) -> tuple[bool, str]:
    from auth import find_user

    user = find_user(username)
    if not user:
        from i18n import t

        return False, t("admin_user_license_not_found")

    ends_at = parse_trial_ends_at(user)
    base = ends_at if ends_at and ends_at > datetime.now() else datetime.now()
    new_end = base + timedelta(days=days)
    ok, message = update_user_license(username, is_paid=False, trial_ends_at=new_end)
    return ok, message
