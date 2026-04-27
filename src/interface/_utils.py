# Shared low-level utilities: date parsing, value extraction, ID normalisation, text helpers.

import re
import unicodedata
import pandas as pd
from datetime import datetime


def _safe_df(record: dict, key: str):
    """Return record[key] DataFrame or None if missing/empty."""
    df = record.get(key)
    return df if (df is not None and not df.empty) else None


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse a string series to datetime, day-first, coercing errors to NaT."""
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
    except (TypeError, ValueError):
        return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _fmt_date(dt, fmt: str = "%d/%m/%Y") -> str:
    """Format a datetime-like value as DD/MM/YYYY; return '—' on failure."""
    try:
        return pd.Timestamp(dt).strftime(fmt)
    except Exception:
        return "—"


def _val(v, fallback: str = "—") -> str:
    """Return a clean string value, or fallback if null/blank."""
    if v is None:
        return fallback
    try:
        if pd.isna(v):
            return fallback
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s if s else fallback


def _is_null_val(v) -> bool:
    """Return True if v is None, NaN, or NaT."""
    if v is None:
        return True
    try:
        return bool(pd.isnull(v))
    except (TypeError, ValueError):
        return False


def _str_id(v) -> str:
    """Convert a numeric-like ID to a clean integer string (e.g. '42.0' -> '42')."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    try:
        return str(int(float(str(v).strip())))
    except Exception:
        return str(v).strip()


def _last_consult_date(record: dict) -> str:
    """Return the most recent consultation date as DD/MM/YYYY, or '—'."""
    df = _safe_df(record, "Consultation")
    if df is None or "Date" not in df.columns:
        return "—"
    dates = _parse_dates(df["Date"]).dropna()
    return _fmt_date(dates.max()) if not dates.empty else "—"


def _n_consult(record: dict) -> int:
    """Return the total number of consultation rows."""
    df = _safe_df(record, "Consultation")
    return len(df) if df is not None else 0


def _sort_consult_desc(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the consultation DataFrame sorted newest-first, with a '_dt' column added."""
    tmp = df.copy()
    if "Date" in tmp.columns:
        tmp["_dt"] = _parse_dates(tmp["Date"])
        tmp = tmp.sort_values("_dt", ascending=False)
    return tmp


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """Return the first candidate column name that exists in df, or None."""
    return next((c for c in candidates if c in df.columns), None)


def _col_lookup(row: pd.Series, candidates: list) -> str:
    """Search a row for the first non-empty value among candidate column names.
    Falls back to Unicode-normalised key comparison to handle encoding variants."""
    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFC", s).strip().lower()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"\s*:\s*", ":", s)
        return s

    normed_row = {_norm(str(k)): v for k, v in row.items()}
    for candidate in candidates:
        v = _val(row.get(candidate), "")
        if v and v != "—":
            return v
        v2 = normed_row.get(_norm(candidate), None)
        if v2 is not None:
            v2 = _val(v2, "")
            if v2 and v2 != "—":
                return v2
    return ""


def _escape(s: str) -> str:
    """Escape special HTML characters."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# Regex patterns for date extraction from free-text fields.
_RE_DATE_FULL  = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b')
_RE_DATE_MONTH = re.compile(r'\b(\d{1,2}[/\-]\d{2,4})\b')
_RE_YEAR_PAREN = re.compile(r'\((\d{2,4})\)')
_RE_YEAR_BARE  = re.compile(r'\b((?:19|20)\d{2})\b')
_RE_YEAR_SHORT = re.compile(r"(?<!\d)'(\d{2})(?!\d)")

_CURRENT_YEAR = datetime.now().year


def _normalise_year(raw: str) -> str:
    """Expand a 2-digit year to 4 digits (00–39 → 2000s, 40–99 → 1900s)."""
    raw = raw.strip()
    if re.fullmatch(r'\d{2}', raw):
        y = int(raw)
        return str(2000 + y) if y < 40 else str(1900 + y)
    if re.fullmatch(r'(?:19|20)\d{2}', raw):
        return raw
    return raw


def _extract_inline_date(text: str) -> str | None:
    """Try to extract a date reference from free text. Returns MM/YYYY, YYYY, or None."""
    if not text or not isinstance(text, str):
        return None
    m = _RE_DATE_FULL.search(text)
    if m:
        raw = m.group(1)
        try:
            dt = pd.to_datetime(raw, dayfirst=True, errors="raise")
            return dt.strftime("%m/%Y")
        except Exception:
            pass
    m = _RE_DATE_MONTH.search(text)
    if m:
        raw = m.group(1)
        parts = re.split(r'[/\-]', raw)
        if len(parts) == 2:
            month_part, year_part = parts
            year_str = _normalise_year(year_part)
            if re.fullmatch(r'(?:19|20)\d{2}', year_str):
                return f"{month_part.zfill(2)}/{year_str}"
    m = _RE_YEAR_PAREN.search(text)
    if m:
        return _normalise_year(m.group(1))
    m = _RE_YEAR_BARE.search(text)
    if m:
        return m.group(1)
    m = _RE_YEAR_SHORT.search(text)
    if m:
        return _normalise_year(m.group(1))
    return None


def _get_date_creation(record: dict) -> str:
    """Return the patient record creation date as DD/MM/YYYY, or ''."""
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return ""
    row = id_df.iloc[0]
    for col in ("DateCreation", "Date création", "Date creation",
                "date_creation", "DATE_CREATION"):
        raw = row.get(col)
        if raw is not None and not _is_null_val(raw):
            try:
                dt = pd.to_datetime(raw, dayfirst=True, errors="raise")
                return dt.strftime("%d/%m/%Y")
            except Exception:
                v = _val(raw, "")
                if v and v != "—":
                    return v
    return ""


def _items_with_dates(
    raw_text: str,
    fallback_date: str,
    max_items: int = 8,
) -> list[dict]:
    """Split semicolon/comma/newline-separated text into labelled items with inline dates.
    Each item is a {label, date} dict. Uses fallback_date when no inline date is found."""
    if not raw_text or raw_text == "—":
        return []
    parts = [
        x.strip()
        for x in re.split(r"[,;\n/]", raw_text)
        if x.strip() and len(x.strip()) > 1
    ][:max_items]
    result = []
    for part in parts:
        inline = _extract_inline_date(part)
        label = part
        if inline:
            label = _RE_DATE_FULL.sub("", label)
            label = _RE_DATE_MONTH.sub("", label)
            label = _RE_YEAR_PAREN.sub("", label)
            label = _RE_YEAR_BARE.sub("", label)
            label = _RE_YEAR_SHORT.sub("", label)
            label = re.sub(r'\s+', ' ', label).strip(" ,-;()")
        if not label:
            label = part
        result.append({"label": label, "date": inline or fallback_date})
    return result
