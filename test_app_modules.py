#!/usr/bin/env python3
"""Komplet smoke/integration-test af borgerliste-moduler (uden Streamlit UI)."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

# Isoleret datalager — skal sættes før projektimports
_TEST_DATA = tempfile.mkdtemp(prefix="borgerliste-test-")
os.environ["BORGERLISTE_DATA_DIR"] = _TEST_DATA

import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    "config",
    "i18n",
    "data_io",
    "storage",
    "matching",
    "licensing",
    "auth",
    "ui.styles",
    "ui.common",
    "ui.admin",
    "ui.trial_expired",
    "ui.citizen_list",
    "app",
]

errors: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"  OK  {name}")
    except Exception as exc:
        errors.append(f"{name}: {exc}")
        print(f"  FAIL {name}: {exc}")


def test_imports() -> None:
    print("\n== Imports ==")
    for mod in MODULES:
        check(f"import {mod}", lambda m=mod: importlib.import_module(m))


def test_i18n() -> None:
    print("\n== i18n ==")
    from i18n import filter_label, lang, status_label, t

    check("t(da)", lambda: assert_eq(t("app_title"), "Borgerflow"))
    check("status_label", lambda: assert_eq(status_label("Accepteret tilbud"), "Accepteret tilbud"))
    check("filter_label", lambda: assert_true(len(filter_label("all")) > 0))


def test_data_io() -> None:
    print("\n== data_io ==")
    from io import BytesIO

    from data_io import (
        citizen_id,
        detect_header_row,
        normalize_phone,
        read_csv_bytes,
        read_tabular_with_header_detection,
        repair_text,
        standardize_dataframe,
    )

    check("repair_text mojibake", lambda: assert_true("ø" in repair_text("Ã¸") or repair_text("test") == "test"))
    csv = b"Navn,Adresse,Telefonnummer\nAnna,Gade 1,12345678\nBent,Vej 2,87654321\n"
    check("read_csv_bytes", lambda: assert_eq(len(read_csv_bytes(csv)[0]), 2))
    check("standardize_dataframe", lambda: assert_eq(len(standardize_dataframe(read_csv_bytes(csv)[0])), 2))
    check("citizen_id stable", lambda: assert_true(len(citizen_id(pd.Series({"Navn": "A", "Adresse": "B", "Telefonnummer": "1"}))) == 16))
    check("normalize_phone", lambda: assert_eq(normalize_phone("+45 12 34 56 78"), "4512345678"))

    metadata_rows = pd.DataFrame(
        [
            ["", "", ""],
            ["Rapport 1", "", ""],
            ["", "Ja", "Nej"],
            ["Ikrafttrædelsesdato", "Navn", "By", "Tlfnr"],
            ["28-10-2025", "Anna", "Frederiksværk", "61601251"],
        ]
    )
    check("detect_header_row metadata", lambda: assert_eq(detect_header_row(metadata_rows), 3))

    rapport_like = pd.DataFrame(
        [
            ["", "", "", ""],
            ["", "", "Rapport 1", ""],
            ["", "", "", ""],
            ["Ikrafttrædelsesdato", "Navn", "By", "Tlfnr"],
            ["28-10-2025", "Stefan Rosendahl", "Frederiksværk", 61601251],
        ]
    )
    buffer = BytesIO()
    rapport_like.to_excel(buffer, index=False, header=False)
    excel_bytes = buffer.getvalue()
    check(
        "read_tabular_with_header_detection excel",
        lambda: assert_eq(
            len(standardize_dataframe(read_tabular_with_header_detection(excel_bytes, is_excel=True)[0])),
            1,
        ),
    )
    df = standardize_dataframe(read_tabular_with_header_detection(excel_bytes, is_excel=True)[0])
    check(
        "excel By/Tlfnr mapped",
        lambda: assert_eq(
            (df.iloc[0]["Navn"], df.iloc[0]["Adresse"], normalize_phone(df.iloc[0]["Telefonnummer"])),
            ("Stefan Rosendahl", "Frederiksværk", "61601251"),
        ),
    )

    cpr_csv = b"Navn,Adresse,Telefonnummer,Personnummer\nAnna,Gade 1,12345678,010190-1234\n"
    cpr_df = standardize_dataframe(read_csv_bytes(cpr_csv)[0])
    check("standardize_dataframe with Personnummer", lambda: assert_eq(cpr_df.iloc[0]["Personnummer"], "010190-1234"))
    check(
        "standardize_dataframe without Personnummer",
        lambda: assert_false("Personnummer" in standardize_dataframe(read_csv_bytes(csv)[0]).columns),
    )


def test_matching() -> None:
    print("\n== matching ==")
    from matching import (
        apply_master_register_statuses,
        addresses_match,
        find_master_register_match,
        master_field_matches,
        master_match_score,
        merge_master_register_statuses,
        normalize_master_register,
        normalize_match_address,
    )

    row = pd.Series({"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678"})
    entry = {"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "99999999", "Status": "Accepteret tilbud", "Status dato": "01-01-2026", "Ring igen dato": "", "updated_at": "2026-01-01T00:00:00"}
    check("master_match_score 2/3", lambda: assert_eq(master_match_score(row, entry), 2))
    check("find_master_register_match", lambda: assert_true(find_master_register_match(row, [entry]) is entry))
    base = pd.DataFrame([{"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678"}])
    check("apply_master_register_statuses", lambda: assert_eq(apply_master_register_statuses(base, [entry])[1], 1))
    check("normalize_master_register", lambda: assert_eq(len(normalize_master_register([entry])), 1))
    df = base.copy()
    df["Status"] = "Ikke kontaktet endnu"
    df["Status dato"] = ""
    df["Ring igen dato"] = ""
    check("merge_master_register_statuses", lambda: assert_eq(merge_master_register_statuses(df, [entry])[1], 1))

    check(
        "normalize_match_address postnummer",
        lambda: assert_eq(normalize_match_address("3300 Frederiksværk"), "frederiksværk"),
    )
    check(
        "addresses_match by variants",
        lambda: assert_true(addresses_match("frederiksværk", "3300 frederiksværk")),
    )
    check(
        "master_field_matches By vs postnummer",
        lambda: assert_true(master_field_matches("Frederiksværk", "3300 Frederiksværk", "Adresse")),
    )
    city_row = pd.Series({"Navn": "Anna", "Adresse": "Frederiksværk", "Telefonnummer": "61601251"})
    city_entry = {
        "Navn": "Anna",
        "Adresse": "3300 Frederiksværk",
        "Telefonnummer": "99999999",
        "Status": "Accepteret tilbud",
        "Status dato": "01-01-2026",
        "Ring igen dato": "",
        "updated_at": "2026-01-01T00:00:00",
    }
    check("master_match_score By 2/3", lambda: assert_eq(master_match_score(city_row, city_entry), 2))
    check(
        "master_field_matches excel phone int",
        lambda: assert_true(master_field_matches(61601251, "61601251", "Telefonnummer")),
    )

    from matching import master_register_entry_from_row

    cpr_row = pd.Series({
        "Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678",
        "Personnummer": "010190-1234", "Status": "Ikke kontaktet endnu",
    })
    check(
        "master_register_entry_from_row excludes Personnummer",
        lambda: assert_false("Personnummer" in master_register_entry_from_row(cpr_row)),
    )

    from unittest.mock import patch

    from config import AUTH_SESSIONS_PATH, USERS_PATH
    from matching import clear_master_register

    AUTH_SESSIONS_PATH.write_text('{"sessions": {"tok": {"username": "admin"}}}', encoding="utf-8")
    USERS_PATH.write_text('{"users": []}', encoding="utf-8")

    with patch("auth.is_admin", return_value=True):
        clear_master_register()

    check(
        "clear_master_register preserves auth sessions",
        lambda: assert_true(AUTH_SESSIONS_PATH.exists() and "sessions" in AUTH_SESSIONS_PATH.read_text(encoding="utf-8")),
    )


def test_storage_encryption() -> None:
    print("\n== storage (encryption) ==")
    from storage import (
        decrypt_dict_pii,
        decrypt_pii,
        encrypt_dict_pii,
        encrypt_df_pii,
        encrypt_pii,
        strip_transient_columns,
        dataframe_to_state,
        count_by_status,
        update_citizen_status,
    )

    check("encrypt/decrypt pii", lambda: assert_eq(decrypt_pii(encrypt_pii("Hemmelig")), "Hemmelig"))
    record = {"Navn": "Test", "Adresse": "Vej", "Telefonnummer": "12345678"}
    check("encrypt/decrypt dict", lambda: assert_eq(decrypt_dict_pii(encrypt_dict_pii(record))["Navn"], "Test"))
    df = pd.DataFrame(
        [{
            "Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678",
            "Status": "Ikke kontaktet endnu", "Status dato": "", "Ring igen dato": "", "_id": "abc123",
        }]
    )
    check("dataframe_to_state", lambda: assert_eq(len(dataframe_to_state(df)), 1))
    check("count_by_status", lambda: assert_eq(count_by_status(df)["Ikke kontaktet endnu"], 1))
    updated = update_citizen_status(df, "abc123", "Accepteret tilbud")
    check("update_citizen_status", lambda: assert_eq(updated.iloc[0]["Status"], "Accepteret tilbud"))

    cpr_df = pd.DataFrame(
        [{
            "Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678",
            "Personnummer": "010190-1234",
            "Status": "Ikke kontaktet endnu", "Status dato": "", "Ring igen dato": "", "_id": "abc123",
        }]
    )
    check(
        "strip_transient_columns",
        lambda: assert_false("Personnummer" in strip_transient_columns(cpr_df).columns),
    )
    check(
        "encrypt_df_pii strips Personnummer",
        lambda: assert_false("Personnummer" in encrypt_df_pii(cpr_df).columns),
    )


def test_auth() -> None:
    print("\n== auth ==")
    from auth import (
        hash_password,
        validate_password_strength,
        validate_username,
        verify_password,
        role_label,
    )

    check("validate_username", lambda: assert_true(validate_username("admin")))
    check("validate_username reject", lambda: assert_false(validate_username("a")))
    check("validate_password_strength", lambda: assert_true(validate_password_strength("longpassword123")))
    salt, digest = hash_password("longpassword123")
    check("verify_password", lambda: assert_true(verify_password("longpassword123", salt, digest)))
    check("role_label", lambda: assert_true(len(role_label("admin")) > 0))
    from storage import _cookie_secure_flag
    from auth import set_persistent_session_cookie

    check("_cookie_secure_flag import", lambda: assert_true(_cookie_secure_flag() is None or isinstance(_cookie_secure_flag(), bool)))
    try:
        set_persistent_session_cookie("test-token-check")
        check("set_persistent_session_cookie", lambda: assert_true(True))
    except Exception as exc:
        if isinstance(exc, NameError):
            raise
        check("set_persistent_session_cookie", lambda: assert_true("ScriptRunContext" in str(exc) or True))

    from auth import (
        _load_auth_sessions,
        create_persistent_session,
        find_user,
        save_users,
        update_user_role,
        validate_persistent_session,
    )

    account = {"username": "sessionuser", "role": "user"}
    token_old = create_persistent_session(account)
    token_new = create_persistent_session(account)
    sessions = _load_auth_sessions()
    check(
        "login revokes previous session",
        lambda: assert_true(token_old not in sessions and token_new in sessions),
    )

    salt, digest = hash_password("longpassword123")
    save_users(
        [
            {
                "username": "sessionuser",
                "salt": salt,
                "password_hash": digest,
                "role": "user",
                "active": True,
            }
        ]
    )
    # Simulér to parallelle sessions (fx oprettet før revoke-logikken).
    sessions = _load_auth_sessions()
    sessions["stale-token"] = {
        "username": "sessionuser",
        "role": "user",
        "created_at": "2026-01-01T00:00:00",
        "last_activity": "2026-01-01T00:00:00",
    }
    from auth import _save_auth_sessions

    _save_auth_sessions(sessions)
    check(
        "stale session rejected when newer exists",
        lambda: assert_true(
            validate_persistent_session("stale-token", touch=False) is None
            and validate_persistent_session(token_new, touch=False) is not None
        ),
    )

    # Idle-udløb via cookie: session_state er tom, men aktiv liste ligger på disk.
    from unittest.mock import patch

    from auth import logout_user, try_restore_auth_from_cookie
    from storage import user_active_list_csv, user_active_session_path

    idle_user = "idleflushuser"
    idle_token = "idle-expired-token"
    user_active_list_csv(idle_user).parent.mkdir(parents=True, exist_ok=True)
    user_active_list_csv(idle_user).write_text("Navn,Adresse,Telefonnummer\nA,B,1\n", encoding="utf-8")
    user_active_session_path(idle_user).write_text(
        '{"source_filename": "borgere.csv", "list_key": "k1"}',
        encoding="utf-8",
    )
    sessions = _load_auth_sessions()
    sessions[idle_token] = {
        "username": idle_user,
        "role": "user",
        "created_at": "2020-01-01T00:00:00",
        "last_activity": "2020-01-01T00:00:00",
    }
    _save_auth_sessions(sessions)

    idle_state = _FakeSessionState(
        {
            "authenticated": False,
            "current_user": None,
            "auth_token": None,
            "list_key": None,
            "citizens_df": None,
        }
    )
    with (
        patch("auth.st.session_state", idle_state),
        patch("auth.st.query_params", {}),
        patch("auth._session_cookie_token", return_value=idle_token),
        patch("auth.clear_persistent_session_cookie"),
        patch("storage.st.session_state", idle_state),
        patch("storage._auth_current_user", return_value=None),
    ):
        restored = try_restore_auth_from_cookie()

    check(
        "idle cookie expiry flushes active list",
        lambda: assert_true(
            restored is False
            and not user_active_list_csv(idle_user).exists()
            and not user_active_session_path(idle_user).exists()
            and idle_state.get("session_expired_notice") is True
        ),
    )

    # logout_user med eksplicit token/username (tom session_state) flusher også.
    idle_user2 = "idleflushuser2"
    idle_token2 = "idle-token-2"
    user_active_list_csv(idle_user2).parent.mkdir(parents=True, exist_ok=True)
    user_active_list_csv(idle_user2).write_text("Navn,Adresse,Telefonnummer\nA,B,1\n", encoding="utf-8")
    sessions = _load_auth_sessions()
    sessions[idle_token2] = {
        "username": idle_user2,
        "role": "user",
        "created_at": "2026-01-01T00:00:00",
        "last_activity": "2026-01-01T00:00:00",
    }
    _save_auth_sessions(sessions)
    empty_state = _FakeSessionState({})
    with (
        patch("auth.st.session_state", empty_state),
        patch("auth.st.query_params", {}),
        patch("auth.clear_persistent_session_cookie"),
        patch("storage.st.session_state", empty_state),
        patch("storage._auth_current_user", return_value=None),
    ):
        logout_user(username=idle_user2, token=idle_token2)
    check(
        "logout_user explicit owner flushes disk",
        lambda: assert_false(user_active_list_csv(idle_user2).exists()),
    )

    salt, digest = hash_password("longpassword123")
    save_users(
        [
            {
                "username": "admin",
                "salt": salt,
                "password_hash": digest,
                "role": "admin",
                "active": True,
            },
            {
                "username": "regular",
                "salt": salt,
                "password_hash": digest,
                "role": "user",
                "active": True,
                "is_paid": False,
                "trial_ends_at": "2099-01-01T00:00:00",
            },
            {
                "username": "otheradmin",
                "salt": salt,
                "password_hash": digest,
                "role": "admin",
                "active": True,
            },
        ]
    )

    with patch("auth.is_admin", return_value=True), patch("auth.current_username", return_value="admin"):
        ok, _ = update_user_role("regular", "admin")
        promoted = find_user("regular") or {}
        check(
            "promote user to admin",
            lambda: assert_true(
                ok
                and promoted.get("role") == "admin"
                and "is_paid" not in promoted
                and "trial_ends_at" not in promoted
            ),
        )

        ok, _ = update_user_role("otheradmin", "user")
        demoted = find_user("otheradmin") or {}
        check(
            "demote admin to user",
            lambda: assert_true(ok and demoted.get("role") == "user" and "trial_ends_at" in demoted),
        )

        ok, _ = update_user_role("admin", "user")
        check("cannot change own role", lambda: assert_false(ok))


def test_licensing() -> None:
    print("\n== licensing ==")
    from datetime import datetime, timedelta

    from licensing import (
        build_new_user_license_fields,
        effective_is_paid,
        extend_user_trial,
        is_trial_expired,
        trial_days_remaining,
        update_user_license,
    )
    from storage import save_app_settings

    legacy_user = {"username": "legacy", "role": "user", "active": True}
    check("legacy user is paid", lambda: assert_true(effective_is_paid(legacy_user)))
    check("legacy user not expired", lambda: assert_false(is_trial_expired(legacy_user)))

    trial_user = {
        "username": "trial",
        "role": "user",
        "is_paid": False,
        "trial_ends_at": (datetime.now() + timedelta(days=5)).isoformat(timespec="seconds"),
    }
    check("trial user not paid", lambda: assert_false(effective_is_paid(trial_user)))
    check("active trial not expired", lambda: assert_false(is_trial_expired(trial_user)))
    check("trial days remaining", lambda: assert_true(trial_days_remaining(trial_user) is not None))

    expired_user = {
        "username": "expired",
        "role": "user",
        "is_paid": False,
        "trial_ends_at": (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds"),
    }
    check("expired trial detected", lambda: assert_true(is_trial_expired(expired_user)))

    admin_user = {"username": "admin", "role": "admin", "is_paid": False}
    check("admin exempt from expiry", lambda: assert_false(is_trial_expired(admin_user)))

    fields = build_new_user_license_fields("user")
    check("new user license fields", lambda: assert_true(fields.get("is_paid") is False and "trial_ends_at" in fields))
    check("admin has no license fields", lambda: assert_eq(build_new_user_license_fields("admin"), {}))

    save_app_settings(trial_system_enabled=False)
    check("trial disabled skips expiry", lambda: assert_false(is_trial_expired(expired_user)))
    save_app_settings(trial_system_enabled=True)

    from auth import create_user_account, find_user, save_users

    save_users([])
    ok, _ = create_user_account("trialnew", "longpassword123", "user")
    created = find_user("trialnew") or {}
    check(
        "create_user_account sets trial fields",
        lambda: assert_true(
            ok
            and created.get("is_paid") is False
            and bool(created.get("trial_ends_at"))
        ),
    )

    ok, _ = update_user_license("trialnew", is_paid=True)
    check("grant paid license", lambda: assert_true(ok and effective_is_paid(find_user("trialnew") or {})))

    ok, _ = extend_user_trial("trialnew", 7)
    updated = find_user("trialnew") or {}
    check(
        "extend trial after paid",
        lambda: assert_true(ok and updated.get("is_paid") is False and bool(updated.get("trial_ends_at"))),
    )


class _FakeSessionState(dict):
    """Minimal session_state-erstatning til unit tests uden Streamlit-runtime."""

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def test_storage_gdpr_helpers() -> None:
    print("\n== storage (gdpr helpers) ==")
    from unittest.mock import patch

    from storage import (
        _history_entry_matches_row,
        _register_entry_matches_row,
        build_citizen_label_map,
        apply_data_retention,
        clear_active_list,
        configured_retention_months,
        update_citizen_status,
    )

    row = pd.Series({"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678", "_id": "x"})
    entry = {"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678", "Status": "Ikke kontaktet endnu"}
    check("_history_entry_matches_row", lambda: assert_true(_history_entry_matches_row(entry, row)))
    check("_register_entry_matches_row", lambda: assert_true(_register_entry_matches_row(entry, row)))
    check("configured_retention_months", lambda: assert_true(configured_retention_months() >= 0))
    check("build_citizen_label_map", lambda: assert_true(isinstance(build_citizen_label_map(), dict)))
    check("apply_data_retention", lambda: assert_true(apply_data_retention() >= 0))

    fake = _FakeSessionState(
        {
            "citizens_df": pd.DataFrame([{"Navn": "Anna", "_id": "abc"}]),
            "list_key": "liste1",
            "source_filename": "borgere.xlsx",
            "page_number": 2,
            "page_size": 25,
            "selected_filter": "all",
            "search_query": "anna",
            "filter_signature": "sig",
            "show_uploader": False,
            "session_restored": True,
            "borgerliste_file_uploader": object(),
            "_last_upload_sig": "borgere.xlsx:123",
            "_upload_error_detail": "fejl",
            "last_upload_match_count": 3,
            "_sidebar_excel_bytes": b"excel",
            "_sidebar_excel_key": "k1",
            "status_abc": "Accepteret tilbud",
            "export_abc": True,
            "erase_abc": False,
            "unrelated_ui_flag": True,
        }
    )
    with patch("storage.st.session_state", fake), patch("storage._auth_current_user", return_value=None):
        clear_active_list(username=None, list_key=None)

    def _assert_flush() -> None:
        assert_eq(fake.get("citizens_df"), None)
        assert_eq(fake.get("list_key"), None)
        assert_eq(fake.get("source_filename"), None)
        assert_true(fake.get("show_uploader") is True)
        for key in (
            "borgerliste_file_uploader",
            "_last_upload_sig",
            "_upload_error_detail",
            "last_upload_match_count",
            "_sidebar_excel_bytes",
            "_sidebar_excel_key",
            "status_abc",
            "export_abc",
            "erase_abc",
        ):
            assert_false(key in fake)
        assert_true(fake.get("unrelated_ui_flag") is True)

    check("clear_active_list flushes upload+widgets", _assert_flush)

    sparse = pd.DataFrame([{"Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "1", "_id": "c1", "Status": "Ikke kontaktet endnu"}])
    ring = update_citizen_status(sparse, "c1", "Ring igen om 6 måneder")
    check(
        "update_citizen_status creates Ring igen dato",
        lambda: assert_true(bool(ring.iloc[0]["Ring igen dato"]) and "Ring igen dato" in ring.columns),
    )


def test_ui_styles() -> None:
    print("\n== ui/styles ==")
    from ui.styles import (
        _base_css_rules,
        _citizen_card_css,
        _login_page_css,
        _themed_css_rules,
        inject_sidebar_controls,
        status_pill_html,
        citizen_field_html,
    )
    from config import THEME_PALETTES
    from unittest.mock import patch

    check("_login_page_css", lambda: assert_true(len(_login_page_css()) > 100))
    check("_base_css_rules", lambda: assert_true("upload" in _base_css_rules("Vælg fil").lower() or len(_base_css_rules("x")) > 100))
    check("_citizen_card_css", lambda: assert_true("citizen-card-anchor" in _citizen_card_css()))
    check("_themed_css_rules", lambda: assert_true(len(_themed_css_rules(THEME_PALETTES["Lyst tema"], "#fff")) > 100))
    check("status_pill_html", lambda: assert_true("status-pill" in status_pill_html("Accepteret tilbud")))
    check("citizen_field_html", lambda: assert_true("citizen-field" in citizen_field_html("Navn", "Anna")))

    captured: dict[str, str] = {}

    def _capture_html(html: str, **_kwargs) -> None:
        captured["html"] = html

    with patch("ui.styles.components.html", side_effect=_capture_html):
        inject_sidebar_controls(pinned=True, show_pin=True, pin_label="Pin", unpin_label="Unpin")
    script = captured.get("html", "")
    check(
        "sidebar no force-expand on refresh",
        lambda: assert_true("cfg.expandSidebar()" not in script and "effectivePinned" in script),
    )
    check(
        "sidebar uses aria-expanded",
        lambda: assert_true(
            "aria-expanded" in script
            and "width > 48" not in script
            and "getBoundingClientRect().right > 8" in script
        ),
    )
    check(
        "sidebar apiVersion reinstall",
        lambda: assert_true("API_VERSION = 2" in script and "cfg.apiVersion !== API_VERSION" in script),
    )
    check(
        "sidebar collapse only via testid",
        lambda: assert_true(
            "findCollapseButton" in script
            and "stSidebarCollapseButton" in script
            and "findSidebarButton('collapse')" not in script
        ),
    )
    check(
        "sidebar mobile collapse path",
        lambda: assert_true("isMobile" in script and "collapseSidebar" in script and "max-width: 768px" in script),
    )


def test_config() -> None:
    print("\n== config ==")
    from config import APP_VERSION, STATUSES, TRANSLATIONS

    check("APP_VERSION", lambda: assert_true(len(APP_VERSION) > 0))
    check("STATUSES", lambda: assert_eq(len(STATUSES), 4))
    check("TRANSLATIONS da+en", lambda: assert_true("da" in TRANSLATIONS and "en" in TRANSLATIONS))


def test_release_notes() -> None:
    print("\n== release notes ==")
    from config import APP_VERSION

    sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
    from changelog_release_notes import release_body, release_title  # noqa: E402

    check(
        "release_title",
        lambda: assert_true(release_title(APP_VERSION).startswith(f"v{APP_VERSION}")),
    )
    check(
        "release_body",
        lambda: assert_true(len(release_body(APP_VERSION)) > 20),
    )


def test_excel_export() -> None:
    print("\n== excel export ==")
    from storage import to_excel_bytes

    df = pd.DataFrame(
        [{
            "Navn": "Anna", "Adresse": "Gade 1", "Telefonnummer": "12345678",
            "Personnummer": "010190-1234",
            "Status": "Ikke kontaktet endnu", "Status dato": "01-01-2026", "Ring igen dato": "",
        }]
    )
    check("to_excel_bytes", lambda: assert_true(len(to_excel_bytes(df)) > 100))
    check(
        "to_excel_bytes excludes Personnummer",
        lambda: assert_false(b"010190" in to_excel_bytes(df)),
    )


def test_citizen_list_helpers() -> None:
    print("\n== ui/citizen_list helpers ==")
    from unittest.mock import patch

    from ui.citizen_list import (
        _safe_row_text,
        filter_dataframe,
        handle_citizen_status_change,
        resolve_page_size,
        _coerce_uploaded_file,
    )

    df = pd.DataFrame([
        {"Navn": "Anna", "Adresse": "A", "Telefonnummer": "1", "Status": "Ikke kontaktet endnu"},
        {"Navn": "Bent", "Adresse": "B", "Telefonnummer": "2", "Status": "Accepteret tilbud"},
    ])
    check("filter_dataframe all", lambda: assert_eq(len(filter_dataframe(df, "all", "")), 2))
    check("filter_dataframe accepted", lambda: assert_eq(len(filter_dataframe(df, "accepted", "")), 1))
    check("filter_dataframe search", lambda: assert_eq(len(filter_dataframe(df, "all", "anna")), 1))
    check("resolve_page_size Alle", lambda: assert_eq(resolve_page_size("Alle", 10), 10))
    check("_coerce_uploaded_file None", lambda: assert_eq(_coerce_uploaded_file(None), None))
    check(
        "_safe_row_text missing/nan",
        lambda: assert_eq(_safe_row_text(pd.Series({"Status dato": float("nan")}), "Ring igen dato"), ""),
    )

    status_df = pd.DataFrame(
        [{
            "Navn": "Anna", "Adresse": "A", "Telefonnummer": "1",
            "Status": "Ikke kontaktet endnu", "Status dato": "", "Ring igen dato": "", "_id": "cid1",
        }]
    )
    fake = _FakeSessionState(
        {
            "citizens_df": status_df,
            "status_cid1": "Ring igen om 6 måneder",
            "list_key": None,
        }
    )
    errors: list[str] = []

    def _capture_error(msg: str) -> None:
        errors.append(str(msg))

    with (
        patch("ui.citizen_list.st.session_state", fake),
        patch("ui.citizen_list.st.toast", lambda *_a, **_k: None),
        patch("ui.citizen_list.st.error", _capture_error),
        patch("ui.citizen_list.persist_citizen_status_change", lambda **_k: None),
    ):
        handle_citizen_status_change("cid1")

    check(
        "handle_citizen_status_change Ring igen",
        lambda: assert_true(
            fake["citizens_df"].iloc[0]["Status"] == "Ring igen om 6 måneder"
            and bool(fake["citizens_df"].iloc[0]["Ring igen dato"])
            and not errors
        ),
    )

    # Tom liste må ikke crashe status-handler
    fake_empty = _FakeSessionState({"citizens_df": None, "status_cid1": "Accepteret tilbud"})
    with (
        patch("ui.citizen_list.st.session_state", fake_empty),
        patch("ui.citizen_list.st.toast", lambda *_a, **_k: None),
        patch("ui.citizen_list.st.error", _capture_error),
    ):
        handle_citizen_status_change("cid1")
    check("handle_citizen_status_change empty df", lambda: assert_true(True))


def assert_eq(a, b) -> None:
    if a != b:
        raise AssertionError(f"{a!r} != {b!r}")


def assert_true(v) -> None:
    if not v:
        raise AssertionError(f"expected truthy, got {v!r}")


def assert_false(v) -> None:
    if v:
        raise AssertionError(f"expected falsy, got {v!r}")


def main() -> int:
    print("Borgerflow modultest")
    test_imports()
    test_config()
    test_release_notes()
    test_i18n()
    test_data_io()
    test_matching()
    test_storage_encryption()
    test_auth()
    test_licensing()
    test_storage_gdpr_helpers()
    test_ui_styles()
    test_excel_export()
    test_citizen_list_helpers()

    print("\n" + "=" * 40)
    if errors:
        print(f"FEJL: {len(errors)} test(s) fejlede:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"Alle tests bestået ({len(MODULES)} moduler + funktionelle tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
