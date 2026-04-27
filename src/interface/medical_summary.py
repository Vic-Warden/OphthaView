# Cockpit Dashboard orchestrator.
# Public API:
#   render_medical_summary(record)   — Streamlit render
#   analyse_patient(record)          — dict of all structured clinical data
#   generate_medical_summary(record) — str (Markdown, used for PDF/LLM)
#   analyse_parcours_soin(record)    — backwards-compatible alias

from datetime import datetime
import streamlit as st

from _utils import _last_consult_date, _n_consult
from _extractors import (
    _extract_visual_acuity, _extract_pio, _extract_pio_alert,
    _extract_motif, _extract_diagnostic, _extract_important,
    _extract_antecedents, _extract_traitements, _extract_traitements_history,
    _extract_prescriptions, _extract_prescriptions_history,
    _extract_plan_suivi, _extract_contact_info,
    _extract_identity_info, _extract_keratometry, _extract_refraction_detail,
    _extract_refraction_text,
    _get_date_creation,
)
from _actes import _build_actes_rows
from _card import (
    _CSS,
    _survival_banner_html,
    _visual_function_card_html,
    _biomechanics_card_html,
    _terrain_card_html,
)
from _pio_chart import _render_pio_chart


def analyse_patient(record: dict) -> dict:
    """Extract and return all structured clinical data for the dashboard."""
    if not record:
        return {}

    ant                    = _extract_antecedents(record)
    motif_text, motif_date = _extract_motif(record)
    diag_text, diag_date   = _extract_diagnostic(record)
    imp_text, _imp_items   = _extract_important(record)

    return {
        # v14 additions
        "identity_info":     _extract_identity_info(record),
        "refraction_text":   _extract_refraction_text(record),
        "refraction_detail": _extract_refraction_detail(record),
        "keratometry":       _extract_keratometry(record),

        # v13
        "visual_acuity":     _extract_visual_acuity(record),
        "pio":               _extract_pio(record),

        # Core (v12)
        "motif":                 motif_text,
        "motif_date":            motif_date,
        "diagnostic":            diag_text,
        "diagnostic_date":       diag_date,
        "antecedents_allergies": ant,
        "traitements":           _extract_traitements(record),
        "prescriptions":         _extract_prescriptions(record),

        # Historised (v12)
        "traitements_history":   _extract_traitements_history(record),
        "prescriptions_history": _extract_prescriptions_history(record),

        # Unchanged
        "plan_suivi":            _extract_plan_suivi(record),
        "pio_alert":             _extract_pio_alert(record),
        "last_consult_date":     _last_consult_date(record),
        "n_consult":             _n_consult(record),
        "important":             imp_text,
        "important_items":       _imp_items,
        "date_creation":         _get_date_creation(record),
        "contact":               _extract_contact_info(record),

        # Legacy
        "antecedents_perso": [
            i["label"] if isinstance(i, dict) else i
            for i in ant["antecedents"]
        ],
        "antecedents_fam": [],
    }


def analyse_parcours_soin(record: dict) -> dict:
    """Backwards-compatible alias for analyse_patient."""
    return analyse_patient(record)


def generate_medical_summary(record: dict) -> str:
    """Return a structured Markdown string — used for PDF export and LLM input."""
    if not record:
        return "_Aucune donnée disponible._"

    d     = analyse_patient(record)
    ant   = d["antecedents_allergies"]
    presc = d["prescriptions"]
    imp   = d.get("important", "")
    cont  = d.get("contact", {})
    dc    = d.get("date_creation", "")
    trt_h = d.get("traitements_history", [])
    prs_h = d.get("prescriptions_history", [])
    av    = d.get("visual_acuity", {})
    pio   = d.get("pio", {})

    lines = [
        "## Synthèse de Suivi Ophtalmologique\n",
        f"**Dernière consultation :** {d['last_consult_date']}  ",
        f"**Nombre de consultations :** {d['n_consult']}\n",
    ]

    if dc:
        lines.append(f"**Dossier ouvert le :** {dc}  ")
    if cont.get("telephone"):
        lines.append(f"**Tél. :** {cont['telephone']}  ")
    if cont.get("adresse_par"):
        lines.append(f"**Référent :** {cont['adresse_par']}\n")

    lines.append("---\n")

    if imp:
        lines += ["### ⚠ Note clinique importante", imp, "", "---\n"]

    lines.append("### 1. Acuité Visuelle")
    av_date_txt = f" *(en date du {av['date']})*" if av.get("date") else ""
    lines.append(f"*Source : {av.get('source', '?')}*{av_date_txt}")
    for side, sc_key, cc_key in [("OD", "od_sc", "od_cc"), ("OG", "og_sc", "og_cc")]:
        sc, cc = av.get(sc_key, ""), av.get(cc_key, "")
        if sc or cc:
            parts = []
            if sc: parts.append(f"sc {sc}")
            if cc: parts.append(f"cc {cc}")
            lines.append(f"- {side} : {' / '.join(parts)}")
    if not any([av.get("od_sc"), av.get("od_cc"), av.get("og_sc"), av.get("og_cc")]):
        lines.append("_Non renseignée_")

    lines.append("\n### 2. PIO (Pression Intra-Oculaire)")
    pio_date_txt = f" *(en date du {pio['date']})*" if pio.get("date") else ""
    if pio.get("od") or pio.get("og"):
        lines.append(f"*Mesure{pio_date_txt}*")
        if pio.get("od"): lines.append(f"- OD : {pio['od']} mmHg")
        if pio.get("og"): lines.append(f"- OG : {pio['og']} mmHg")
        if pio.get("alert"):
            lines.append("⚠ Hypertonie oculaire détectée — surveillance renforcée recommandée")
    else:
        lines.append("_Non renseignée_")

    lines += ["\n### 3. Antécédents & Allergies"]
    for item in ant["antecedents"]:
        if isinstance(item, dict):
            date_txt = f" [{item['date']}]" if item.get("date") else ""
            lines.append(f"- {item['label']}{date_txt}")
        else:
            lines.append(f"- {item}")
    if ant["allergies"]:
        lines.append("**Allergies :**")
        for item in ant["allergies"]:
            if isinstance(item, dict):
                date_txt = f" [{item['date']}]" if item.get("date") else ""
                lines.append(f"- ⚠ {item['label']}{date_txt}")
            else:
                lines.append(f"- ⚠ {item}")
    if not ant["antecedents"] and not ant["allergies"]:
        lines.append("_Aucun renseigné_")

    lines += ["\n### 4. Traitements"]
    if trt_h:
        local_items    = [i for i in trt_h if i.get("type") == "local"]
        systemic_items = [i for i in trt_h if i.get("type") != "local"]
        if local_items and systemic_items:
            lines.append("**Collyres / Locaux :**")
            for item in local_items:
                dt = f"[{item['date']}] " if item.get("date") else ""
                lines.append(f"- {dt}{item['label']}")
            lines.append("**Systémiques :**")
            for item in systemic_items:
                dt = f"[{item['date']}] " if item.get("date") else ""
                lines.append(f"- {dt}{item['label']}")
        else:
            for item in trt_h:
                dt = f"[{item['date']}] " if item.get("date") else ""
                lines.append(f"- {dt}{item['label']}")
    elif d["traitements"]:
        lines.extend(f"- {i}" for i in d["traitements"])
    else:
        lines.append("_Aucun renseigné_")

    diag_date_txt = f" *(en date du {d['diagnostic_date']})*" if d.get("diagnostic_date") else ""
    lines += [
        f"\n### 5. Diagnostic OPH{diag_date_txt}",
        d["diagnostic"] or "_Non renseigné_",
    ]

    lines += ["\n### 6. Plan de suivi", d["plan_suivi"] or "_Non planifié_"]

    lines += ["\n### 7. Prescriptions"]
    if prs_h:
        for p in prs_h:
            dt = f"Le {p['date']} : " if p.get("date") else ""
            if p.get("ordonnance"):
                lines.append(f"- {dt}{p['ordonnance']}")
            if p.get("autres"):
                lines.append(f"  *(Autres : {p['autres']})*")
    elif presc.get("ordonnance") or presc.get("autres"):
        if presc.get("date"):
            lines.append(f"*En date du {presc['date']}*")
        if presc["ordonnance"]:
            lines.append(f"**Ordonnance :** {presc['ordonnance']}")
        if presc["autres"]:
            lines.append(f"**Autres :** {presc['autres']}")
    else:
        lines.append("_Aucune prescription renseignée_")

    if d["pio_alert"]:
        lines += ["", "---", f"⚠ **Alerte PIO :** {d['pio_alert']}"]

    return "\n".join(lines)


def _render_dashboard(
    record: dict,
    generate_pdf_bytes_fn=None,
    pdf_available: bool = False,
    full_name: str = "",
    dob_str: str = "",
    patient_id: str = "",
) -> None:
    data  = analyse_patient(record)
    actes = _build_actes_rows(record)

    # Survival banner.
    st.markdown(_survival_banner_html(record, data), unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Three clinical cards side by side.
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 1, 1])

    with col_a:
        st.markdown(_visual_function_card_html(data), unsafe_allow_html=True)

    with col_b:
        st.markdown(_biomechanics_card_html(data, actes), unsafe_allow_html=True)

    with col_c:
        st.markdown(_terrain_card_html(data), unsafe_allow_html=True)

    # ── Level 3: PIO chart ────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.69rem;font-weight:800;color:#1B3A6B;'
        'letter-spacing:0.07em;text-transform:uppercase;'
        'border-bottom:1px solid #E2E8F0;padding-bottom:5px;'
        'margin-bottom:8px;font-family:\'Segoe UI\',sans-serif;">'
        '📈&nbsp; PIO — Évolution temporelle (OD / OG)'
        '</div>',
        unsafe_allow_html=True,
    )
    _render_pio_chart(record)


def render_medical_summary(
    record: dict,
    generate_pdf_bytes_fn=None,
    pdf_available: bool = False,
    full_name: str = "",
    dob_str: str = "",
    patient_id: str = "",
) -> None:
    """Main public entry point — renders the Cockpit Dashboard in Streamlit."""
    # Collapse sidebar automatically
    _collapse_sidebar_js = """
    <script>
    (function() {
        try {
            const btn = window.parent.document.querySelector(
                'button[data-testid="collapsedControl"], '
                + 'button[aria-label="Close sidebar"], '
                + 'button[title="Close sidebar"]'
            );
            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {
                const expanded = sidebar.getAttribute('aria-expanded');
                if (expanded === 'true' && btn) { btn.click(); }
            }
        } catch(e) {}
    })();
    </script>
    """
    st.markdown(_collapse_sidebar_js, unsafe_allow_html=True)

    # Inject global stylesheet once
    st.markdown(_CSS, unsafe_allow_html=True)

    _render_dashboard(
        record,
        generate_pdf_bytes_fn=generate_pdf_bytes_fn,
        pdf_available=pdf_available,
        full_name=full_name,
        dob_str=dob_str,
        patient_id=patient_id,
    )

    st.caption(
        f"Analyse générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}  ·  "
        "Données issues du dossier local  ·  "
        "Outil d'aide à la décision — ne remplace pas l'examen clinique."
    )