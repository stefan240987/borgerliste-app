from __future__ import annotations
import streamlit as st
from config import (
    FILTER_BUTTON_I18N, FILTER_I18N, STATUS_I18N, THEME_OPTIONS, TRANSLATIONS,
)


def lang() -> str:
    return st.session_state.get("language", "da")


def t(key: str, **kwargs: object) -> str:
    text = TRANSLATIONS.get(lang(), TRANSLATIONS["da"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def status_label(status: str, short: bool = False) -> str:
    keys = STATUS_I18N.get(status)
    if not keys:
        return status
    return t(keys[1] if short else keys[0])


def filter_label(filter_key: str) -> str:
    return t(FILTER_I18N.get(filter_key, "filter_all"))


def filter_button_label(filter_key: str) -> str:
    return t(FILTER_BUTTON_I18N.get(filter_key, "filter_all"))


def page_size_label(value: int | str) -> str:
    if value == "Alle":
        return t("page_size_all")
    if value == 1:
        return t("page_size_one")
    return t("page_size_n", n=value)


def theme_help(theme: str) -> str:
    mapping = {
        "Lyst tema": "theme_light",
        "Mørkt tema": "theme_dark",
        "Browser standard": "theme_browser",
    }
    return t(mapping.get(theme, "theme_light"))

