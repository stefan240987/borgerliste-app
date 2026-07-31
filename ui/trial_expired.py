from __future__ import annotations

import streamlit as st

from auth import current_username, get_user_record
from i18n import t
from licensing import format_trial_end_date, is_trial_expired
from ui.common import navigate_to_account


def render_trial_expired_page() -> None:
    record = get_user_record(current_username()) or {}
    end_date = format_trial_end_date(record)

    st.title(t("trial_expired_title"))
    st.markdown(t("trial_expired_body", date=end_date))
    st.info(t("trial_expired_contact"))

    if st.button(t("trial_expired_go_account"), type="primary", use_container_width=False):
        navigate_to_account(tab="profile")
