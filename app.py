"""Borgerflow – Streamlit entry point."""
from __future__ import annotations
import streamlit as st
from auth import (
    ensure_auth_cookie_synced, ensure_authenticated_session, current_username, get_user_record,
    render_login, restore_auth_from_cookie_if_needed,
)
from i18n import t
from licensing import is_trial_expired
from storage import DataLockTimeoutError, ensure_user_data_loaded, save_active_session_metadata
from ui.admin import render_about_page, render_account_page, render_feedback_page, render_privacy_page
from ui.trial_expired import render_trial_expired_page
from config import INDSATS_FILTER_ALL
from ui.citizen_list import (
    filter_dataframe, indsats_filter_options, render_citizen_list, render_pagination_bar,
    render_status_metrics, render_upload_section, resolve_page_size,
    sync_session_df_with_master,
)
from ui.common import (
    INFO_PAGES, finish_page, init_session_state, render_page_navigation, render_sidebar_content,
    render_sidebar_settings, restore_navigation_from_query_params,
)
from ui.styles import inject_styles


def main() -> None:
    init_session_state()
    st.set_page_config(
        page_title=t("app_title"),
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="auto",
    )
    inject_styles(st.session_state.get("theme_choice", "Browser standard"))

    try:
        _run_app()
    except DataLockTimeoutError as exc:
        st.error(str(exc))
        st.info("Tip: Kør `pkill -f \"streamlit run.*borgerliste\"` og start kun én instans.")


def _run_app() -> None:
    restore_auth_from_cookie_if_needed()

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
    restore_navigation_from_query_params()

    user_record = get_user_record(current_username()) if st.session_state.get("current_user") else None
    trial_blocked = bool(user_record and is_trial_expired(user_record))

    if trial_blocked:
        render_page_navigation()
        render_sidebar_content()
        render_sidebar_settings()
        active_page = st.session_state.get("active_page", "borgerliste")
        if active_page == "account":
            render_account_page()
        elif active_page == "privacy":
            render_privacy_page()
        elif active_page == "about":
            render_about_page()
        elif active_page == "feedback":
            render_feedback_page()
        else:
            render_trial_expired_page()
        finish_page(show_pin=True)
        return

    ensure_user_data_loaded()
    if purged := st.session_state.pop("retention_purged_count", None):
        st.toast(t("admin_retention_purged", count=purged), icon="ℹ️")
    sync_session_df_with_master()

    render_page_navigation()

    df = st.session_state.citizens_df
    if st.session_state.get("active_page") not in INFO_PAGES and (df is None or df.empty):
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

    if st.session_state.get("active_page") == "about":
        render_about_page()
        finish_page(show_pin=True)
        return

    if st.session_state.get("active_page") == "feedback":
        render_feedback_page()
        finish_page(show_pin=True)
        return

    st.title(t("app_title"))
    render_upload_section()

    indsats_options = indsats_filter_options(df)
    if indsats_options is None:
        st.session_state.indsats_filter = INDSATS_FILTER_ALL
    elif st.session_state.get("indsats_filter", INDSATS_FILTER_ALL) not in (
        INDSATS_FILTER_ALL,
        *indsats_options,
    ):
        st.session_state.indsats_filter = INDSATS_FILTER_ALL
    indsats_filter = st.session_state.get("indsats_filter", INDSATS_FILTER_ALL)

    # KPI-overblik følger indsats-filteret, men ikke status/søgning (uændret uden indsats).
    render_status_metrics(filter_dataframe(df, "all", "", indsats_filter))

    st.markdown("---")
    search = st.text_input(
        t("search_placeholder"),
        key="search_query",
        placeholder=t("search_placeholder"),
        label_visibility="collapsed",
    )
    selected_filter = st.session_state.get("selected_filter", "all")
    filtered_df = filter_dataframe(df, selected_filter, search, indsats_filter)
    st.caption(t("citizens_summary", total=len(df), shown=len(filtered_df)))

    filter_signature = f"{selected_filter}|{search.strip().lower()}|{indsats_filter}"
    if st.session_state.filter_signature != filter_signature:
        st.session_state.filter_signature = filter_signature
        st.session_state.page_number = 0

    st.markdown(f"#### {t('citizens_heading')}")
    page_size = resolve_page_size(st.session_state.page_size, len(filtered_df))
    start, end, _page_number = render_pagination_bar(
        len(filtered_df),
        page_size,
        st.session_state.page_number,
        indsats_options=indsats_options,
    )

    render_citizen_list(filtered_df.iloc[start:end])
    save_active_session_metadata()
    finish_page(show_pin=True)


if __name__ == "__main__":
    main()
