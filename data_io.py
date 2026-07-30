from __future__ import annotations
import hashlib
import os
import re
from io import BytesIO
import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile
from config import (
    COLUMN_ALIASES, CSV_ENCODINGS, DANISH_CHARS, MAX_UPLOAD_BYTES, MOJIBAKE_MARKERS,
)
from i18n import t


def normalize_header(value: object) -> str:
    return repair_text(re.sub(r"\s+", " ", str(value).strip().lower()))


def looks_like_mojibake(text: str) -> bool:
    if not text:
        return False
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        return True
    return "Ã" in text and not any(ch in text for ch in DANISH_CHARS)


def repair_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if not text:
        return text

    fixed = text
    for _ in range(4):
        if not looks_like_mojibake(fixed):
            break
        changed = False
        for encoding in ("latin-1", "cp1252", "iso-8859-1"):
            try:
                candidate = fixed.encode(encoding).decode("utf-8").strip()
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if candidate and candidate != fixed:
                fixed = candidate
                changed = True
                break
        if not changed:
            break
    return fixed


def repair_dataframe_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.select_dtypes(include=["object", "string"]).columns:
        out[column] = out[column].map(repair_text)
    return out


def encoding_quality_score(df: pd.DataFrame) -> float:
    sample = " ".join(
        str(value)
        for column in df.select_dtypes(include=["object", "string"]).columns
        for value in df[column].dropna().head(200)
    )
    if not sample:
        return 0.0
    score = 0.0
    score += sum(3 for ch in DANISH_CHARS if ch in sample)
    score -= sum(5 for marker in MOJIBAKE_MARKERS if marker in sample)
    score -= sample.count("Ã") * 4
    replacement = sample.count("�") + sample.count("ï¿½")
    score -= replacement * 6
    return score


def read_csv_bytes(raw: bytes) -> tuple[pd.DataFrame, str]:
    best_df: pd.DataFrame | None = None
    best_encoding = "utf-8"
    best_score = float("-inf")
    last_error: Exception | None = None

    for encoding in CSV_ENCODINGS:
        try:
            candidate = pd.read_csv(BytesIO(raw), encoding=encoding)
            score = encoding_quality_score(candidate)
            if score > best_score:
                best_score = score
                best_df = candidate
                best_encoding = encoding
        except Exception as exc:
            last_error = exc

    if best_df is None:
        raise ValueError(t("upload_error"))

    return repair_dataframe_text(best_df), best_encoding


def read_uploaded_file(uploaded_file) -> tuple[pd.DataFrame, str]:
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        raw = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))
        df, encoding = read_csv_bytes(raw)
        return df, encoding
    if name.endswith((".xlsx", ".xls")):
        raw = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError(t("upload_too_large", max_mb=MAX_UPLOAD_BYTES // (1024 * 1024)))
        df = pd.read_excel(BytesIO(raw))
        return repair_dataframe_text(df), "excel"
    raise ValueError(t("upload_error"))


def find_column(df: pd.DataFrame, target: str) -> str | None:
    aliases = {normalize_header(alias) for alias in COLUMN_ALIASES[target]}
    for col in df.columns:
        if normalize_header(col) in aliases:
            return col
    return None


def standardize_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    for target in COLUMN_ALIASES:
        source = find_column(raw, target)
        if source is None:
            raise ValueError(t("missing_column", column=target))
        mapping[target] = source

    df = raw[[mapping["Navn"], mapping["Adresse"], mapping["Telefonnummer"]]].copy()
    df.columns = ["Navn", "Adresse", "Telefonnummer"]
    for column in df.columns:
        df[column] = df[column].map(repair_text)
    df = df[df["Navn"].str.len() > 0].reset_index(drop=True)
    return df


def citizen_id(row: pd.Series) -> str:
    key = f"{row['Navn']}|{row['Adresse']}|{row['Telefonnummer']}".lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D+", "", str(phone or ""))

