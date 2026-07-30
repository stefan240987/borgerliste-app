"""Borgerliste – Streamlit entry point."""
from __future__ import annotations
import streamlit as st
from auth import (
    ensure_auth_cookie_synced, ensure_authenticated_session, prepare_cookie_reading,
    render_login, try_restore_auth_from_cookie,
)
from i18n import t
from storage import ensure_user_data_loaded, save_active_session_metadata
from ui.admin import render_account_page, render_privacy_page
from ui.citizen_list import (
    filter_dataframe, render_citizen_list, render_pagination_bar, render_status_metrics,
    render_upload_section, resolve_page_size, sync_session_df_with_master,
)
from ui.common import (
    finish_page, init_session_state, render_page_navigation, render_sidebar_content,
    render_sidebar_settings,
)
from ui.styles import inject_styles


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

