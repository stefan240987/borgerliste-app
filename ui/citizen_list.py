from __future__ import annotations
import html
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import DeletedFile, UploadedFile
from config import (
    DISPLAY_COLUMNS, FILTER_MAP, INDSATS_FILTER_ALL, MAX_AUDIT_ENTRIES, OVERVIEW_CARDS,
    PAGE_SIZE_OPTIONS, STATUSES, STATUS_HISTORY_PATH, STATUS_TO_FILTER,
    MASTER_REFERENCE_REGISTER_PATH, AUDIT_LOG_PATH,
)
from auth import current_user, current_username
from data_io import read_uploaded_file, repair_text, standardize_dataframe
from i18n import (
    filter_button_label, filter_label, page_size_label, status_label, t,
)
from matching import (
    apply_master_register_statuses, load_master_register, merge_master_register_statuses,
    maybe_sync_master_from_all_user_data, sync_master_register_from_dataframe,
    upsert_master_register_entry, _parse_master_register_payload,
)
from storage import (
    _data_file_lock, _read_json_raw, _safe_storage_key, _touch_master_sync_stamp,
    _write_text_atomic, apply_saved_statuses, clear_citizen_widget_keys,
    collect_citizen_data_export, count_by_status, dataframe_to_state, erase_citizen_data,
    list_storage_key, load_saved_state, save_active_list, save_state, set_selected_filter,
    storage_path, update_citizen_status, upsert_history_entry,
)
from ui.styles import citizen_field_html, status_pill_html


def indsats_filter_options(df: pd.DataFrame | None) -> list[str] | None:
    if df is None or df.empty or "Indsats navn" not in df.columns:
        return None
    values = sorted(
        {
            text
            for text in (repair_text(value) for value in df["Indsats navn"].tolist())
            if text
        },
        key=str.casefold,
    )
    return values or None


def filter_dataframe(
    df: pd.DataFrame,
    filter_key: str,
    search: str,
    indsats_filter: str | None = None,
) -> pd.DataFrame:
    selected = FILTER_MAP.get(filter_key, STATUSES)
    filtered = df[df["Status"].isin(selected)].copy()
    if search.strip():
        needle = search.strip().lower()
        filtered = filtered[
            filtered["Navn"].str.lower().str.contains(needle, na=False)
            | filtered["Adresse"].str.lower().str.contains(needle, na=False)
            | filtered["Telefonnummer"].str.lower().str.contains(needle, na=False)
        ]
    if (
        indsats_filter
        and indsats_filter != INDSATS_FILTER_ALL
        and "Indsats navn" in filtered.columns
    ):
        filtered = filtered[
            filtered["Indsats navn"].map(repair_text) == indsats_filter
        ]
    return filtered.reset_index(drop=True)


def kpi_card_label(filter_value: str, status: str | None) -> str:
    if status:
        return status_label(status, short=True)
    return filter_label("all")


def render_overview_kpi_card(
    filter_value: str,
    status: str | None,
    count: int,
    selected: str,
) -> None:
    is_active = selected == filter_value
    with st.container(border=True):
        st.markdown('<div class="kpi-overview-card">', unsafe_allow_html=True)
        if status:
            st.markdown(status_pill_html(status, short=True), unsafe_allow_html=True)
        else:
            st.markdown(
                f'<span class="status-pill status-pill--all">{filter_label("all")}</span>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<p class="kpi-number">{count}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button(
        filter_button_label(filter_value),
        key=f"kpi_filter_{filter_value}",
        use_container_width=True,
        type="primary" if is_active else "secondary",
        help=t("overview_filter_hint"),
    ):
        if is_active and filter_value != "all":
            set_selected_filter("all")
        elif not is_active:
            set_selected_filter(filter_value)
        st.rerun()


def render_status_metrics(df: pd.DataFrame) -> None:
    counts = count_by_status(df)
    selected = st.session_state.get("selected_filter", "all")

    st.markdown(f"#### {t('overview')}")
    st.caption(t("overview_filter_hint"))
    st.markdown('<div id="kpi-overview-anchor"></div>', unsafe_allow_html=True)

    card_counts = {
        "all": len(df),
        **{STATUS_TO_FILTER[status]: counts[status] for status in STATUSES},
    }

    cols = st.columns(len(OVERVIEW_CARDS))
    for col, (filter_value, status) in zip(cols, OVERVIEW_CARDS):
        with col:
            render_overview_kpi_card(
                filter_value,
                status,
                card_counts[filter_value],
                selected,
            )


def sync_session_df_with_master() -> bool:
    """Opdater den aktive liste med seneste master-status fra alle brugere."""
    if st.session_state.pop("_skip_master_sync_once", False):
        return False

    df = st.session_state.get("citizens_df")
    if df is None or df.empty:
        return False

    maybe_sync_master_from_all_user_data()
    register = load_master_register()
    updated, _matched = merge_master_register_statuses(df, register)

    status_cols = ["Status", "Status dato", "Ring igen dato"]
    if all(updated[col].equals(df[col]) for col in status_cols if col in df.columns and col in updated.columns):
        return False

    st.session_state.citizens_df = updated.reset_index(drop=True)
    list_key = st.session_state.get("list_key")
    if list_key:
        save_state(list_key, dataframe_to_state(st.session_state.citizens_df))
    save_active_list(st.session_state.citizens_df)
    return True


def handle_file_upload(uploaded) -> bool:
    try:
        raw_df, _detected_encoding = read_uploaded_file(uploaded)
        base_df = standardize_dataframe(raw_df)
        key = list_storage_key(uploaded.name, base_df)

        register = load_master_register()
        full_df, matched_count = apply_master_register_statuses(base_df, register)
        list_state = load_saved_state(key)
        if list_state:
            full_df = apply_saved_statuses(full_df, list_state)
        full_df, _master_merged = merge_master_register_statuses(full_df, register)
        sync_master_register_from_dataframe(full_df)

        clear_citizen_widget_keys()
        st.session_state.list_key = key
        st.session_state.source_filename = uploaded.name
        st.session_state.citizens_df = full_df
        st.session_state.last_upload_match_count = matched_count
        st.session_state.page_number = 0
        st.session_state.page_size = 25
        st.session_state.selected_filter = "all"
        st.session_state.indsats_filter = INDSATS_FILTER_ALL
        st.session_state.search_query = ""
        st.session_state.filter_signature = None
        st.session_state.show_uploader = False
        st.session_state.session_restored = False
        st.session_state.pop("_sidebar_excel_key", None)
        st.session_state.pop("_sidebar_excel_bytes", None)
        save_state(key, dataframe_to_state(full_df))
        save_active_list(full_df)
        maybe_sync_master_from_all_user_data(force=True)
        return True
    except Exception as exc:
        st.session_state._upload_error_detail = str(exc)
        st.error(t("upload_error"))
        return False


def _coerce_uploaded_file(value: object) -> UploadedFile | None:
    """Accepter kun rigtige uploads — Streamlit kan efterlade DeletedFile i session state."""
    if value is None:
        return None
    if isinstance(value, DeletedFile):
        return None
    if isinstance(value, UploadedFile):
        return value
    if isinstance(value, list):
        for item in value:
            coerced = _coerce_uploaded_file(item)
            if coerced is not None:
                return coerced
        return None
    name = getattr(value, "name", None)
    if name and callable(getattr(value, "read", None)):
        return value  # type: ignore[return-value]
    return None


def _clear_stale_upload_state() -> None:
    raw = st.session_state.get("borgerliste_file_uploader")
    if raw is None:
        return
    if _coerce_uploaded_file(raw) is None:
        st.session_state.pop("borgerliste_file_uploader", None)


def _upload_signature(uploaded: UploadedFile) -> str:
    size = getattr(uploaded, "size", None)
    if size is None:
        try:
            uploaded.seek(0, os.SEEK_END)
            size = uploaded.tell()
            uploaded.seek(0)
        except Exception:
            size = 0
    return f"{uploaded.name}:{size}"


def render_upload_section() -> None:
    list_loaded = st.session_state.citizens_df is not None and not st.session_state.citizens_df.empty
    expanded = not list_loaded or st.session_state.show_uploader
    label = t("upload_expander_change") if list_loaded else t("upload_expander")

    with st.expander(label, expanded=expanded):
        if list_loaded and not st.session_state.show_uploader:
            matched = st.session_state.get("last_upload_match_count")
            if matched is not None:
                st.success(
                    t(
                        "upload_loaded_with_matches",
                        count=len(st.session_state.citizens_df),
                        matched=matched,
                    )
                )
            else:
                st.success(
                    t("upload_loaded", filename=st.session_state.source_filename, count=len(st.session_state.citizens_df))
                )
            if st.button(t("upload_select_new"), use_container_width=True):
                st.session_state.show_uploader = True
                st.rerun()
        else:
            st.caption(t("upload_hint_new") if list_loaded else t("upload_hint"))
            st.markdown(f"<p class='upload-hint'>{t('upload_drag_hint')}</p>", unsafe_allow_html=True)

            uploaded = st.file_uploader(
                t("upload_browse"),
                type=["csv", "xlsx", "xls"],
                label_visibility="collapsed",
                key="borgerliste_file_uploader",
            )
            uploaded = _coerce_uploaded_file(uploaded)
            if uploaded is None:
                uploaded = _coerce_uploaded_file(st.session_state.get("borgerliste_file_uploader"))
            if uploaded is None:
                _clear_stale_upload_state()
                st.session_state.pop("_last_upload_sig", None)
                st.session_state.pop("_upload_error_detail", None)
            else:
                signature = _upload_signature(uploaded)
                needs_upload = st.session_state.get("_last_upload_sig") != signature
                list_empty = (
                    st.session_state.citizens_df is None or st.session_state.citizens_df.empty
                )
                if not needs_upload and list_empty:
                    # Liste er flushet (fx logout) — genindlæs ikke zombie-upload fra widget-state.
                    st.session_state.pop("borgerliste_file_uploader", None)
                    st.session_state.pop("_last_upload_sig", None)
                    st.session_state.pop("_upload_error_detail", None)
                    needs_upload = False
                if needs_upload:
                    if handle_file_upload(uploaded):
                        st.session_state._last_upload_sig = signature
                        st.session_state.pop("borgerliste_file_uploader", None)
                        st.rerun()
                    else:
                        st.session_state.pop("_last_upload_sig", None)

            if detail := st.session_state.get("_upload_error_detail"):
                st.caption(detail)

            if list_loaded and st.button(t("upload_keep_current"), use_container_width=True):
                st.session_state.show_uploader = False
                st.rerun()


def resolve_page_size(selected: int | str, total_rows: int) -> int:
    if selected == "Alle":
        return max(total_rows, 1)
    return int(selected)


def render_pagination_bar(
    total_rows: int,
    page_size: int,
    page_number: int,
    indsats_options: list[str] | None = None,
) -> tuple[int, int, int]:
    total_pages = max(1, (total_rows + page_size - 1) // page_size) if total_rows else 1
    page_number = min(max(page_number, 0), total_pages - 1)
    start = page_number * page_size
    end = min(start + page_size, total_rows)

    if total_pages > 1:
        nav_prev, nav_info, nav_next = st.columns([1, 2.2, 1])

        with nav_prev:
            if st.button(t("prev"), disabled=page_number <= 0, use_container_width=True):
                st.session_state.page_number = max(page_number - 1, 0)
                st.rerun()

        with nav_info:
            info_key = "page_info_one" if page_size == 1 else "page_info"
            st.markdown(
                f"<div class='page-info'>{t(info_key, current=page_number + 1, total=total_pages)}</div>",
                unsafe_allow_html=True,
            )

        with nav_next:
            if st.button(t("next"), disabled=page_number >= total_pages - 1, use_container_width=True):
                st.session_state.page_number = min(page_number + 1, total_pages - 1)
                st.rerun()

    if indsats_options:
        size_cols = st.columns([0.8, 1.2, 1.4, 0.8])
        page_size_col = size_cols[1]
        indsats_col = size_cols[2]
    else:
        size_cols = st.columns([1, 1.2, 1])
        page_size_col = size_cols[1]
        indsats_col = None

    with page_size_col:
        page_size_choice = st.selectbox(
            t("page_size_label"),
            PAGE_SIZE_OPTIONS,
            index=PAGE_SIZE_OPTIONS.index(st.session_state.page_size)
            if st.session_state.page_size in PAGE_SIZE_OPTIONS
            else 1,
            format_func=page_size_label,
        )
        if page_size_choice != st.session_state.page_size:
            st.session_state.page_size = page_size_choice
            st.session_state.page_number = 0
            st.rerun()

    if indsats_col is not None and indsats_options:
        choices = [INDSATS_FILTER_ALL, *indsats_options]
        current_indsats = st.session_state.get("indsats_filter", INDSATS_FILTER_ALL)
        if current_indsats not in choices:
            current_indsats = INDSATS_FILTER_ALL
            st.session_state.indsats_filter = INDSATS_FILTER_ALL
        with indsats_col:
            indsats_choice = st.selectbox(
                t("indsats_filter_label"),
                choices,
                index=choices.index(current_indsats),
                format_func=lambda value: (
                    t("indsats_filter_all") if value == INDSATS_FILTER_ALL else value
                ),
            )
        if indsats_choice != st.session_state.get("indsats_filter", INDSATS_FILTER_ALL):
            st.session_state.indsats_filter = indsats_choice
            st.session_state.page_number = 0
            st.rerun()

    st.session_state.page_number = page_number
    return start, end, page_number


def persist_citizen_status_change(
    *,
    updated: pd.DataFrame,
    updated_row: pd.Series,
    old_status: str,
    list_key: str | None,
) -> None:
    """Gem statusændring i én låst transaktion (liste, master, history, audit)."""
    audit_entry = {
        "id": secrets.token_hex(8),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "username": current_username(),
        "role": current_user().get("role", "user") if current_user() else "user",
        "citizen_id": str(updated_row["_id"]),
        "old_status": old_status,
        "new_status": str(updated_row["Status"]),
        "list_key": list_key,
    }

    with _data_file_lock(shared=False):
        if list_key:
            key = _safe_storage_key(list_key)
            _write_text_atomic(
                storage_path(key),
                json.dumps(dataframe_to_state(updated), ensure_ascii=False, indent=2) + "\n",
            )

        register_payload = _read_json_raw(MASTER_REFERENCE_REGISTER_PATH, {"cleared": False, "entries": []})
        register_state = _parse_master_register_payload(register_payload)
        register = list(register_state["entries"])  # type: ignore[arg-type]
        upsert_master_register_entry(updated_row, register)
        _write_text_atomic(
            MASTER_REFERENCE_REGISTER_PATH,
            json.dumps({"cleared": False, "entries": register}, ensure_ascii=False, indent=2) + "\n",
        )

        history = _read_json_raw(STATUS_HISTORY_PATH, {})
        if not isinstance(history, dict):
            history = {}
        upsert_history_entry(updated_row, history)
        _write_text_atomic(
            STATUS_HISTORY_PATH,
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        )

        audit_payload = _read_json_raw(AUDIT_LOG_PATH, {"entries": []})
        if isinstance(audit_payload, dict) and isinstance(audit_payload.get("entries"), list):
            entries = [entry for entry in audit_payload["entries"] if isinstance(entry, dict)]
        elif isinstance(audit_payload, list):
            entries = [entry for entry in audit_payload if isinstance(entry, dict)]
        else:
            entries = []
        entries.append(audit_entry)
        _write_text_atomic(
            AUDIT_LOG_PATH,
            json.dumps({"entries": entries[-MAX_AUDIT_ENTRIES:]}, ensure_ascii=False, indent=2) + "\n",
        )

    save_active_list(updated)
    _touch_master_sync_stamp()


def handle_citizen_status_change(citizen_id: str) -> None:
    widget_key = f"status_{citizen_id}"
    new_status = st.session_state.get(widget_key)
    if new_status is None:
        return

    df = st.session_state.get("citizens_df")
    if df is None or df.empty or "_id" not in df.columns:
        return

    try:
        mask = df["_id"] == citizen_id
        if not mask.any():
            return

        old_status = df.loc[mask, "Status"].iloc[0]
        if new_status == old_status:
            return

        updated = update_citizen_status(df, citizen_id, new_status)
        st.session_state.citizens_df = updated
        updated_row = updated[updated["_id"] == citizen_id].iloc[0]
        persist_citizen_status_change(
            updated=updated,
            updated_row=updated_row,
            old_status=str(old_status),
            list_key=st.session_state.get("list_key"),
        )
        st.session_state._skip_master_sync_once = True
        st.toast(t("status_saved"), icon="✅")
    except Exception as exc:
        st.session_state._status_error_detail = str(exc)
        st.error(t("status_save_error"))


def _citizen_status_change_handler(citizen_id: str):
    def _handler() -> None:
        handle_citizen_status_change(citizen_id)

    return _handler


def _safe_row_text(row: pd.Series, column: str) -> str:
    value = row[column] if column in row.index else ""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "nat"} else text


def render_citizen_card(row: pd.Series) -> None:
    row_status = _safe_row_text(row, "Status") or STATUSES[0]
    status_key = STATUS_TO_FILTER.get(row_status, "not_contacted")
    st.markdown(
        f'<div class="citizen-card-anchor" data-status="{html.escape(status_key)}"></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(status_pill_html(row_status, short=True), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_name"), row["Navn"], emphasized=True), unsafe_allow_html=True)
        personnummer = repair_text(row.get("Personnummer", ""))
        if personnummer:
            st.markdown(citizen_field_html(t("col_personnummer"), personnummer), unsafe_allow_html=True)
        indsats_navn = repair_text(row.get("Indsats navn", ""))
        if indsats_navn:
            st.markdown(citizen_field_html(t("col_indsats_navn"), indsats_navn), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_address"), row["Adresse"]), unsafe_allow_html=True)
        st.markdown(citizen_field_html(t("col_phone"), row["Telefonnummer"]), unsafe_allow_html=True)

        widget_key = f"status_{row['_id']}"
        desired_status = row_status if row_status in STATUSES else STATUSES[0]
        # Undgå Streamlit-konflikt mellem index= og eksisterende session-værdi.
        if widget_key not in st.session_state or st.session_state.get(widget_key) not in STATUSES:
            st.session_state[widget_key] = desired_status
        st.selectbox(
            t("change_status"),
            STATUSES,
            key=widget_key,
            format_func=lambda s: status_label(s, short=True),
            on_change=_citizen_status_change_handler(row["_id"]),
        )

        status_dato = _safe_row_text(row, "Status dato")
        if status_dato:
            st.caption(t("last_updated", date=status_dato))
        ring_igen = _safe_row_text(row, "Ring igen dato")
        if ring_igen:
            st.caption(t("call_again_date", date=ring_igen))

        with st.expander(t("gdpr_citizen_title"), expanded=False):
            export_payload = collect_citizen_data_export(row)
            st.download_button(
                t("gdpr_export_citizen"),
                data=json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=t("gdpr_export_filename", citizen_id=str(row["_id"])),
                mime="application/json",
                key=f"export_{row['_id']}",
                use_container_width=True,
            )
            confirm_key = f"erase_confirm_{row['_id']}"
            if st.session_state.get(confirm_key):
                st.warning(t("gdpr_erase_warning"))
                col_cancel, col_confirm = st.columns(2)
                with col_cancel:
                    if st.button(t("gdpr_erase_cancel"), key=f"erase_cancel_{row['_id']}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with col_confirm:
                    if st.button(t("gdpr_erase_confirm"), key=f"erase_confirm_btn_{row['_id']}", use_container_width=True):
                        erase_citizen_data(row)
                        st.session_state.pop(confirm_key, None)
                        st.toast(t("gdpr_erase_done"), icon="✅")
                        st.rerun()
            elif st.button(t("gdpr_erase_citizen"), key=f"erase_{row['_id']}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()


def render_citizen_list(page_slice: pd.DataFrame) -> None:
    if page_slice.empty:
        st.info(t("no_citizens_match"))
        return

    for _, row in page_slice.iterrows():
        render_citizen_card(row)

