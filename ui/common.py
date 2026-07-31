from __future__ import annotations
import html
import json
from datetime import datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from config import LOGO_PATH, PAGE_SIZE_OPTIONS, THEME_ICONS, THEME_OPTIONS
from auth import (
    current_session_expires_at, current_user, get_user_record, inject_session_idle_reload_watch,
    is_admin, logout_user, role_label,
)
from i18n import lang, t, theme_help
from licensing import sidebar_license_badge_text
from storage import (
    clear_active_list, save_user_preferences, sidebar_excel_bytes,
    apply_saved_user_preferences,
)
from ui.styles import inject_sidebar_controls

VALID_PAGES = frozenset({"borgerliste", "account", "privacy"})
ACCOUNT_TAB_SPECS_BASE: tuple[tuple[str, str], ...] = (
    ("profile", "account_profile_tab"),
    ("activity", "account_activity_tab"),
)
ACCOUNT_TAB_SPECS_ADMIN: tuple[tuple[str, str], ...] = (
    ("users", "account_admin_users_tab"),
    ("settings", "account_admin_settings_tab"),
    ("master", "account_admin_master_tab"),
    ("audit", "account_admin_audit_tab"),
    ("gdpr", "account_admin_gdpr_tab"),
)
ADMIN_ONLY_ACCOUNT_TAB_SLUGS = frozenset(slug for slug, _ in ACCOUNT_TAB_SPECS_ADMIN)
ALL_ACCOUNT_TAB_SLUGS = frozenset(
    slug for slug, _ in (*ACCOUNT_TAB_SPECS_BASE, *ACCOUNT_TAB_SPECS_ADMIN)
)


def account_tab_specs(*, admin: bool) -> list[tuple[str, str]]:
    specs = list(ACCOUNT_TAB_SPECS_BASE)
    if admin:
        specs.extend(ACCOUNT_TAB_SPECS_ADMIN)
    return specs


def resolve_account_tab_slug(raw: str | None, *, admin: bool) -> str:
    slug = (raw or "profile").strip().lower()
    if slug not in ALL_ACCOUNT_TAB_SLUGS:
        return "profile"
    if slug in ADMIN_ONLY_ACCOUNT_TAB_SLUGS and not admin:
        return "profile"
    return slug


def resolve_account_tab_default_label(*, admin: bool) -> str | None:
    slug = resolve_account_tab_slug(st.session_state.get("account_tab"), admin=admin)
    for tab_slug, label_key in account_tab_specs(admin=admin):
        if tab_slug == slug:
            return t(label_key)
    return None


def _trial_blocked() -> bool:
    from licensing import is_trial_expired

    user_record = get_user_record(current_user()["username"]) if current_user() else None
    return bool(user_record and is_trial_expired(user_record))


def _resolve_page_from_query(*, trial_blocked: bool) -> str:
    page = str(st.query_params.get("page", "borgerliste")).strip().lower()
    if page not in VALID_PAGES:
        page = "borgerliste"
    if trial_blocked and page not in ("account", "privacy"):
        page = "borgerliste"
    return page


def _apply_page_query_param(page: str) -> None:
    if st.query_params.get("page") != page:
        st.query_params["page"] = page


def _apply_tab_query_param(tab: str | None) -> None:
    if tab:
        if st.query_params.get("tab") != tab:
            st.query_params["tab"] = tab
    elif "tab" in st.query_params:
        del st.query_params["tab"]


def restore_navigation_from_query_params() -> None:
    """Gendan active_page og account_tab fra URL efter auth (fx ved F5)."""
    if not st.session_state.get("authenticated"):
        return
    trial_blocked = _trial_blocked()
    page = _resolve_page_from_query(trial_blocked=trial_blocked)
    st.session_state.active_page = page
    if page == "account":
        admin = is_admin()
        tab = resolve_account_tab_slug(st.query_params.get("tab"), admin=admin)
        st.session_state.account_tab = tab


def sync_navigation_to_query_params() -> None:
    """Skriv navigation til URL når session_state afviger (sidebar, logout-path)."""
    if not st.session_state.get("authenticated"):
        return
    trial_blocked = _trial_blocked()
    page = st.session_state.get("active_page", "borgerliste")
    if page not in VALID_PAGES:
        page = "borgerliste"
    if trial_blocked and page not in ("account", "privacy"):
        page = "borgerliste"
    _apply_page_query_param(page)
    if page == "account":
        tab = resolve_account_tab_slug(st.session_state.get("account_tab"), admin=is_admin())
        st.session_state.account_tab = tab
        _apply_tab_query_param(tab)
    else:
        _apply_tab_query_param(None)


def navigate_to_page(page: str) -> None:
    if page not in VALID_PAGES:
        page = "borgerliste"
    st.session_state.active_page = page
    if page == "account":
        tab = resolve_account_tab_slug(st.session_state.get("account_tab"), admin=is_admin())
        st.session_state.account_tab = tab
        _apply_page_query_param(page)
        _apply_tab_query_param(tab)
    else:
        _apply_page_query_param(page)
        _apply_tab_query_param(None)
    st.rerun()


def navigate_to_account(*, tab: str = "profile") -> None:
    admin = is_admin()
    tab = resolve_account_tab_slug(tab, admin=admin)
    st.session_state.active_page = "account"
    st.session_state.account_tab = tab
    _apply_page_query_param("account")
    _apply_tab_query_param(tab)
    st.rerun()


def inject_account_tab_url_sync(label_to_slug: dict[str, str]) -> None:
    """Opdater ?tab= i URL ved faneklik uden synlig UI-ændring."""
    if not label_to_slug or st.session_state.get("_account_tab_sync_injected"):
        return
    st.session_state._account_tab_sync_injected = True
    mapping = json.dumps(label_to_slug, ensure_ascii=False)
    components.html(
        f"""<script>
(function () {{
  const slugByLabel = {mapping};
  const doc = window.parent.document;
  function bindTabs() {{
    const tabLists = doc.querySelectorAll('[data-testid="stTabs"] [role="tablist"]');
    tabLists.forEach((tabList) => {{
      if (tabList.dataset.borgerlisteTabSync === "1") return;
      tabList.dataset.borgerlisteTabSync = "1";
      tabList.addEventListener("click", (event) => {{
        const btn = event.target.closest('[role="tab"]');
        if (!btn) return;
        const label = (btn.textContent || "").trim();
        const slug = slugByLabel[label];
        if (!slug) return;
        const url = new URL(window.parent.location.href);
        if (url.searchParams.get("page") !== "account") return;
        if (url.searchParams.get("tab") === slug) return;
        url.searchParams.set("tab", slug);
        window.parent.history.replaceState({{}}, "", url.toString());
      }});
    }});
  }}
  bindTabs();
  const observer = new MutationObserver(bindTabs);
  observer.observe(doc.body, {{ childList: true, subtree: true }});
}})();
</script>""",
        height=0,
        width=0,
    )


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
        sync_navigation_to_query_params()
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
        navigate_to_page("borgerliste")
    if st.sidebar.button(
        t("nav_account"),
        use_container_width=True,
        type="primary" if current_page == "account" else "secondary",
        key="nav_account",
    ):
        navigate_to_page("account")
    if st.sidebar.button(
        t("nav_privacy"),
        use_container_width=True,
        type="primary" if current_page == "privacy" else "secondary",
        key="nav_privacy",
    ):
        navigate_to_page("privacy")
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
        "account_tab": "profile",
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
        badge_text = sidebar_license_badge_text(get_user_record(user["username"]) or user)
        badge_html = ""
        if badge_text:
            badge_html = f'<span class="sidebar-license-badge">{html.escape(badge_text)}</span>'
        st.sidebar.markdown(
            f'<div class="sidebar-user-pill">'
            f'<span class="sidebar-user-name">{html.escape(user["username"])}</span>'
            f'<span class="sidebar-user-role">{html.escape(role_label(str(user.get("role", "user"))))}</span>'
            f"{badge_html}"
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
