# DMP-Extractor — Ophthalmology Patient Records

Internal Streamlit application that consolidates ophthalmology patient records from JSON source files into a single searchable dashboard, with per-consultation PDF export.

---

## Features

- **Patient search** — accent-insensitive, case-insensitive, word-order-independent
- **Consultation dashboard** — chronological act table with exam chips (keratometry, refraction, imaging, procedures) and doctor name resolution
- **Per-day PDF export** — each row in the act table generates a PDF scoped to that date only (consultation + linked keratometry, refraction, documents)
- **360° patient profile** — visual acuity, IOP, history, allergies, treatments, diagnosis, follow-up plan in a single card
- **IOP chart** — temporal Plotly chart with min/max annotations (OD / OG)
- **Light theme** — forced via `.streamlit/config.toml`; consistent rendering regardless of OS theme
- **Zero-config data loading** — any `.json` file dropped into `data_raw/` is picked up automatically on next launch

---

## Project Structure

```
DMP-EXTRACTOR/
├── .streamlit/
│   └── config.toml             # Light theme + brand colors
├── data_raw/                   # JSON source files
│   ├── Patients.json           # Patient identity (required)
│   ├── Consultation.json       # Consultation history (required)
│   ├── tKERATO.json
│   ├── tREFRACTION.json
│   ├── Documents.json
│   ├── Ag_Rdv.json
│   ├── tPostIT.json
│   └── person.json             # Doctor name lookup (optional)
├── src/
│   ├── extraction.py           # Data loading, cleaning, ID normalization, record assembly
│   └── interface/
│       ├── app.py              # Streamlit entry point, PDF generation
│       ├── medical_summary.py  # Orchestrator — public API (render, analyse, export)
│       ├── _extractors.py      # Clinical data extractors (AV, IOP, treatments, Rx…)
│       ├── _actes.py           # Act table: data builder + Streamlit renderer
│       ├── _card.py            # CSS, HTML helpers, 360° patient card
│       ├── _pio_chart.py       # IOP Plotly chart + Streamlit renderer
│       └── _utils.py           # Shared utilities (date parsing, DataFrame helpers…)
├── requirements.txt
└── README.md
```

---

## Requirements

Python 3.10+

```
pandas
streamlit
plotly
fpdf2       # optional — required for PDF export
numpy
```

> `fpdf2 >= 2.7` is recommended — ships with bundled DejaVu fonts for full Unicode support. If not installed, PDF buttons are disabled but all other features remain functional.

---

## Installation

```bash
git clone https://github.com/Vic-Warden/dmp-extractor.git
cd DMP-EXTRACTOR
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Data Setup

Place JSON exports from your ophthalmology software into `data_raw/`.

| File | Join column | Purpose |
|---|:---:|---|
| `Patients.json` | `Code patient` | Identity, name, DOB |
| `Consultation.json` | `Code patient` | Consultation history |
| `tKERATO.json` | `NumConsult` | Keratometry |
| `tREFRACTION.json` | `NumConsult` | Refraction |
| `Documents.json` | `code patient` | Documents |
| `Ag_Rdv.json` | `Code Patient` | Appointments |
| `tPostIT.json` | `CodePat` | Sticky notes |
| `person.json` | `ID` → `Nom+Prénom` | Doctor names |

Column names are case-sensitive and must match the table above exactly.

---

## Usage

```bash
streamlit run src/interface/app.py
```

Opens at `http://localhost:8501`.

1. Type a patient name (partial, accented, or any word order) in the sidebar.
2. The dashboard loads: act table → 360° profile card → IOP chart.
3. Click **"Consulter cette journée"** on any act row to download a PDF for that date.

---

## Notes

- **Read-only** — no source file is ever modified.
- **Data caching** — files load once at startup (`@st.cache_resource`). Restart the app to pick up changes in `data_raw/`.
- **Internal use only** — no data is sent externally.