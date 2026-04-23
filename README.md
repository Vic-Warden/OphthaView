# DMP-Extractor — Ophthalmology Patient Records

An internal Streamlit application that consolidates ophthalmology patient records from scattered JSON source files into a single searchable interface, with one-click PDF export of full dossiers or individual consultations.

---

## Features

- **Flexible patient search** — accent-insensitive, case-insensitive, word-order-independent (e.g. `dupont jean` = `Jean Dupont` = `ÉLODIE dupont`)
- **Unified record view** — consultations, keratometry (`tKERATO`), refraction (`tREFRACTION`), appointments (`Ag_Rdv`), sticky notes (`tPostIT`), and linked documents in one place
- **OD / OG split layout** — bilateral exam values displayed side by side with blue (OD) / green (OG) color coding, auto-detected from column name suffixes
- **Chronological sorting** — all sections sorted newest-first automatically; technical exams sorted via their linked consultation date
- **PDF export (full dossier)** — one-click export of the entire patient record; empty fields are silently omitted
- **PDF export (per consultation)** — individual PDF per consultation entry, including linked keratometry, refraction and documents for that session
- **Doctor name resolution** — doctor codes are resolved to human-readable names via `person.json` when available
- **Zero-config data loading** — any new `.json` file dropped into `data_raw/` is picked up automatically on the next launch
- **Graceful PDF fallback** — if `fpdf2` is not installed, PDF buttons are hidden; all other features remain fully functional

---

## Project Structure

```
DMP-EXTRACTOR/
├── data_raw/                   # ← Place all JSON source files here
│   ├── Patients.json           # Patient identity (required)
│   ├── Consultation.json       # Consultation history (required)
│   ├── tKERATO.json            # Keratometry exams
│   ├── tREFRACTION.json        # Refraction exams
│   ├── Documents.json          # Patient documents
│   ├── Ag_Rdv.json             # Appointments
│   ├── tPostIT.json            # Sticky notes
│   └── person.json             # Doctor name lookup (optional)
├── notebooks_executed/
│   └── notebooks_executed.ipynb
├── src/
│   └── interface/
│       └── app.py              # Streamlit UI, rendering, PDF generation
│   └── extraction.py           # Data loading, cleaning, ID normalization, record assembly
├── .gitignore
├── Rapport_Medical.pdf         # Functional report (FR) — for medical staff
├── Rapport_Technique.pdf       # Technical report (FR) — for developers
├── README.md
└── requirements.txt
```

---

## Requirements

- **Python 3.10+**
- Dependencies listed in `requirements.txt`:

```
pandas
streamlit
fpdf2       # optional — required for PDF export only
numpy       # pulled in automatically by pandas
```

> `fpdf2 >= 2.7` is recommended — it ships with bundled DejaVu fonts for full Unicode/accent support in generated PDFs. No external font installation is needed.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Vic-Warden/dmp-extractor.git

cd DMP-EXTRACTOR

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux

venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Add fpdf2 for PDF export
pip install fpdf2
```

---

## Data Setup

Place all JSON export files from your ophthalmology management software into the `data_raw/` folder.

| File | Key join column | Purpose |
|---|:---:|---|
| `Patients.json` | `Code patient` | Patient identity, name, DOB |
| `Consultation.json` | `Code patient` | Full consultation history |
| `tKERATO.json` | `NumConsult` | Keratometry measurements |
| `tREFRACTION.json` | `NumConsult` | Refraction measurements |
| `Documents.json` | `code patient` | Patient documents |
| `Ag_Rdv.json` | `Code Patient` | Appointment history |
| `tPostIT.json` | `CodePat` | Internal sticky notes |
| `person.json` | `ID` → `Nom+Prénom` | Doctor name lookup |

> **Note:** Column names in JSON files are case-sensitive and must match the values in the table above exactly for joins to work correctly.

---

## Usage

Run the app from the project root:

```bash
streamlit run src/interface/app.py
```

The app opens automatically in your browser at `http://localhost:8501`.

**Workflow:**
1. Type a patient name (or partial name) in the **left sidebar** search box.
2. The app resolves and displays the full consolidated record instantly.
3. Browse the three tabs: **Consultations**, **Examens techniques**, **Documents**.
4. Click **"Générer le dossier complet (PDF)"** for a full record export.
5. Inside any consultation entry, click **"Télécharger cette consultation (PDF)"** for a targeted single-consultation export.

**Search examples** (all return the same patient):

| Input |
|---|
| `dupont` |
| `jean` |
| `dupont jean` |
| `jean dupont` |
| `DUPONT` | 
| `élodie` or `elodie` |

---

## Important Notes

- **Read-only** — the app never writes back to or modifies any source file.
- **Data caching** — JSON files are loaded once at startup via `@st.cache_resource`. Restart the app to pick up any changes to `data_raw/`.
- **Missing fields** — any field absent from the source data is silently omitted from both the UI and PDF exports; no placeholder values are invented.
- **Internal use only** — the app is designed to run on a local or internal network. No data is sent externally.
- **PDF font handling** — the app attempts to load DejaVu fonts bundled with `fpdf2`. If unavailable, it falls back to Helvetica automatically; the PDF is always generated regardless.