from __future__ import annotations
import html
from datetime import datetime
from pathlib import Path
import streamlit as st
from config import LOGO_PATH, PAGE_SIZE_OPTIONS, THEME_ICONS, THEME_OPTIONS
from auth import (
    current_session_expires_at, current_user, inject_session_idle_reload_watch,
    logout_user, role_label,
)
from i18n import lang, t, theme_help
from storage import (
    clear_active_list, save_user_preferences, sidebar_excel_bytes,
    apply_saved_user_preferences,
)
from ui.styles import inject_sidebar_controls


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

