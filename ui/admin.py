from __future__ import annotations
import html
from datetime import datetime
import pandas as pd
import streamlit as st
from config import (
    MAX_RETENTION_MONTHS, MAX_TRIAL_DAYS, MIN_PASSWORD_LENGTH, MIN_RETENTION_MONTHS,
    MIN_SESSION_IDLE_MINUTES, MAX_SESSION_IDLE_MINUTES, MIN_TRIAL_DAYS, USER_ROLES,
)
from auth import (
    admin_reset_user_password, create_user_account, current_user, current_username,
    deactivate_user_account, get_user_record, is_admin, load_users,
    role_label, update_user_password, verify_admin_master_delete,
)
from i18n import status_label, t
from licensing import (
    effective_is_paid, extend_user_trial, format_trial_end_date, is_trial_expired,
    license_status_key, parse_trial_ends_at, trial_days_remaining, update_user_license,
)
from matching import (
    clear_master_register, load_master_register, maybe_sync_master_from_all_user_data,
)
from storage import (
    append_audit_log, apply_data_retention, build_citizen_label_map, configured_retention_months,
    configured_session_idle_minutes, configured_trial_days, load_audit_log, public_signup_enabled,
    save_app_settings, trial_system_enabled,
)
from ui.common import account_tab_specs, inject_account_tab_url_sync, resolve_account_tab_default_label


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

    if str(user.get("role", "user")) != "admin" and trial_system_enabled():
        st.markdown(f"#### {t('account_license_title')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input(
                t("account_license_status"),
                value=t(license_status_key(record)),
                disabled=True,
            )
        with col2:
            st.text_input(
                t("account_license_expires"),
                value=format_trial_end_date(record) if not effective_is_paid(record) else "—",
                disabled=True,
            )
        with col3:
            days = trial_days_remaining(record)
            if effective_is_paid(record):
                remaining_text = "—"
            elif is_trial_expired(record):
                remaining_text = t("account_license_expired_on", date=format_trial_end_date(record))
            elif days is not None:
                remaining_text = t("account_license_days_value", days=days)
            else:
                remaining_text = "—"
            st.text_input(t("account_license_days_remaining"), value=remaining_text, disabled=True)

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

    st.markdown(f"#### {t('admin_trial_title')}")
    trial_enabled = trial_system_enabled()
    trial_days = configured_trial_days()
    st.caption(
        t(
            "admin_trial_current",
            status=t("admin_trial_status_on" if trial_enabled else "admin_trial_status_off"),
            days=trial_days,
        )
    )

    with st.form("admin_trial_settings_form"):
        enabled = st.checkbox(
            t("admin_trial_enabled_label"),
            value=trial_enabled,
            help=t("admin_trial_enabled_help"),
        )
        default_days = st.number_input(
            t("admin_trial_days_label"),
            min_value=MIN_TRIAL_DAYS,
            max_value=MAX_TRIAL_DAYS,
            value=trial_days,
            step=1,
            help=t("admin_trial_days_help"),
        )
        submitted = st.form_submit_button(t("admin_session_save"), use_container_width=True)
        if submitted:
            try:
                days = int(default_days)
            except (TypeError, ValueError):
                days = -1
            if not MIN_TRIAL_DAYS <= days <= MAX_TRIAL_DAYS:
                st.error(t("admin_trial_days_invalid", min=MIN_TRIAL_DAYS, max=MAX_TRIAL_DAYS))
            else:
                save_app_settings(trial_system_enabled=enabled, default_trial_days=days)
                st.success(t("admin_trial_days_saved"))
                st.rerun()

    signup_enabled = public_signup_enabled()
    st.markdown(f"#### {t('admin_public_signup_label')}")
    st.caption(
        t(
            "admin_public_signup_current",
            status=t("admin_public_signup_status_on" if signup_enabled else "admin_public_signup_status_off"),
        )
    )
    st.caption(t("admin_public_signup_help"))

    with st.form("admin_public_signup_form"):
        enabled = st.checkbox(
            t("admin_public_signup_label"),
            value=signup_enabled,
            help=t("admin_public_signup_help"),
        )
        submitted = st.form_submit_button(t("admin_session_save"), use_container_width=True)
        if submitted:
            save_app_settings(public_signup_enabled=enabled)
            st.success(t("admin_public_signup_saved"))
            st.rerun()


def _render_admin_user_license_controls(username: str, user: dict) -> None:
    if str(user.get("role", "user")) == "admin":
        st.caption(t("license_status_admin"))
        return

    status = t(license_status_key(user))
    expires = format_trial_end_date(user) if not effective_is_paid(user) else "—"
    st.caption(f"{t('account_license_status')}: **{status}** · {t('account_license_expires')}: {expires}")

    with st.expander(t("admin_user_license_title"), expanded=False):
        is_paid = st.checkbox(
            t("admin_user_is_paid"),
            value=effective_is_paid(user),
            key=f"license_paid_{username}",
        )
        current_end = parse_trial_ends_at(user)
        default_date = current_end.date() if current_end else datetime.now().date()
        new_date = st.date_input(
            t("admin_user_trial_ends"),
            value=default_date,
            key=f"license_date_{username}",
            disabled=is_paid,
        )

        extend_cols = st.columns(3)
        for col, extra_days in zip(extend_cols, (7, 14, 30)):
            with col:
                if st.button(
                    t("admin_user_extend_days", days=extra_days),
                    key=f"extend_{extra_days}_{username}",
                    use_container_width=True,
                    disabled=is_paid,
                ):
                    ok, message = extend_user_trial(username, extra_days)
                    if ok:
                        st.toast(message, icon="✅")
                        st.rerun()
                    st.error(message)

        if st.button(t("admin_session_save"), key=f"license_save_{username}", use_container_width=True):
            if is_paid:
                ok, message = update_user_license(username, is_paid=True)
            else:
                end_dt = datetime(new_date.year, new_date.month, new_date.day, 23, 59, 59)
                ok, message = update_user_license(
                    username,
                    is_paid=False,
                    trial_ends_at=end_dt,
                )
            if ok:
                st.toast(message, icon="✅")
                st.rerun()
            st.error(message)


def render_admin_users_section() -> None:
    st.markdown(f"#### {t('admin_users_title')}")

    if notice := st.session_state.pop("_admin_user_created_notice", None):
        st.success(notice)

    with st.expander(t("admin_create_user"), expanded=False):
        with st.form("create_user_form", clear_on_submit=True):
            username = st.text_input(t("admin_new_username"))
            password = st.text_input(t("admin_new_password"), type="password")
            role = st.selectbox(t("admin_new_role"), USER_ROLES, format_func=role_label)
            submitted = st.form_submit_button(t("admin_create_submit"), use_container_width=True)
            if submitted:
                ok, message = create_user_account(username, password, role)
                if ok:
                    st.session_state._admin_user_created_notice = message
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

            _render_admin_user_license_controls(username, user)

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

    admin = is_admin()
    tab_specs = [(slug, t(key)) for slug, key in account_tab_specs(admin=admin)]
    tab_labels = [label for _, label in tab_specs]
    default_tab = resolve_account_tab_default_label(admin=admin)

    tabs = st.tabs(tab_labels, default=default_tab)
    with tabs[0]:
        render_profile_section()
    with tabs[1]:
        render_user_activity_section()
    if admin:
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

    inject_account_tab_url_sync({label: slug for slug, label in tab_specs})
