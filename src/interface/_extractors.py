# Clinical data extractors for the Cockpit Dashboard.
# All functions take a `record` dict and return structured Python objects.

import re
import pandas as pd
from datetime import datetime

from _utils import (
    _safe_df, _parse_dates, _fmt_date, _val, _is_null_val, _str_id,
    _sort_consult_desc, _find_col, _col_lookup,
    _last_consult_date, _n_consult,
    _get_date_creation, _items_with_dates,
    _RE_DATE_FULL, _RE_DATE_MONTH, _RE_YEAR_PAREN, _RE_YEAR_BARE, _RE_YEAR_SHORT,
)

# Column name candidates for visual acuity in Consultation and tREFRACTION tables.
_AV_CANDIDATES = {
    "avdl_sc":     ["AVscOD", "AV sc OD", "AVSCOD", "AVD sc", "AVDsc"],
    "avdl_cc":     ["AVccOD", "AV cc OD", "AVCCOD", "AVD cc", "AVDcc"],
    "avgl_sc":     ["AVscOG", "AV sc OG", "AVSCOG", "AVG sc", "AVGsc"],
    "avgl_cc":     ["AVccOG", "AV cc OG", "AVCCOG", "AVG cc", "AVGcc"],
    "refrac_avdl": ["AVDL"],
    "refrac_avgl": ["AVGL"],
    "refrac_avdp": ["AVDP"],
    "refrac_avgp": ["AVGP"],
}


def _extract_visual_acuity(record: dict) -> dict:
    result = {"od_sc": "", "od_cc": "", "og_sc": "", "og_cc": "", "date": "", "source": ""}

    df_c = _safe_df(record, "Consultation")
    if df_c is not None:
        tmp = _sort_consult_desc(df_c)
        col_avdl_sc = _find_col(tmp, _AV_CANDIDATES["avdl_sc"])
        col_avdl_cc = _find_col(tmp, _AV_CANDIDATES["avdl_cc"])
        col_avgl_sc = _find_col(tmp, _AV_CANDIDATES["avgl_sc"])
        col_avgl_cc = _find_col(tmp, _AV_CANDIDATES["avgl_cc"])

        for _, row in tmp.iterrows():
            od_sc = _val(row.get(col_avdl_sc), "") if col_avdl_sc else ""
            od_cc = _val(row.get(col_avdl_cc), "") if col_avdl_cc else ""
            og_sc = _val(row.get(col_avgl_sc), "") if col_avgl_sc else ""
            og_cc = _val(row.get(col_avgl_cc), "") if col_avgl_cc else ""
            if any(v and v != "—" for v in (od_sc, od_cc, og_sc, og_cc)):
                dt = _fmt_date(row.get("_dt") or row.get("Date"), "%d/%m/%Y")
                result.update({
                    "od_sc":  od_sc if od_sc != "—" else "",
                    "od_cc":  od_cc if od_cc != "—" else "",
                    "og_sc":  og_sc if og_sc != "—" else "",
                    "og_cc":  og_cc if og_cc != "—" else "",
                    "date":   dt if dt != "—" else "",
                    "source": "Consultation",
                })
                return result

    # Fallback: TypeRef 12 = lunettes portées from refraction text.
    rt = _extract_refraction_text(record)
    lunettes = rt.get("lunettes", {})
    av_lun = lunettes.get("av", {})
    if av_lun.get("od") or av_lun.get("og"):
        date_str = _last_consult_date(record)
        result.update({
            "od_cc": av_lun.get("od", ""),
            "og_cc": av_lun.get("og", ""),
            "date":  date_str if date_str != "—" else "",
            "source": "Lunettes portées",
        })
        return result

    df_r = _safe_df(record, "tREFRACTION")
    df_consult = _safe_df(record, "Consultation")
    if df_r is not None:
        date_map: dict[str, pd.Timestamp] = {}
        if df_consult is not None and "N° consultation" in df_consult.columns:
            for _, row in df_consult.iterrows():
                nc = _str_id(row.get("N° consultation"))
                dt = _parse_dates(pd.Series([row.get("Date")])).iloc[0]
                if nc and not _is_null_val(dt):
                    date_map[nc] = dt

        # Prefer TypeRef 12 (lunettes) rows for AVDL/AVGL.
        best_dt, best_row = None, None
        for _, row in df_r.iterrows():
            nc = _str_id(row.get("NumConsult"))
            dt = date_map.get(nc)
            if dt is not None and (best_dt is None or dt > best_dt):
                type_ref = str(row.get("TypeRef", "")).strip()
                if type_ref == "12":
                    best_dt, best_row = dt, row

        # If no TypeRef 12, fall back to any row.
        if best_row is None:
            for _, row in df_r.iterrows():
                nc = _str_id(row.get("NumConsult"))
                dt = date_map.get(nc)
                if dt is not None and (best_dt is None or dt > best_dt):
                    best_dt, best_row = dt, row

        if best_row is not None:
            col_avdl = _find_col(df_r, _AV_CANDIDATES["refrac_avdl"])
            col_avgl = _find_col(df_r, _AV_CANDIDATES["refrac_avgl"])
            avdl = _val(best_row.get(col_avdl), "") if col_avdl else ""
            avgl = _val(best_row.get(col_avgl), "") if col_avgl else ""
            if avdl != "—" or avgl != "—":
                result.update({
                    "od_cc":  avdl if avdl != "—" else "",
                    "og_cc":  avgl if avgl != "—" else "",
                    "date":   _fmt_date(best_dt) if best_dt else "",
                    "source": "Réfraction",
                })

    return result


def _extract_pio(record: dict) -> dict:
    result = {"od": "", "og": "", "date": "", "alert": False}
    df = _safe_df(record, "Consultation")
    if df is None or "TOD" not in df.columns:
        return result
    tmp = _sort_consult_desc(df)
    for _, row in tmp.iterrows():
        od = _val(row.get("TOD"), "")
        og = _val(row.get("TOG"), "") if "TOG" in tmp.columns else ""
        if (od and od != "—") or (og and og != "—"):
            dt = _fmt_date(row.get("_dt") or row.get("Date"), "%d/%m/%Y")
            result["od"]   = od if od != "—" else ""
            result["og"]   = og if og != "—" else ""
            result["date"] = dt if dt != "—" else ""
            for v_str in (od, og):
                try:
                    if float(v_str.replace(",", ".")) > 21:
                        result["alert"] = True
                except (ValueError, AttributeError):
                    pass
            return result
    return result


def _extract_pio_alert(record: dict) -> str:
    """Return a human-readable alert string if IOP exceeds 21 mmHg, else ''."""
    pio = _extract_pio(record)
    if not pio["alert"]:
        return ""
    parts = []
    if pio["od"]:
        parts.append(f"PIO OD : {pio['od']} mmHg")
    if pio["og"]:
        parts.append(f"PIO OG : {pio['og']} mmHg")
    return " · ".join(parts) + " — surveillance renforcée recommandée" if parts else ""


def _extract_pio_history(record: dict) -> pd.DataFrame:
    """Return a DataFrame[date, od, og] with all available IOP measurements, sorted ascending."""
    df = _safe_df(record, "Consultation")
    if df is None:
        return pd.DataFrame(columns=["date", "od", "og"])

    has_tod = "TOD" in df.columns
    has_tog = "TOG" in df.columns
    if not has_tod and not has_tog:
        return pd.DataFrame(columns=["date", "od", "og"])

    tmp = df.copy()
    tmp["_dt"] = _parse_dates(tmp["Date"] if "Date" in tmp.columns else pd.Series(dtype=str))

    def _to_float(series: pd.Series) -> pd.Series:
        return (
            series.astype(str)
            .str.replace(",", ".", regex=False)
            .str.strip()
            .replace({"": float("nan"), "—": float("nan"), "nan": float("nan"),
                      "None": float("nan"), "NaN": float("nan")})
            .pipe(pd.to_numeric, errors="coerce")
        )

    rows = pd.DataFrame({
        "date": tmp["_dt"],
        "od":   _to_float(tmp["TOD"]) if has_tod else float("nan"),
        "og":   _to_float(tmp["TOG"]) if has_tog else float("nan"),
    })
    rows = rows.dropna(subset=["date"])
    rows = rows[rows[["od", "og"]].notna().any(axis=1)]
    rows = rows.sort_values("date").reset_index(drop=True)
    return rows


def _extract_important(record: dict) -> tuple[str, list[dict]]:
    """Return (raw_text, items_with_dates) from the Important/Note field."""
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return ("", [])
    row = id_df.iloc[0]
    raw = _col_lookup(row, ["Important", "IMPORTANT", "important",
                             "Notes importantes", "Note importante", "Note"])
    if not raw:
        return ("", [])
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    fallback = _get_date_creation(record)
    items = _items_with_dates(text, fallback, max_items=12)
    return (text, items)


def _extract_contact_info(record: dict) -> dict:
    """Return {telephone, adresse_par} from the identity table."""
    id_df = _safe_df(record, "identity")
    result = {"telephone": "", "adresse_par": ""}
    if id_df is None:
        return result
    row = id_df.iloc[0]
    tel = _col_lookup(row, ["Téléphone", "Telephone", "TELEPHONE",
                             "Téléphone bureau", "Tel", "Mobile"])
    if tel:
        result["telephone"] = tel
    ref = _col_lookup(row, ["Adressé par :", "Adressé par:", "Adressé par",
                             "Adresse par :", "Adresse par", "Référent",
                             "Referent", "Médecin référent"])
    if ref:
        result["adresse_par"] = ref
    return result


def _extract_antecedents(record: dict) -> dict:
    """Return {antecedents: [...], allergies: [...]} from the identity table."""
    id_df = _safe_df(record, "identity")
    result = {"antecedents": [], "allergies": []}
    if id_df is None:
        return result
    row = id_df.iloc[0]
    fallback = _get_date_creation(record)
    for col in ("Antécédants", "Antecedants", "Antécédents", "ANTECEDANTS"):
        raw = _val(row.get(col), "")
        if raw and raw != "—":
            result["antecedents"] = _items_with_dates(raw, fallback, max_items=8)
            break
    raw = _val(row.get("Allergies"), "")
    if raw and raw != "—":
        result["allergies"] = _items_with_dates(raw, fallback, max_items=5)
    return result


def _extract_traitements(record: dict) -> list:
    """Return a flat list of treatment strings from the identity table (legacy)."""
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return []
    raw = _val(id_df.iloc[0].get("Traitements"), "")
    if raw and raw != "—":
        return [
            x.strip()
            for x in re.split(r"[,;\n/]", raw)
            if x.strip() and len(x.strip()) > 1
        ][:8]
    return []


# Regex to classify a treatment as local (eye drop / topical) vs systemic.
_COLLYRE_KEYWORDS = re.compile(
    r'\b(collyre|goutte|gel ophtalmique|timolol|latanoprost|dorzolamide|'
    r'brimonidine|bimatoprost|travoprost|tafluprost|brinzolamide|betaxolol|'
    r'carteolol|azetazolamide|acetazolamide|pilocarpin|tropicamide|'
    r'dexaméthasone|prednisolone|tobramycin|ciprofloxacin|ofloxacin|'
    r'chloramphénicol|fluorescéine|hypromellose|larme|lubrifiant)\\b',
    re.IGNORECASE,
)


def _classify_traitement(label: str) -> str:
    return "local" if _COLLYRE_KEYWORDS.search(label) else "systemic"


def _extract_traitements_history(record: dict) -> list[dict]:
    """Return a sorted list of {label, date, type} treatment dicts, newest first."""
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return []
    raw = _val(id_df.iloc[0].get("Traitements"), "")
    if not raw or raw == "—":
        return []
    fallback = _get_date_creation(record)
    items = _items_with_dates(raw, fallback, max_items=10)

    def _sort_key(item):
        d = item.get("date", "")
        for fmt in ("%d/%m/%Y", "%m/%Y", "%Y"):
            try:
                return pd.Timestamp(datetime.strptime(d, fmt))
            except (ValueError, TypeError):
                pass
        return pd.Timestamp.min

    items_sorted = sorted(items, key=_sort_key, reverse=True)
    for item in items_sorted:
        item["type"] = _classify_traitement(item["label"])
    return items_sorted


def _extract_prescriptions_history(record: dict) -> list[dict]:
    """Return all prescription rows from Consultation, newest first."""
    df = _safe_df(record, "Consultation")
    if df is None:
        return []
    tmp = _sort_consult_desc(df)
    result = []
    for _, row in tmp.iterrows():
        ord_v = _val(row.get("Ordonnance"), "") if "Ordonnance" in tmp.columns else ""
        aut_v = _val(row.get("AutresPrescriptions"), "") if "AutresPrescriptions" in tmp.columns else ""
        if (ord_v and ord_v != "—") or (aut_v and aut_v != "—"):
            dt = _fmt_date(row.get("_dt") or row.get("Date"), "%d/%m/%Y")
            result.append({
                "date":       dt if dt != "—" else "",
                "ordonnance": ord_v if ord_v != "—" else "",
                "autres":     aut_v if aut_v != "—" else "",
            })
    return result


def _extract_prescriptions(record: dict) -> dict:
    """Return the most recent prescription {ordonnance, autres, date}."""
    df = _safe_df(record, "Consultation")
    if df is None:
        return {"ordonnance": "", "autres": "", "date": ""}
    tmp = _sort_consult_desc(df)
    for _, row in tmp.iterrows():
        ord_v = _val(row.get("Ordonnance"), "") if "Ordonnance" in tmp.columns else ""
        aut_v = _val(row.get("AutresPrescriptions"), "") if "AutresPrescriptions" in tmp.columns else ""
        if (ord_v and ord_v != "—") or (aut_v and aut_v != "—"):
            dt = _fmt_date(row.get("_dt") or row.get("Date"), "%d/%m/%Y")
            return {
                "ordonnance": ord_v if ord_v != "—" else "",
                "autres":     aut_v if aut_v != "—" else "",
                "date":       dt if dt != "—" else "",
            }
    return {"ordonnance": "", "autres": "", "date": ""}


def _extract_diagnostic(record: dict) -> tuple[str, str]:
    """Return (diagnostic_text, date_str) from the identity table."""
    id_df = _safe_df(record, "identity")
    diag_text = ""
    if id_df is not None:
        row = id_df.iloc[0]
        for col in ("Diagnostic OPH", "Diagnostic  OPH", "DiagnosticOPH",
                    "Diagnostic Oph", "Diagnostic"):
            v = _val(row.get(col), "")
            if v and v != "—":
                diag_text = v[:250]
                break
    date_str = _last_consult_date(record)
    return (diag_text, date_str if date_str != "—" else "")


def _extract_plan_suivi(record: dict) -> str:
    """Return the most recent ProchainRDV value, or ''."""
    df = _safe_df(record, "Consultation")
    if df is None or "ProchainRDV" not in df.columns:
        return ""
    tmp = _sort_consult_desc(df)
    for _, row in tmp.iterrows():
        v = _val(row.get("ProchainRDV"), "")
        if v and v != "—":
            return v[:180]
    return ""


def _extract_motif(record: dict) -> tuple[str, str]:
    """Return (motif_text, date_str) from the most recent DOMINANTE field."""
    df = _safe_df(record, "Consultation")
    if df is None:
        return ("Bilan ophtalmologique général", "")
    tmp = _sort_consult_desc(df)
    if "DOMINANTE" in tmp.columns:
        for _, row in tmp.iterrows():
            v = _val(row.get("DOMINANTE"), "")
            if v and v != "—" and len(v) > 2:
                dt = _fmt_date(row.get("_dt") or row.get("Date"), "%d/%m/%Y")
                return (v[:150], dt if dt != "—" else "")
    return ("Bilan ophtalmologique général", "")


def _extract_identity_info(record: dict) -> dict:
    """Extract patient display name, date of birth, age, and patient ID for the survival banner."""
    result = {"full_name": "", "dob": "", "age": "", "patient_id": ""}
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return result
    row = id_df.iloc[0]

    nom    = _val(row.get("NOM"), "")
    prenom = _val(
        row.get("Prénom") or row.get("PRENOM") or row.get("Prenom"), ""
    )
    parts = []
    if nom and nom != "—":
        parts.append(nom.upper())
    if prenom and prenom != "—":
        parts.append(prenom.title())
    result["full_name"] = " ".join(parts)

    for col in ("Date de naissance", "DateNaissance", "DDN",
                "Naissance", "date_naissance", "DATE_NAISS"):
        raw = row.get(col)
        if raw is not None and not _is_null_val(raw):
            try:
                dt = pd.to_datetime(raw, dayfirst=True, errors="raise")
                result["dob"] = dt.strftime("%d/%m/%Y")
                age = (pd.Timestamp.now() - dt).days // 365
                result["age"] = str(int(age)) if 0 < age < 130 else ""
            except Exception:
                result["dob"] = _val(raw, "")
            break

    for col in ("Code patient", "CodePatient", "ID", "id", "code_patient"):
        raw = row.get(col)
        if raw is not None and not _is_null_val(raw):
            result["patient_id"] = _str_id(raw)
            break

    return result


# Column name candidates for keratometry (OD and OG).
_KERATO_OD = [
    ("k1",   ["K1OD", "K1_OD", "K1D", "Kflat_OD", "Kflat_D", "KERATOD_K1", "K1"]),
    ("k2",   ["K2OD", "K2_OD", "K2D", "Ksteep_OD", "Ksteep_D", "KERATOD_K2", "K2"]),
    ("axis", ["AxeOD", "Axe_OD", "AxD", "Ax_OD", "AXE_OD", "AxisOD", "AXEOD"]),
    ("km",   ["KmOD", "Km_OD", "KmD", "MeanK_OD", "KmD_mean"]),
]
_KERATO_OG = [
    ("k1",   ["K1OG", "K1_OG", "K1G", "Kflat_OG", "Kflat_G", "KERATOG_K1"]),
    ("k2",   ["K2OG", "K2_OG", "K2G", "Ksteep_OG", "Ksteep_G", "KERATOG_K2"]),
    ("axis", ["AxeOG", "Axe_OG", "AxG", "Ax_OG", "AXE_OG", "AxisOG", "AXEOG"]),
    ("km",   ["KmOG", "Km_OG", "KmG", "MeanK_OG"]),
]


def _extract_keratometry(record: dict) -> dict:
    """Return {od: {k1, k2, axis, km}, og: {k1, k2, axis, km}, date} from tKERATO.
    Falls back to regex parsing of REFRACTION text if structured columns are absent."""
    result: dict = {"od": {}, "og": {}, "date": ""}
    df = _safe_df(record, "tKERATO")

    if df is not None:
        best_row = _most_recent_row(df, record)
        if best_row is not None:
            df_consult = _safe_df(record, "Consultation")
            date_map   = _build_consult_date_map(df_consult)
            best_dt    = None
            for _, row in df.iterrows():
                nc = _str_id(row.get("NumConsult"))
                dt = date_map.get(nc)
                if dt is not None and (best_dt is None or dt > best_dt):
                    best_dt = dt
            if best_dt:
                result["date"] = _fmt_date(best_dt)

            def _read_eye(candidates: list) -> dict:
                eye: dict = {}
                for key, cols in candidates:
                    col = _find_col(df, cols)
                    if col is None:
                        continue
                    v = _val(best_row.get(col), "")
                    if not v or v == "—":
                        continue
                    try:
                        f = float(str(v).replace(",", "."))
                        # Convert radius (mm) to diopters if value is in mm range.
                        if key in ("k1", "k2", "km") and f < 20:
                            f = 337.5 / f
                        eye[key] = f"{f:.2f}" if key != "axis" else f"{f:.0f}"
                    except (ValueError, TypeError):
                        eye[key] = v
                return eye

            result["od"] = _read_eye(_KERATO_OD)
            result["og"] = _read_eye(_KERATO_OG)

            if result["od"] or result["og"]:
                return result

    # Fallback: parse REFRACTION free text.
    rt = _extract_refraction_text(record)
    km_od = rt.get("kerato", {}).get("od", {}).get("km", "")
    km_og = rt.get("kerato", {}).get("og", {}).get("km", "")
    k1_od = rt.get("kerato", {}).get("od", {}).get("k1", "")
    k2_od = rt.get("kerato", {}).get("od", {}).get("k2", "")
    k1_og = rt.get("kerato", {}).get("og", {}).get("k1", "")
    k2_og = rt.get("kerato", {}).get("og", {}).get("k2", "")
    if km_od or k1_od:
        result["od"] = {k: v for k, v in {"k1": k1_od, "k2": k2_od, "km": km_od}.items() if v}
    if km_og or k1_og:
        result["og"] = {k: v for k, v in {"k1": k1_og, "k2": k2_og, "km": km_og}.items() if v}
    if not result["date"]:
        result["date"] = _last_consult_date(record) or ""

    return result


# Column name candidates for refraction (OD and OG).
_REFRAC_OD = {
    "sph":  ["SphOD", "Sph_OD", "SphD", "SPH_OD", "SPHOD", "Sphere_OD"],
    "cyl":  ["CylOD", "Cyl_OD", "CylD", "CYL_OD", "CYLOD", "Cylindre_OD"],
    "axis": ["AxeOD", "Axe_OD", "AxD",  "AXE_OD", "AXEOD", "Axe_refrac_OD"],
    "add":  ["AddOD", "Add_OD", "AddD",  "ADD_OD", "Addition_OD"],
}
_REFRAC_OG = {
    "sph":  ["SphOG", "Sph_OG", "SphG", "SPH_OG", "SPHOG", "Sphere_OG"],
    "cyl":  ["CylOG", "Cyl_OG", "CylG", "CYL_OG", "CYLOG", "Cylindre_OG"],
    "axis": ["AxeOG", "Axe_OG", "AxG",  "AXE_OG", "AXEOG", "Axe_refrac_OG"],
    "add":  ["AddOG", "Add_OG", "AddG",  "ADD_OG", "Addition_OG"],
}


def _extract_refraction_detail(record: dict) -> dict:
    """Return {od: {sph, cyl, axis, add}, og: {sph, cyl, axis, add}, date} from tREFRACTION.
    Priority: TypeRef 12 (lunettes portées) > TypeRef 6 (autoréfractomètre) > any row.
    Falls back to _extract_refraction_text if structured columns are absent."""
    result: dict = {"od": {}, "og": {}, "date": ""}
    df = _safe_df(record, "tREFRACTION")

    if df is not None:
        df_consult = _safe_df(record, "Consultation")
        date_map   = _build_consult_date_map(df_consult)

        best_dt, best_row = None, None
        for target_type in ("12", "6", None):
            for _, row in df.iterrows():
                nc = _str_id(row.get("NumConsult"))
                dt = date_map.get(nc)
                if dt is None:
                    continue
                type_ref = str(row.get("TypeRef", "")).strip()
                if target_type is not None and type_ref != target_type:
                    continue
                if best_dt is None or dt > best_dt:
                    best_dt, best_row = dt, row
            if best_row is not None:
                break

        if best_row is None and not df.empty:
            best_row = df.iloc[0]

        if best_row is not None:
            if best_dt:
                result["date"] = _fmt_date(best_dt)

            def _read_eye(candidates: dict) -> dict:
                eye: dict = {}
                for key, cols in candidates.items():
                    col = _find_col(df, cols)
                    if col is None:
                        continue
                    v = _val(best_row.get(col), "")
                    if not v or v == "—":
                        continue
                    try:
                        f = float(str(v).replace(",", "."))
                        if key == "axis":
                            eye[key] = f"{f:.0f}°"
                        else:
                            eye[key] = f"{f:+.2f}"
                    except (ValueError, TypeError):
                        eye[key] = v
                return eye

            result["od"] = _read_eye(_REFRAC_OD)
            result["og"] = _read_eye(_REFRAC_OG)

            if result["od"] or result["og"]:
                return result

    # Fallback: parse REFRACTION free text — priority: subjective > lunettes > autoref.
    rt = _extract_refraction_text(record)
    for source_key in ("subjective", "lunettes", "autoref"):
        src = rt.get(source_key, {})
        od  = src.get("od", {})
        og  = src.get("og", {})
        if od or og:
            def _fmt_eye(eye_dict: dict) -> dict:
                out = {}
                for k, v in eye_dict.items():
                    if k in ("av",):
                        continue
                    try:
                        f = float(str(v).replace(",", "."))
                        if k == "axis":
                            out[k] = f"{f:.0f}°"
                        else:
                            out[k] = f"{f:+.2f}"
                    except (ValueError, TypeError):
                        out[k] = str(v)
                return out
            result["od"] = _fmt_eye(od)
            result["og"] = _fmt_eye(og)
            if not result["date"]:
                result["date"] = _last_consult_date(record) or ""
            return result

    return result


def _extract_refraction_text(record: dict) -> dict:
    """Parse the free-text REFRACTION field from the most recent Consultation row.

    Returns a structured dict:
    {
        "kerato": {
            "od": {"k1": str, "k2": str, "km": str, "ax1": str, "ax2": str,
                   "diop1": str, "diop2": str, "diop_mean": str, "cyl_corneen": str},
            "og": { ... same ... }
        },
        "pachy": {
            "od": int|None, "og": int|None,
            "to_brute": {"od": int|None, "og": int|None}
        },
        "autoref":   {"od": {sph, cyl, axis}, "og": { ... }},
        "lunettes":  {"od": {sph, cyl, axis, add}, "og": { ... }, "av": {od, og}},
        "subjective":{"od": {sph, cyl, axis, add}, "og": { ... }, "av": {od, og}}
    }
    Any sub-dict is {} / None when the corresponding block is absent from the text.
    """
    empty: dict = {
        "kerato":    {"od": {}, "og": {}},
        "pachy":     {"od": None, "og": None, "to_brute": {"od": None, "og": None}},
        "autoref":   {"od": {}, "og": {}},
        "lunettes":  {"od": {}, "og": {}, "av": {"od": "", "og": ""}},
        "subjective":{"od": {}, "og": {}, "av": {"od": "", "og": ""}},
    }

    df = _safe_df(record, "Consultation")
    if df is None:
        return empty

    # Get REFRACTION text from the most recent consultation.
    tmp = _sort_consult_desc(df)
    raw_text = ""
    for _, row in tmp.iterrows():
        v = _val(row.get("REFRACTION"), "")
        if v and v != "—":
            raw_text = v
            break
    if not raw_text:
        return empty

    result = {
        "kerato":    {"od": {}, "og": {}},
        "pachy":     {"od": None, "og": None, "to_brute": {"od": None, "og": None}},
        "autoref":   {"od": {}, "og": {}},
        "lunettes":  {"od": {}, "og": {}, "av": {"od": "", "og": ""}},
        "subjective":{"od": {}, "og": {}, "av": {"od": "", "og": ""}},
    }

    def _num(s: str) -> str:
        """Normalise a numeric string: replace comma with dot."""
        return s.replace(",", ".").strip() if s else ""

    def _signed(s: str) -> str:
        """Return a signed float string like '+4.00' or '-0.50'."""
        s = _num(s)
        try:
            f = float(s)
            return f"{f:+.2f}"
        except (ValueError, TypeError):
            return s

    # Keratometry block patterns (radius mm → diopters via 337.5/r).
    _RE_KER_OD = re.compile(
        r'ROD=\s*([\d,\.]+)/([\d,\.]+).*?Km=\s*([\d,\.]+).*?AXES\s+OD=\s*([\d]+)[°]?/([\d]+)',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_KER_OG = re.compile(
        r'ROG=\s*([\d,\.]+)/([\d,\.]+).*?Km=\s*([\d,\.]+).*?AXES\s+OG=\s*([\d]+)[°]?/([\d]+)',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_DIOP_OD = re.compile(
        r'Dioptrie\s+OD=\s*([\d,\.]+)/([\d,\.]+)\s+Moyenne\s*=\s*([\d,\.]+)',
        re.IGNORECASE,
    )
    _RE_DIOP_OG = re.compile(
        r'Dioptrie\s+OG=\s*([\d,\.]+)/([\d,\.]+)\s+Moyenne\s*=\s*([\d,\.]+)',
        re.IGNORECASE,
    )
    _RE_CYL_D = re.compile(
        r'Cylindre\s+corn[ée]+en\s+D=\s*([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?',
        re.IGNORECASE,
    )
    _RE_CYL_G = re.compile(
        r'Cylindre\s+corn[ée]+en\s+G=\s*([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?',
        re.IGNORECASE,
    )
    _RE_KM_OD = re.compile(r'(?:ROD.*?)Km=\s*([\d,\.]+)', re.IGNORECASE | re.DOTALL)
    _RE_KM_OG = re.compile(r'(?:ROG.*?)Km=\s*([\d,\.]+)', re.IGNORECASE | re.DOTALL)

    m = _RE_KER_OD.search(raw_text)
    if m:
        r1, r2, km, ax1, ax2 = m.groups()
        try:
            k1 = f"{337.5 / float(_num(r1)):.2f}"
            k2 = f"{337.5 / float(_num(r2)):.2f}"
            km_d = f"{337.5 / float(_num(km)):.2f}"
        except (ValueError, ZeroDivisionError):
            k1 = k2 = km_d = ""
        result["kerato"]["od"] = {
            "k1": k1, "k2": k2, "km": km_d, "ax1": ax1, "ax2": ax2,
        }
        m2 = _RE_DIOP_OD.search(raw_text)
        if m2:
            result["kerato"]["od"].update({
                "diop1": _num(m2.group(1)), "diop2": _num(m2.group(2)),
                "diop_mean": _num(m2.group(3)),
            })
        m3 = _RE_CYL_D.search(raw_text)
        if m3:
            result["kerato"]["od"]["cyl_corneen"] = f"{_num(m3.group(1))} à {m3.group(2)}°"
    else:
        m_km = _RE_KM_OD.search(raw_text)
        if m_km:
            try:
                km_d = f"{337.5 / float(_num(m_km.group(1))):.2f}"
                result["kerato"]["od"]["km"] = km_d
            except (ValueError, ZeroDivisionError):
                pass

    m = _RE_KER_OG.search(raw_text)
    if m:
        r1, r2, km, ax1, ax2 = m.groups()
        try:
            k1 = f"{337.5 / float(_num(r1)):.2f}"
            k2 = f"{337.5 / float(_num(r2)):.2f}"
            km_g = f"{337.5 / float(_num(km)):.2f}"
        except (ValueError, ZeroDivisionError):
            k1 = k2 = km_g = ""
        result["kerato"]["og"] = {
            "k1": k1, "k2": k2, "km": km_g, "ax1": ax1, "ax2": ax2,
        }
        m2 = _RE_DIOP_OG.search(raw_text)
        if m2:
            result["kerato"]["og"].update({
                "diop1": _num(m2.group(1)), "diop2": _num(m2.group(2)),
                "diop_mean": _num(m2.group(3)),
            })
        m3 = _RE_CYL_G.search(raw_text)
        if m3:
            result["kerato"]["og"]["cyl_corneen"] = f"{_num(m3.group(1))} à {m3.group(2)}°"
    else:
        m_km = _RE_KM_OG.search(raw_text)
        if m_km:
            try:
                km_g = f"{337.5 / float(_num(m_km.group(1))):.2f}"
                result["kerato"]["og"]["km"] = km_g
            except (ValueError, ZeroDivisionError):
                pass

    # Pachymetry block: "OD = 544 µm (TO Brute = 15)".
    _RE_PACHY_OD = re.compile(
        r'Pachym[ée]trie.*?OD\s*=\s*(\d+)\s*[µu]m(?:\s*\(TO\s*Brute\s*=\s*(\d+)\))?',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_PACHY_OG = re.compile(
        r'Pachym[ée]trie.*?OG\s*=\s*(\d+)\s*[µu]m(?:\s*\(TO\s*Brute\s*=\s*(\d+)\))?',
        re.IGNORECASE | re.DOTALL,
    )

    m = _RE_PACHY_OD.search(raw_text)
    if m:
        result["pachy"]["od"] = int(m.group(1))
        if m.group(2):
            result["pachy"]["to_brute"]["od"] = int(m.group(2))

    m = _RE_PACHY_OG.search(raw_text)
    if m:
        result["pachy"]["og"] = int(m.group(1))
        if m.group(2):
            result["pachy"]["to_brute"]["og"] = int(m.group(2))

    # Autorefractometer block: "OD : +4,25 (-0,50 à 35°)".
    _RE_AUTOREF_OD = re.compile(
        r'Autor[ée]fractom[eè]tre.*?OD\s*:\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_AUTOREF_OG = re.compile(
        r'Autor[ée]fractom[eè]tre.*?OG\s*:\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)',
        re.IGNORECASE | re.DOTALL,
    )

    m = _RE_AUTOREF_OD.search(raw_text)
    if m:
        result["autoref"]["od"] = {"sph": _signed(m.group(1)), "cyl": _signed(m.group(2)), "axis": m.group(3) + "°"}

    m = _RE_AUTOREF_OG.search(raw_text)
    if m:
        result["autoref"]["og"] = {"sph": _signed(m.group(1)), "cyl": _signed(m.group(2)), "axis": m.group(3) + "°"}

    # Lunettes portées block: "OD= +4,00 (-0,50 à 50°)= 10 /10; Add 2,00".
    _RE_LUN_OD = re.compile(
        r'Lunettes\s+port[ée]es.*?OD=\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)'
        r'(?:=\s*([\d]+)\s*/\s*10)?'
        r'(?:.*?Add\s*([\d,\.]+))?',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_LUN_OG = re.compile(
        r'Lunettes\s+port[ée]es.*?OG=\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)'
        r'(?:=\s*([\d]+)\s*/\s*10)?'
        r'(?:.*?Add\s*([\d,\.]+))?',
        re.IGNORECASE | re.DOTALL,
    )

    m = _RE_LUN_OD.search(raw_text)
    if m:
        sph, cyl, axis, av_num, add = m.groups()
        result["lunettes"]["od"] = {"sph": _signed(sph), "cyl": _signed(cyl), "axis": axis + "°"}
        if add:
            result["lunettes"]["od"]["add"] = _signed(add)
        if av_num:
            result["lunettes"]["av"]["od"] = f"{av_num}/10"

    m = _RE_LUN_OG.search(raw_text)
    if m:
        sph, cyl, axis, av_num, add = m.groups()
        result["lunettes"]["og"] = {"sph": _signed(sph), "cyl": _signed(cyl), "axis": axis + "°"}
        if add:
            result["lunettes"]["og"]["add"] = _signed(add)
        if av_num:
            result["lunettes"]["av"]["og"] = f"{av_num}/10"

    # Subjective refraction block: "OD= +4,00 (-0,50 à 50°)= 10 /10; Add 2,00".
    _RE_SUBJ_OD = re.compile(
        r'R[ée]fraction\s+subjective.*?OD=\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)'
        r'(?:=\s*([\d]+)\s*/\s*10)?'
        r'(?:.*?Add\s*([\d,\.]+))?',
        re.IGNORECASE | re.DOTALL,
    )
    _RE_SUBJ_OG = re.compile(
        r'R[ée]fraction\s+subjective.*?OG=\s*([+-]?[\d,\.]+)\s*\(([+-]?[\d,\.]+)\s*[àa]\s*([\d]+)[°]?\)'
        r'(?:=\s*([\d]+)\s*/\s*10)?'
        r'(?:.*?Add\s*([\d,\.]+))?',
        re.IGNORECASE | re.DOTALL,
    )

    m = _RE_SUBJ_OD.search(raw_text)
    if m:
        sph, cyl, axis, av_num, add = m.groups()
        result["subjective"]["od"] = {"sph": _signed(sph), "cyl": _signed(cyl), "axis": axis + "°"}
        if add:
            result["subjective"]["od"]["add"] = _signed(add)
        if av_num:
            result["subjective"]["av"]["od"] = f"{av_num}/10"

    m = _RE_SUBJ_OG.search(raw_text)
    if m:
        sph, cyl, axis, av_num, add = m.groups()
        result["subjective"]["og"] = {"sph": _signed(sph), "cyl": _signed(cyl), "axis": axis + "°"}
        if add:
            result["subjective"]["og"]["add"] = _signed(add)
        if av_num:
            result["subjective"]["av"]["og"] = f"{av_num}/10"

    return result


def _build_consult_date_map(df_consult) -> dict:
    """Build {consult_id_str -> pd.Timestamp} from the Consultation DataFrame."""
    date_map: dict[str, pd.Timestamp] = {}
    if df_consult is None or "N° consultation" not in df_consult.columns:
        return date_map
    for _, row in df_consult.iterrows():
        nc = _str_id(row.get("N° consultation"))
        dt = _parse_dates(pd.Series([row.get("Date")])).iloc[0]
        if nc and not _is_null_val(dt):
            date_map[nc] = dt
    return date_map


def _most_recent_row(df: pd.DataFrame, record: dict):
    """Return the row of df whose NumConsult maps to the most recent consultation date."""
    df_consult = _safe_df(record, "Consultation")
    date_map   = _build_consult_date_map(df_consult)
    best_dt, best_row = None, None
    for _, row in df.iterrows():
        nc = _str_id(row.get("NumConsult"))
        dt = date_map.get(nc)
        if dt is not None and (best_dt is None or dt > best_dt):
            best_dt, best_row = dt, row
    if best_row is None and not df.empty:
        best_row = df.iloc[0]
    return best_row