from __future__ import annotations
import html
from datetime import datetime
import streamlit as st
from config import (
    FEEDBACK_KINDS, MAX_FEEDBACK_MESSAGE_LENGTH, MAX_FEEDBACK_TITLE_LENGTH,
    MAX_RETENTION_MONTHS, MAX_TRIAL_DAYS, MIN_PASSWORD_LENGTH, MIN_RETENTION_MONTHS,
    MIN_SESSION_IDLE_MINUTES, MAX_SESSION_IDLE_MINUTES, MIN_TRIAL_DAYS, USER_ROLES,
)
from auth import (
    admin_reset_user_password, create_user_account, current_user, current_username,
    deactivate_user_account, get_user_record, is_admin, load_users, reactivate_user_account,
    role_label, update_user_password, update_user_role, verify_admin_master_delete,
)
from i18n import t
from licensing import (
    effective_is_paid, extend_user_trial, format_trial_end_date, is_trial_expired,
    license_status_key, parse_trial_ends_at, trial_days_remaining, update_user_license,
)
from matching import (
    clear_master_register, load_master_register, maybe_sync_master_from_all_user_data,
)
from storage import (
    append_feedback, build_citizen_label_map, configured_retention_months,
    configured_session_idle_minutes, configured_trial_days, load_audit_log, load_feedback,
    public_signup_enabled, save_app_settings, trial_system_enabled,
)
from ui.common import account_tab_specs, inject_account_tab_url_sync, resolve_account_tab_default_label
from ui.styles import (
    admin_license_badge_html, admin_municipality_badges_html, admin_role_badge_html,
    status_pill_html,
)

_ADMIN_USER_COL_WEIGHTS = [2.0, 1.0, 1.0, 1.3, 1.0, 1.0]
_AUDIT_COL_WEIGHTS_ADMIN = [1.5, 1.0, 2.0, 1.0, 1.0]
_AUDIT_COL_WEIGHTS_USER = [1.5, 2.0, 1.0, 1.0]
_FEEDBACK_COL_WEIGHTS = [1.3, 1.0, 1.0, 1.5, 2.5]


def _feedback_kind_label(kind: str) -> str:
    key = f"feedback_kind_{kind}"
    label = t(key)
    return label if label != key else kind


def _account_panel_divider() -> None:
    st.markdown('<div class="account-panel-divider"></div>', unsafe_allow_html=True)


def _account_inline_form_marker() -> None:
    st.markdown('<div class="account-inline-form-marker"></div>', unsafe_allow_html=True)


def _render_audit_table(
    entries: list[dict],
    labels: dict[str, str],
    *,
    show_user: bool,
) -> None:
    weights = _AUDIT_COL_WEIGHTS_ADMIN if show_user else _AUDIT_COL_WEIGHTS_USER
    header_keys = (
        ("admin_audit_col_time", "admin_audit_col_user", "admin_audit_col_citizen", "admin_audit_col_from", "admin_audit_col_to")
        if show_user
        else ("admin_audit_col_time", "admin_audit_col_citizen", "admin_audit_col_from", "admin_audit_col_to")
    )

    header_cols = st.columns(weights)
    for col, key in zip(header_cols, header_keys):
        col.markdown(
            f'<div class="account-table-header">{html.escape(t(key))}</div>',
            unsafe_allow_html=True,
        )

    for entry in entries:
        citizen_id = str(entry.get("citizen_id", ""))
        citizen_label = labels.get(citizen_id, citizen_id)
        old_status = str(entry.get("old_status", ""))
        new_status = str(entry.get("new_status", ""))
        cols = st.columns(weights)

        col_idx = 0
        cols[col_idx].markdown(
            f'<div class="account-table-row">{html.escape(str(entry.get("timestamp", "")))}</div>',
            unsafe_allow_html=True,
        )
        col_idx += 1

        if show_user:
            cols[col_idx].markdown(
                f'<div class="account-table-row">{html.escape(str(entry.get("username", "")))}</div>',
                unsafe_allow_html=True,
            )
            col_idx += 1

        cols[col_idx].markdown(
            f'<div class="account-table-row">{html.escape(citizen_label)}</div>',
            unsafe_allow_html=True,
        )
        col_idx += 1

        cols[col_idx].markdown(status_pill_html(old_status), unsafe_allow_html=True)
        col_idx += 1
        cols[col_idx].markdown(status_pill_html(new_status), unsafe_allow_html=True)


def render_profile_section() -> None:
    user = current_user()
    if not user:
        return

    record = get_user_record(user["username"]) or {}
    st.markdown('<div class="account-panel">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(t("account_username_label"), value=user["username"], disabled=True)
    with col2:
        st.text_input(t("account_role_label"), value=role_label(str(user.get("role", "user"))), disabled=True)
    if record.get("created_at"):
        st.caption(f"{t('account_created_label')}: {record['created_at']}")

    if str(user.get("role", "user")) != "admin" and trial_system_enabled():
        _account_panel_divider()
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

    _account_panel_divider()
    st.markdown(f"#### {t('account_change_password_title')}")
    st.caption(t("account_password_hint", min=MIN_PASSWORD_LENGTH))
    with st.form("change_password_form", clear_on_submit=True):
        pw_col1, pw_col2 = st.columns(2)
        with pw_col1:
            current_password = st.text_input(t("account_current_password"), type="password")
            new_password = st.text_input(t("account_new_password"), type="password")
        with pw_col2:
            confirm_password = st.text_input(t("account_confirm_password"), type="password")
        submitted = st.form_submit_button(t("account_password_submit"), type="primary")
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
    st.markdown('<div class="account-panel">', unsafe_allow_html=True)

    st.markdown(f"#### {t('admin_session_title')}")
    current_minutes = configured_session_idle_minutes()
    st.caption(t("admin_session_current", minutes=current_minutes))
    st.caption(t("admin_session_idle_help"))

    with st.form("admin_session_settings_form"):
        input_col, btn_col = st.columns([3, 1])
        with input_col:
            idle_minutes = st.number_input(
                t("admin_session_idle_label"),
                min_value=MIN_SESSION_IDLE_MINUTES,
                max_value=MAX_SESSION_IDLE_MINUTES,
                value=current_minutes,
                step=1,
            )
        with btn_col:
            _account_inline_form_marker()
            submitted = st.form_submit_button(t("admin_session_save"))
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

    _account_panel_divider()
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
        days_col, btn_col = st.columns([3, 1])
        with days_col:
            default_days = st.number_input(
                t("admin_trial_days_label"),
                min_value=MIN_TRIAL_DAYS,
                max_value=MAX_TRIAL_DAYS,
                value=trial_days,
                step=1,
                help=t("admin_trial_days_help"),
            )
        with btn_col:
            _account_inline_form_marker()
            submitted = st.form_submit_button(t("admin_session_save"))
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

    _account_panel_divider()
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
        _, btn_col = st.columns([3, 1])
        with btn_col:
            _account_inline_form_marker()
            submitted = st.form_submit_button(t("admin_session_save"))
        if submitted:
            save_app_settings(public_signup_enabled=enabled)
            st.success(t("admin_public_signup_saved"))
            st.rerun()


def _format_user_created_date(user: dict) -> str:
    raw = user.get("created_at")
    if not raw:
        return t("admin_municipalities_none")
    try:
        return datetime.fromisoformat(str(raw)).strftime("%d-%m-%Y")
    except ValueError:
        return str(raw)[:10]


def _render_admin_users_toolbar() -> None:
    title_col, action_col = st.columns([3, 1])
    with title_col:
        st.markdown(f"#### {t('admin_users_title')}")
    with action_col:
        if st.button(
            t("admin_create_user_btn"),
            key="admin_create_user_btn",
            type="primary",
            use_container_width=True,
        ):
            _admin_create_user_dialog()


@st.dialog(t("admin_create_user"))
def _admin_create_user_dialog() -> None:
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


def _render_admin_users_table(users: list[dict]) -> None:
    header = st.columns(_ADMIN_USER_COL_WEIGHTS)
    for col, label_key in zip(
        header,
        (
            "admin_users_col_username",
            "admin_users_col_role",
            "admin_users_col_municipalities",
            "admin_users_col_license",
            "admin_users_col_created",
            "admin_users_col_actions",
        ),
    ):
        col.markdown(f'<div class="account-table-header">{html.escape(t(label_key))}</div>', unsafe_allow_html=True)

    for user in users:
        username = str(user.get("username", ""))
        active = bool(user.get("active", True))
        role = str(user.get("role", "user"))
        cols = st.columns(_ADMIN_USER_COL_WEIGHTS)

        username_html = html.escape(username)
        if not active:
            username_html = f'<span class="admin-user-inactive">{username_html}</span>'
        cols[0].markdown(f'<div class="account-table-row">{username_html}</div>', unsafe_allow_html=True)
        cols[1].markdown(admin_role_badge_html(role), unsafe_allow_html=True)
        cols[2].markdown(admin_municipality_badges_html(None), unsafe_allow_html=True)
        cols[3].markdown(admin_license_badge_html(user), unsafe_allow_html=True)
        cols[4].markdown(
            f'<div class="account-table-row">{html.escape(_format_user_created_date(user))}</div>',
            unsafe_allow_html=True,
        )
        with cols[5]:
            st.markdown('<div class="account-table-btn-marker"></div>', unsafe_allow_html=True)
            if st.button(t("admin_edit_user"), key=f"edit_{username}"):
                _admin_edit_user_dialog(username)


def _render_edit_section_role(username: str, user: dict) -> None:
    st.markdown(f"**{t('admin_edit_section_role')}**")
    current_role = str(user.get("role", "user"))
    active = bool(user.get("active", True))

    if not active and user.get("deactivated_at"):
        st.caption(t("admin_user_deactivated_at", date=user["deactivated_at"]))

    st.info(t("admin_municipalities_coming_soon"))

    if not active or username == current_username():
        if username == current_username() and active:
            st.caption(t("admin_cannot_change_own_role"))
        return

    role_cols = st.columns([2, 1])
    with role_cols[0]:
        new_role = st.selectbox(
            t("admin_change_role"),
            USER_ROLES,
            index=USER_ROLES.index(current_role) if current_role in USER_ROLES else 0,
            format_func=role_label,
            key=f"dialog_role_{username}",
            label_visibility="collapsed",
        )
    with role_cols[1]:
        if st.button(t("admin_change_role_submit"), key=f"dialog_role_save_{username}", use_container_width=True):
            ok, message = update_user_role(username, new_role)
            if ok:
                st.toast(message, icon="✅")
                st.rerun()
            st.error(message)


def _render_edit_section_license(username: str, user: dict) -> None:
    st.markdown(f"**{t('admin_edit_section_license')}**")
    if str(user.get("role", "user")) == "admin":
        st.caption(t("license_status_admin"))
        return

    status = t(license_status_key(user))
    expires = format_trial_end_date(user) if not effective_is_paid(user) else "—"
    st.caption(f"{t('account_license_status')}: **{status}** · {t('account_license_expires')}: {expires}")

    is_paid = st.checkbox(
        t("admin_user_is_paid"),
        value=effective_is_paid(user),
        key=f"dialog_license_paid_{username}",
    )
    current_end = parse_trial_ends_at(user)
    default_date = current_end.date() if current_end else datetime.now().date()
    new_date = st.date_input(
        t("admin_user_trial_ends"),
        value=default_date,
        key=f"dialog_license_date_{username}",
        disabled=is_paid,
    )

    extend_cols = st.columns(3)
    for col, extra_days in zip(extend_cols, (7, 14, 30)):
        with col:
            if st.button(
                t("admin_user_extend_days", days=extra_days),
                key=f"dialog_extend_{extra_days}_{username}",
                use_container_width=True,
                disabled=is_paid,
            ):
                ok, message = extend_user_trial(username, extra_days)
                if ok:
                    st.toast(message, icon="✅")
                    st.rerun()
                st.error(message)

    if st.button(t("admin_session_save"), key=f"dialog_license_save_{username}", use_container_width=True):
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


def _render_edit_section_password(username: str) -> None:
    st.markdown(f"**{t('admin_edit_section_password')}**")
    with st.form(f"dialog_reset_password_{username}", clear_on_submit=True):
        new_password = st.text_input(
            t("admin_reset_password_for", username=username),
            type="password",
            key=f"dialog_reset_pw_{username}",
        )
        if st.form_submit_button(t("admin_reset_password"), use_container_width=True):
            ok, message = admin_reset_user_password(username, new_password)
            if ok:
                st.success(message)
            else:
                st.error(message)


def _render_edit_section_danger(username: str, user: dict) -> None:
    active = bool(user.get("active", True))
    st.markdown(
        f'<div class="admin-danger-zone"><div class="admin-danger-zone-title">{html.escape(t("admin_edit_section_danger"))}</div></div>',
        unsafe_allow_html=True,
    )

    if not active:
        if st.button(
            t("admin_reactivate"),
            key=f"dialog_reactivate_{username}",
            use_container_width=True,
            type="primary",
        ):
            ok, message = reactivate_user_account(username)
            if ok:
                st.toast(message, icon="✅")
                st.rerun()
            st.error(message)
        return

    if username == current_username():
        st.caption(t("admin_cannot_deactivate_self"))
        return

    delete_data = st.checkbox(
        t("admin_deactivate_delete_data"),
        key=f"dialog_delete_data_{username}",
    )
    if st.button(
        t("admin_deactivate"),
        key=f"dialog_deactivate_{username}",
        use_container_width=True,
        type="secondary",
    ):
        ok, message = deactivate_user_account(username, delete_data=delete_data)
        if ok:
            st.toast(message, icon="✅")
            st.rerun()
        st.error(message)


@st.dialog(t("admin_edit_user_title"))
def _admin_edit_user_dialog(username: str) -> None:
    user = get_user_record(username)
    if not user:
        st.error(t("admin_user_license_not_found"))
        return

    st.markdown(f"**{html.escape(username)}**")
    st.divider()

    _render_edit_section_role(username, user)
    st.divider()
    _render_edit_section_license(username, user)
    st.divider()
    _render_edit_section_password(username)
    st.divider()
    _render_edit_section_danger(username, user)


def render_admin_users_section() -> None:
    _render_admin_users_toolbar()

    if notice := st.session_state.pop("_admin_user_created_notice", None):
        st.success(notice)

    users = load_users()
    if not users:
        st.info(t("admin_no_users"))
        return

    _render_admin_users_table(users)


def render_admin_master_section() -> None:
    maybe_sync_master_from_all_user_data(force=True)
    register = load_master_register()
    count = len(register)

    st.markdown('<div class="account-panel">', unsafe_allow_html=True)
    st.caption(t("master_admin_description"))
    st.markdown(
        (
            f'<div class="account-metric-inline">'
            f'<span class="account-metric-value">{count}</span>'
            f'<span class="account-metric-label">{html.escape(t("master_register_count", count=count))}</span>'
            f"</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="account-danger-panel">', unsafe_allow_html=True)
    st.markdown(f"#### {t('clear_master_register')}")
    st.caption(t("master_delete_warning"))

    with st.form("master_delete_form", clear_on_submit=True):
        pwd_col, btn_col = st.columns([3, 1])
        with pwd_col:
            password = st.text_input(t("master_delete_password"), type="password")
        with btn_col:
            _account_inline_form_marker()
            submitted = st.form_submit_button(t("master_delete_confirm"), type="secondary")
        if submitted:
            if verify_admin_master_delete(password):
                clear_master_register()
                st.session_state.user_data_loaded_for = None
                st.toast(t("master_register_cleared"), icon="✅")
                st.rerun()
            st.error(t("master_delete_password_error"))


def render_gdpr_privacy_section() -> None:
    st.markdown(t("gdpr_text"))
    st.markdown(t("gdpr_section_roles"))
    st.markdown(t("gdpr_section_data"))
    st.markdown(t("gdpr_section_security"))
    st.markdown(t("gdpr_section_rights"))
    st.markdown(t("gdpr_section_checklist"))


def render_user_activity_section() -> None:
    st.markdown(f"#### {t('user_audit_title')}")
    st.caption(t("user_audit_caption"))
    username = current_username()
    entries = [entry for entry in load_audit_log() if entry.get("username") == username]
    if not entries:
        st.info(t("admin_audit_empty"))
        return

    labels = build_citizen_label_map()
    _render_audit_table(list(reversed(entries[-500:])), labels, show_user=False)


def render_admin_gdpr_section() -> None:
    st.markdown('<div class="account-panel">', unsafe_allow_html=True)

    st.markdown(f"#### {t('admin_retention_title')}")
    current_months = configured_retention_months()
    st.caption(t("admin_retention_help"))
    if current_months <= 0:
        st.caption(t("admin_retention_disabled"))
    else:
        st.caption(t("admin_retention_current", months=current_months))

    with st.form("admin_retention_form"):
        months_col, btn_col = st.columns([3, 1])
        with months_col:
            months = st.number_input(
                t("admin_retention_label"),
                min_value=MIN_RETENTION_MONTHS,
                max_value=MAX_RETENTION_MONTHS,
                value=current_months,
                step=1,
                help=t("admin_retention_help"),
            )
        with btn_col:
            _account_inline_form_marker()
            submitted = st.form_submit_button(t("admin_session_save"))
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

    _account_panel_divider()
    st.markdown(f"#### {t('admin_gdpr_processing_title')}")
    st.markdown(f'<div class="account-gdpr-table-note"></div>', unsafe_allow_html=True)
    if current_months <= 0:
        retention_text = t("admin_gdpr_retention_disabled")
    else:
        retention_text = t("admin_gdpr_retention_active", months=current_months)
    st.markdown(t("admin_gdpr_processing_body", retention=retention_text))


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

    _render_audit_table(list(reversed(filtered[-500:])), labels, show_user=True)


def render_privacy_page() -> None:
    st.title(t("gdpr_title"))
    render_gdpr_privacy_section()


def render_about_page() -> None:
    st.title(t("about_title"))
    st.markdown(t("about_lead"))
    st.markdown(f"- {t('about_bullet_1')}")
    st.markdown(f"- {t('about_bullet_2')}")
    st.markdown(f"- {t('about_bullet_3')}")


def render_feedback_page() -> None:
    st.title(t("feedback_title"))
    st.markdown(t("feedback_lead"))

    kind_labels = {kind: _feedback_kind_label(kind) for kind in FEEDBACK_KINDS}
    with st.form("feedback_form", clear_on_submit=True):
        kind_label = st.radio(
            t("feedback_kind_label"),
            list(kind_labels.values()),
            horizontal=True,
        )
        title = st.text_input(
            t("feedback_title_label"),
            max_chars=MAX_FEEDBACK_TITLE_LENGTH,
        )
        message = st.text_area(
            t("feedback_message_label"),
            max_chars=MAX_FEEDBACK_MESSAGE_LENGTH,
            height=160,
        )
        submitted = st.form_submit_button(t("feedback_submit"), type="primary")
        if submitted:
            kind = next((k for k, label in kind_labels.items() if label == kind_label), "")
            ok, result_message = append_feedback(kind=kind, title=title, message=message)
            if ok:
                st.success(result_message)
            else:
                st.error(result_message)


def _render_feedback_table(entries: list[dict]) -> None:
    header_keys = (
        "admin_feedback_col_time",
        "admin_feedback_col_user",
        "admin_feedback_col_kind",
        "admin_feedback_col_title",
        "admin_feedback_col_message",
    )
    header_cols = st.columns(_FEEDBACK_COL_WEIGHTS)
    for col, key in zip(header_cols, header_keys):
        col.markdown(
            f'<div class="account-table-header">{html.escape(t(key))}</div>',
            unsafe_allow_html=True,
        )

    for entry in entries:
        cols = st.columns(_FEEDBACK_COL_WEIGHTS)
        values = (
            str(entry.get("timestamp", "")),
            str(entry.get("username", "")),
            _feedback_kind_label(str(entry.get("kind", ""))),
            str(entry.get("title", "")),
            str(entry.get("message", "")),
        )
        for col, value in zip(cols, values):
            col.markdown(
                f'<div class="account-table-row">{html.escape(value)}</div>',
                unsafe_allow_html=True,
            )


def render_admin_feedback_section() -> None:
    st.markdown(f"#### {t('admin_feedback_title')}")
    st.caption(t("admin_feedback_caption"))
    entries = load_feedback()
    if not entries:
        st.info(t("admin_feedback_empty"))
        return

    kind_labels = {kind: _feedback_kind_label(kind) for kind in FEEDBACK_KINDS}
    filter_cols = st.columns(2)
    usernames = sorted({str(entry.get("username", "")) for entry in entries if entry.get("username")})
    with filter_cols[0]:
        filter_kind = st.selectbox(
            t("admin_feedback_filter_kind"),
            [t("admin_feedback_all_kinds"), *[kind_labels[k] for k in FEEDBACK_KINDS]],
        )
    with filter_cols[1]:
        filter_user = st.selectbox(
            t("admin_feedback_filter_user"),
            [t("admin_feedback_all_users"), *usernames],
        )

    filtered = entries
    if filter_kind != t("admin_feedback_all_kinds"):
        kind_key = next((k for k, label in kind_labels.items() if label == filter_kind), "")
        filtered = [entry for entry in filtered if entry.get("kind") == kind_key]
    if filter_user != t("admin_feedback_all_users"):
        filtered = [entry for entry in filtered if entry.get("username") == filter_user]

    _render_feedback_table(list(reversed(filtered[-500:])))


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
            render_admin_feedback_section()
        with tabs[7]:
            render_admin_gdpr_section()

    inject_account_tab_url_sync({label: slug for slug, label in tab_specs})
