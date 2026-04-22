import pandas as pd
import numpy as np
from pathlib import Path


def load_all_data(data_folder: str = "data_raw") -> dict:
    """
    Load every JSON file in the given folder into a dict of DataFrames.
    Keys are file stems (e.g. 'Patients', 'Consultation', 'tKERATO', …).
    """
    base_path = Path(data_folder)
    dfs = {}
    for file_path in base_path.glob("*.json"):
        dfs[file_path.stem] = pd.read_json(file_path)
    print(f"[LOAD] {len(dfs)} file(s) loaded: {sorted(dfs.keys())}")
    return dfs


def normalize_id(value) -> str | None:
    """
    Convert any ID value to a plain string for safe cross-file comparison.

    Handles all common storage formats:
      - float  : 1007368913.0  →  '1007368913'
      - int    : 1007368913    →  '1007368913'
      - string : '1007368913'  →  '1007368913'
      - None / NaN             →  None
    """
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    try:
        # int(float(...)) cleanly strips any trailing .0
        return str(int(float(str(value).strip())))
    except (ValueError, OverflowError):
        s = str(value).strip()
        return s if s else None


def clean_df(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Drop fully-empty columns and normalise null-like strings.

    KEY FIX: regex replacement is applied ONLY to object (string) columns.
    Applying it to numeric columns raises a TypeError in pandas >= 2.0 and
    silently corrupts results in older versions.
    """
    if df is None or df.empty:
        return None

    # Replace null-like strings only on text columns
    str_cols = df.select_dtypes(include="object").columns
    if len(str_cols) > 0:
        df = df.copy()
        df[str_cols] = df[str_cols].replace(
            [r"^\s*$", "NaN", "nan", "null", "None", ""],
            np.nan,
            regex=True,
        )

    # Remove columns that are entirely NaN (no useful data)
    df = df.dropna(axis=1, how="all")
    return df if not df.empty else None


def get_full_patient_record(dfs: dict, patient_name: str) -> dict | None:
    """
    Build the complete medical file for a patient by following all ID links
    across the loaded JSON files.

    Lookup strategy
    ───────────────
    Level 1 – direct link via patient ID:
        Ag_Rdv       →  'Code Patient'
        Consultation →  'Code patient'
        Documents    →  'code patient'   ← note: all lowercase
        tPostIT      →  'CodePat'

    Level 2 – indirect link via consultation IDs (found at level 1):
        tKERATO      →  'NumConsult'
        tREFRACTION  →  'NumConsult'

    Returns a dict of { section_name: DataFrame } or None if not found.
    """

    # ── 1. Locate the patient in Patients.json ────────────────────────────
    df_patients = dfs.get("Patients")
    if df_patients is None:
        print("[ERROR] 'Patients' not found in loaded data.")
        return None

    match = df_patients[
        df_patients["NOM"].str.contains(patient_name, case=False, na=False)
    ].copy()

    if match.empty:
        print(f"[NOT FOUND] No patient matching '{patient_name}'.")
        return None

    patient_id = normalize_id(match.iloc[0]["Code patient"])
    print(f"[OK] Patient found — Code patient: {patient_id}")

    record = {"identity": clean_df(match)}

    # ── 2. Build doctor ID → full name lookup from person.json ────────────
    doctor_map = {}
    if "person" in dfs:
        doctor_map = dfs["person"].set_index("ID")["Nom+Prénom"].to_dict()

    # ── 3. Direct lookups by patient ID ──────────────────────────────────
    # Each entry: section_key → exact column name in that JSON file
    # Column names must match the raw JSON exactly (case-sensitive).
    direct_links = {
        "Ag_Rdv":       "Code Patient",   # capital C + P
        "Consultation": "Code patient",   # capital C, lowercase p
        "Documents":    "code patient",   # all lowercase  ← was a common bug source
        "tPostIT":      "CodePat",        # camelCase — no Viale data expected here
    }

    for section, id_col in direct_links.items():
        df = dfs.get(section)
        if df is None:
            print(f"[SKIP] '{section}' not found in loaded files.")
            continue

        if id_col not in df.columns:
            print(f"[SKIP] Column '{id_col}' not found in '{section}' "
                  f"(available: {list(df.columns[:5])} …).")
            continue

        # Filter rows that belong to this patient
        mask = df[id_col].apply(normalize_id) == patient_id
        filtered = df[mask].copy()

        if filtered.empty:
            print(f"[EMPTY] '{section}': no rows for patient ID {patient_id}.")
            continue

        # Enrich with doctor name wherever a doctor-code column is present
        for doc_col in ("Code Docteur", "Code Médecin"):
            if doc_col in filtered.columns:
                filtered["Doctor_Name"] = filtered[doc_col].map(doctor_map)
                break

        cleaned = clean_df(filtered)
        if cleaned is not None:
            record[section] = cleaned
            print(f"[OK] '{section}': {len(cleaned)} row(s) recovered.")
        else:
            print(f"[EMPTY] '{section}': data was all-NaN after cleaning.")

    # ── 4. Indirect lookups via consultation IDs ──────────────────────────
    # tKERATO and tREFRACTION are not linked directly to the patient;
    # they reference the consultation via NumConsult.
    if "Consultation" not in record:
        print("[WARN] No 'Consultation' section — cannot resolve tKERATO / tREFRACTION.")
        return record

    consult_ids = (
        record["Consultation"]["N° consultation"]
        .apply(normalize_id)
        .dropna()
        .tolist()
    )
    print(f"[INFO] {len(consult_ids)} consultation ID(s) to resolve for tKERATO / tREFRACTION.")

    indirect_links = {
        "tKERATO":     "NumConsult",
        "tREFRACTION": "NumConsult",
    }

    for section, id_col in indirect_links.items():
        df = dfs.get(section)
        if df is None:
            print(f"[SKIP] '{section}' not found in loaded files.")
            continue

        mask = df[id_col].apply(normalize_id).isin(consult_ids)
        filtered = df[mask].copy()

        cleaned = clean_df(filtered)
        if cleaned is not None:
            record[section] = cleaned
            print(f"[OK] '{section}': {len(cleaned)} row(s) recovered.")
        else:
            print(f"[EMPTY] '{section}': no matching rows for this patient's consultations.")

    return record