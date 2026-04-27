# Builds act rows from patient record data and renders them in Streamlit.

import re
import pandas as pd
import streamlit as st

from _utils import (
    _safe_df, _parse_dates, _fmt_date, _val, _is_null_val, _str_id,
    _sort_consult_desc, _escape,
)

# Maps document description keywords to a canonical label and category.
_EXAM_LABEL_MAP: list[tuple[str, list[str], str]] = [
    ("OCT",              ["oct"],                                                        "img"),
    ("Angiographie",     ["angio", "ffa"],                                              "img"),
    ("Rétinographie",    ["rétino", "retino", "fond d", "rétinographie", "retinographie"], "img"),
    ("Imagerie",         ["imagenet", "imagerie"],                                      "img"),
    ("Lampe à fente",    ["laf", "lampe à fente", "lampe a fente", "lamp fente"],       "exam"),
    ("Champ visuel",     ["champ visuel", "périmét", "perimetrie", "périmètre"],        "exam"),
    ("Biométrie",        ["biométrie", "biometrie", "iolmaster", "iol master"],         "exam"),
    ("Pachymétrie",      ["pachy"],                                                     "exam"),
    ("Topo cornéenne",   ["topograph", "topo cor"],                                     "exam"),
    ("Kératométrie",     ["kérato", "kerato"],                                          "exam"),
    ("Laser",            ["laser"],                                                     "proc"),
    ("Injection IVT",    ["ivt", "injection intra", "injection ivt"],                   "proc"),
]

# CSS class per exam category.
_BADGE_CSS: dict[str, str] = {
    "img":  "ck-chip ck-chip-img",
    "exam": "ck-chip ck-chip-exam",
    "proc": "ck-chip ck-chip-proc",
}


def _normalize_exam_label(raw: str) -> tuple[str, str]:
    """Match raw description to a canonical label and category. Returns ("", "") if no match."""
    if not raw or raw == "—":
        return ("", "")
    clean = raw.strip().lower()
    # Strip eye-side qualifiers before matching.
    clean = re.sub(r'\b(od|og|odg|od/og|oed)\b', '', clean).strip()
    for canonical, patterns, category in _EXAM_LABEL_MAP:
        for pat in patterns:
            if pat in clean:
                return (canonical, category)
    # No match: use raw label, truncated if needed.
    label = raw.strip()
    if len(label) > 36:
        label = label[:36] + "…"
    return (label.title(), "")


def _build_actes_rows(record: dict) -> list[dict]:
    """Aggregate consultations and linked documents into act rows keyed by (date, doctor).
    Each row: {date_ts, date_str, motif, tech_actes, doctor}. Sorted newest-first."""
    consult_df = _safe_df(record, "Consultation")
    ker_df     = _safe_df(record, "tKERATO")
    ref_df     = _safe_df(record, "tREFRACTION")
    docs_df    = _safe_df(record, "Documents")

    # Collect consultation IDs that have linked kerato/refraction data.
    nc_has_kerato: set[str] = set()
    if ker_df is not None and "NumConsult" in ker_df.columns:
        nc_has_kerato = {_str_id(v) for v in ker_df["NumConsult"] if _str_id(v)}

    nc_has_refrac: set[str] = set()
    if ref_df is not None and "NumConsult" in ref_df.columns:
        nc_has_refrac = {_str_id(v) for v in ref_df["NumConsult"] if _str_id(v)}

    groups: dict[tuple, dict] = {}

    def _upsert(date_ts, date_str: str, doctor: str,
                motif: str, tech: list[tuple[str, str]]):
        """Insert or update a group entry; avoid duplicate exam labels."""
        key = (date_str, doctor)
        if key not in groups:
            groups[key] = {
                "date_ts":    date_ts,
                "date_str":   date_str,
                "motif":      motif,
                "tech_actes": [],
                "doctor":     doctor,
            }
        if not groups[key]["motif"] and motif:
            groups[key]["motif"] = motif
        seen_labels = {t[0] for t in groups[key]["tech_actes"]}
        for label, cat in tech:
            if label and label not in seen_labels:
                groups[key]["tech_actes"].append((label, cat))
                seen_labels.add(label)

    # Build rows from consultations.
    if consult_df is not None:
        tmp = _sort_consult_desc(consult_df)
        for _, row in tmp.iterrows():
            dt = row.get("_dt")
            if _is_null_val(dt):
                continue
            date_str = _fmt_date(dt)
            doctor   = _val(row.get("Doctor_Name"), "")
            if doctor == "—":
                doctor = ""
            motif = _val(row.get("DOMINANTE"), "")
            if motif == "—":
                motif = ""
            nc   = _str_id(row.get("N° consultation"))
            tech = []
            if nc and nc in nc_has_kerato:
                tech.append(("Kératométrie", "exam"))
            if nc and nc in nc_has_refrac:
                tech.append(("Réfraction", "exam"))
            _upsert(dt, date_str, doctor, motif, tech)

    # Enrich rows with linked documents; create a new row if no matching date exists.
    if docs_df is not None and "Date" in docs_df.columns:
        for _, row in docs_df.iterrows():
            raw_dt = row.get("Date")
            dts    = _parse_dates(pd.Series([raw_dt]))
            dt     = dts.iloc[0] if not dts.empty else None
            if _is_null_val(dt):
                continue
            date_str = _fmt_date(dt)
            raw_desc = row.get("DESCRIPTIONS") or row.get("Type") or ""
            desc = _val(raw_desc, "")
            if not desc or desc == "—":
                continue
            label, cat = _normalize_exam_label(desc)
            if not label:
                continue
            matched_key = next((k for k in groups if k[0] == date_str), None)
            if matched_key:
                seen = {t[0] for t in groups[matched_key]["tech_actes"]}
                if label not in seen:
                    groups[matched_key]["tech_actes"].append((label, cat))
            else:
                _upsert(dt, date_str, "", "", [(label, cat)])

    return sorted(groups.values(), key=lambda x: x["date_ts"], reverse=True)


def _filter_record_by_date(record: dict, date_str: str) -> dict:
    """Return a shallow copy of record with all DataFrames filtered to a single date."""
    consult_df = _safe_df(record, "Consultation")

    # Collect consultation IDs matching the target date.
    matching_nc: set[str] = set()
    if consult_df is not None and "Date" in consult_df.columns:
        tmp = consult_df.copy()
        tmp["_dt_fmt"] = _parse_dates(tmp["Date"]).dt.strftime("%d/%m/%Y")
        for _, row in tmp[tmp["_dt_fmt"] == date_str].iterrows():
            nc = _str_id(row.get("N° consultation"))
            if nc:
                matching_nc.add(nc)

    filtered: dict = {}
    for key, df in record.items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            filtered[key] = df
            continue

        if key == "Consultation" and "Date" in df.columns:
            tmp = df.copy()
            tmp["_dt_fmt"] = _parse_dates(tmp["Date"]).dt.strftime("%d/%m/%Y")
            filtered[key] = tmp[tmp["_dt_fmt"] == date_str].drop(columns=["_dt_fmt"])

        elif key in ("tKERATO", "tREFRACTION") and "NumConsult" in df.columns:
            # Keep only rows linked to matching consultations.
            if matching_nc:
                mask = df["NumConsult"].astype(str).isin(matching_nc)
                filtered[key] = df[mask]
            else:
                filtered[key] = df.iloc[0:0]

        elif key == "Documents" and "Date" in df.columns:
            tmp = df.copy()
            tmp["_dt_fmt"] = _parse_dates(tmp["Date"]).dt.strftime("%d/%m/%Y")
            filtered[key] = tmp[tmp["_dt_fmt"] == date_str].drop(columns=["_dt_fmt"])

        else:
            filtered[key] = df

    return filtered


_ACTES_CHIP_CSS = """
<style>
.ck-act-chips { display:flex; flex-wrap:wrap; gap:4px; margin-top:3px; }
.ck-chip {
    font-size:0.63rem; font-weight:700; padding:2px 8px;
    border-radius:4px; white-space:nowrap; line-height:1.5;
    border:1px solid transparent; letter-spacing:0.02em;
}
.ck-chip-img  { background:#F5F3FF; color:#4C1D95; border-color:#C4B5FD; }
.ck-chip-exam { background:#ECFDF5; color:#065F46; border-color:#6EE7B7; }
.ck-chip-proc { background:#FFFBEB; color:#92400E; border-color:#FCD34D; }
.ck-chip-grey { background:#F9FAFB; color:#374151; border-color:#D1D5DB; }
</style>
"""


def _render_actes_streamlit(
    rows: list[dict],
    n_total: int,
    record: dict,
    generate_pdf_bytes_fn,
    pdf_available: bool,
    full_name: str,
    dob_str: str,
    patient_id: str,
) -> None:
    """Render the act table (max 10 rows) with per-day PDF download buttons."""
    st.markdown(_ACTES_CHIP_CSS, unsafe_allow_html=True)

    last_date = rows[0]["date_str"] if rows else "—"

    # Section header with visit count and last visit date.
    st.markdown(
        f'<div style="font-size:0.69rem;font-weight:800;color:#1B3A6B;'
        f'letter-spacing:0.07em;text-transform:uppercase;'
        f'border-bottom:1px solid #E2E8F0;padding-bottom:5px;margin-bottom:8px;'
        f'font-family:\'Segoe UI\',sans-serif;">'
        f'📋&nbsp; Tableau des Actes'
        f'<span style="font-weight:400;color:#6B7280;font-size:0.62rem;margin-left:10px;">'
        f'{n_total} visite(s) · Dernier acte : {_escape(last_date)}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    if not rows:
        st.info("Aucun acte enregistré pour ce patient.")
        return

    col_w = [1.2, 4, 2, 1.6]

    # Column headers.
    h_date, h_actes, h_doctor, h_pdf = st.columns(col_w)
    for col, label in zip(
        [h_date, h_actes, h_doctor, h_pdf],
        ["Date", "Actes réalisés", "Praticien", "Rapport"],
    ):
        col.markdown(
            f'<div style="font-size:0.60rem;font-weight:800;text-transform:uppercase;'
            f'letter-spacing:0.10em;color:#6B7280;padding-bottom:5px;'
            f'border-bottom:2px solid #E5E7EB;">{label}</div>',
            unsafe_allow_html=True,
        )

    visible_rows = rows[:10]
    for i, r in enumerate(visible_rows):
        c_date, c_actes, c_doctor, c_pdf = st.columns(col_w)

        with c_date:
            st.markdown(
                f'<div style="font-size:0.84rem;font-weight:700;color:#1B3A6B;'
                f'padding-top:10px;">{_escape(r["date_str"])}</div>',
                unsafe_allow_html=True,
            )

        with c_actes:
            motif_text = _escape(r["motif"][:80]) if r["motif"] else "Consultation"
            motif_style = (
                "font-size:0.84rem;font-weight:600;color:#111827;padding-top:9px;"
                if r["motif"]
                else "font-size:0.79rem;font-style:italic;color:#6B7280;padding-top:9px;"
            )
            # Build chip HTML for each exam type.
            chips_html = ""
            if r["tech_actes"]:
                chips = [
                    f'<span class="{_BADGE_CSS.get(cat, "ck-chip ck-chip-grey")}">'
                    f'{_escape(label)}</span>'
                    for label, cat in r["tech_actes"]
                ]
                chips_html = f'<div class="ck-act-chips">{"".join(chips)}</div>'
            st.markdown(
                f'<div style="{motif_style}">{motif_text}</div>{chips_html}',
                unsafe_allow_html=True,
            )

        with c_doctor:
            doctor_text = _escape(r["doctor"]) if r["doctor"] else "—"
            st.markdown(
                f'<div style="font-size:0.78rem;color:#6B7280;padding-top:10px;">'
                f'{doctor_text}</div>',
                unsafe_allow_html=True,
            )

        with c_pdf:
            date_str  = r["date_str"]
            safe_date = date_str.replace("/", "-")
            safe_name = full_name.replace(" ", "_")
            filename  = f"consultation_{safe_name}_{safe_date}.pdf"
            btn_key   = f"pdf_acte_{i}_{date_str}"

            st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
            if pdf_available and generate_pdf_bytes_fn is not None:
                # Filter record to the selected date and generate the PDF.
                record_filtre = _filter_record_by_date(record, date_str)
                pdf_bytes = generate_pdf_bytes_fn(
                    record_filtre, full_name, dob_str, patient_id
                )
                st.download_button(
                    label="📄 PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=btn_key,
                    help=f"Télécharger le rapport du {date_str}",
                    use_container_width=True,
                )
            else:
                # fpdf2 not installed: show disabled button.
                st.button(
                    "📄 PDF",
                    key=btn_key,
                    disabled=True,
                    help="fpdf2 non installé — pip install fpdf2",
                    use_container_width=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        # Row separator.
        if i < len(visible_rows) - 1:
            st.markdown(
                '<hr style="border:none;border-top:1px solid #E5E7EB;margin:2px 0;">',
                unsafe_allow_html=True,
            )

    if len(rows) > 10:
        st.caption(f"Affichage des 10 visites les plus récentes sur {len(rows)} au total.")