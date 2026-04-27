# CSS, HTML component builders for the Medical Dashboard.
# OD (Œil Droit) = Red  |  OG (Œil Gauche) = Blue
#
# Public API:
#   _CSS                                     — global stylesheet (inject once per page)
#   _survival_banner_html(record, data)      — identity + motif + alerts banner
#   _visual_function_card_html(data)         — visual acuity card
#   _biomechanics_card_html(data, actes_rows)— IOP + biometry + exam badges card
#   _terrain_card_html(data)                 — allergies + antecedents + diagnostic + treatments card
#   _patient_header_strip_html(record)       — legacy compact strip
#   _360_card_html(data)                     — legacy 360° card

from _utils import (
    _escape, _n_consult, _last_consult_date,
    _safe_df, _is_null_val, _val, _str_id,
)


# Global stylesheet — inject once per page.
_CSS = """
<style>
:root {
    /* ── OD (Œil Droit) — Rouge/Chaud ── */
    --od:         #C0392B;
    --od-dark:    #922B21;
    --od-mid:     #E74C3C;
    --od-bg:      #FDEDEC;
    --od-bg2:     #FEF9F8;
    --od-border:  #F1948A;

    /* ── OG (Œil Gauche) — Bleu/Froid ── */
    --og:         #1A5276;
    --og-dark:    #1B2F6E;
    --og-mid:     #2980B9;
    --og-bg:      #EBF5FB;
    --og-bg2:     #F4F9FD;
    --og-border:  #7FB3D3;

    /* ── Neutrals ── */
    --ck-navy:    #0F1F3D;
    --ck-navy2:   #1B3A6B;
    --ck-teal:    #0D7A5F;
    --ck-amber:   #D97706;
    --ck-red:     #DC2626;
    --ck-muted:   #6B7280;
    --ck-border:  #E5E7EB;
    --ck-card:    #FFFFFF;
    --ck-soft:    #F8FAFC;
    --ck-text:    #111827;
    --ck-r:       10px;
    --ck-shadow:  0 2px 16px rgba(0,0,0,0.07);
    --ck-font:    'Segoe UI', system-ui, Arial, sans-serif;
}

/* ═══════════════════════════════════════════════════════════════
   LEVEL 1 — SURVIVAL BANNER
   ═══════════════════════════════════════════════════════════════ */
.ck2-banner {
    display: flex; align-items: stretch;
    background: #0F1F3D;
    border-radius: var(--ck-r);
    border: 1px solid #1B3A6B;
    box-shadow: 0 4px 24px rgba(0,0,0,0.22);
    overflow: hidden;
    margin-bottom: 10px;
    font-family: var(--ck-font);
}
.ck2-banner-identity {
    flex: 0 0 210px; min-width: 0;
    padding: 11px 16px;
    border-right: 1px solid rgba(255,255,255,0.09);
    display: flex; flex-direction: column; justify-content: center; gap: 3px;
}
.ck2-banner-name {
    font-size: 0.96rem; font-weight: 800;
    color: #FFFFFF; letter-spacing: 0.01em; line-height: 1.25;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ck2-banner-id {
    font-size: 0.60rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: rgba(255,255,255,0.40);
    margin-top: 2px;
}
.ck2-banner-meta {
    font-size: 0.67rem; color: rgba(255,255,255,0.55); line-height: 1.55;
}
.ck2-banner-meta b { color: rgba(255,255,255,0.82); font-weight: 700; }
.ck2-banner-motif {
    flex: 1; min-width: 0; padding: 11px 20px;
    display: flex; flex-direction: column; justify-content: center;
    border-right: 1px solid rgba(255,255,255,0.09);
}
.ck2-banner-motif-label {
    font-size: 0.54rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.15em; color: rgba(255,255,255,0.38); margin-bottom: 4px;
}
.ck2-banner-motif-text {
    font-size: 1.05rem; font-weight: 700; color: #FFFFFF;
    line-height: 1.3; letter-spacing: 0.01em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ck2-banner-motif-date {
    font-size: 0.60rem; color: rgba(255,255,255,0.35); margin-top: 4px;
}
.ck2-banner-alerts {
    flex: 0 0 192px; padding: 9px 12px;
    display: flex; flex-direction: column; gap: 4px; justify-content: center;
}
.ck2-alert-allergy {
    display: flex; align-items: center; gap: 5px;
    background: #FEF2F2; border: 1px solid #FECACA;
    border-radius: 5px; padding: 4px 8px;
    font-size: 0.65rem; font-weight: 800; color: #991B1B;
    line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ck2-alert-important {
    display: flex; align-items: flex-start; gap: 5px;
    background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.30);
    border-radius: 5px; padding: 4px 8px;
    font-size: 0.62rem; font-weight: 600; color: #FCD34D;
    line-height: 1.35;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
}
.ck2-alert-none {
    font-size: 0.61rem; color: rgba(255,255,255,0.22); font-style: italic; padding: 4px 0;
}

/* ═══════════════════════════════════════════════════════════════
   LEVEL 2 — CLINICAL CARD SHELL (shared)
   ═══════════════════════════════════════════════════════════════ */
.ck2-card {
    background: #FFFFFF;
    border-radius: var(--ck-r);
    border: 1px solid #E2E8F0;
    box-shadow: var(--ck-shadow);
    overflow: hidden;
    font-family: var(--ck-font);
    margin-bottom: 8px;
}
.ck2-card-header {
    display: flex; align-items: center; gap: 7px;
    background: #F8FAFC; border-bottom: 2px solid #E2E8F0;
    padding: 6px 13px;
}
.ck2-card-icon { font-size: 0.85rem; line-height: 1; }
.ck2-card-title {
    font-size: 0.58rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.15em; color: var(--ck-navy2);
}
.ck2-card-title-date {
    font-size: 0.55rem; font-weight: 500; color: var(--ck-muted);
    font-style: italic; margin-left: 6px; letter-spacing: 0.02em;
}
.ck2-card-body { padding: 10px 13px 12px; }

/* ═══════════════════════════════════════════════════════════════
   COL 1 — FONCTION VISUELLE
   ═══════════════════════════════════════════════════════════════ */

/* Eye section container */
.ck2-eye-od {
    background: var(--od-bg2); border: 1px solid var(--od-border);
    border-radius: 7px; padding: 8px 10px; margin-bottom: 7px;
}
.ck2-eye-og {
    background: var(--og-bg2); border: 1px solid var(--og-border);
    border-radius: 7px; padding: 8px 10px; margin-bottom: 4px;
}

/* Eye label row */
.ck2-eye-hdr {
    display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
}
.ck2-dot-od {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--od); flex-shrink: 0; box-shadow: 0 0 0 2px var(--od-border);
}
.ck2-dot-og {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--og); flex-shrink: 0; box-shadow: 0 0 0 2px var(--og-border);
}
.ck2-eye-lbl-od {
    font-size: 0.60rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--od-dark);
}
.ck2-eye-lbl-og {
    font-size: 0.60rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--og-dark);
}
.ck2-eye-lbl-full {
    font-size: 0.56rem; font-weight: 400; color: var(--ck-muted); margin-left: 3px;
}

/* AV table grid: label | sc | cc */
.ck2-av-grid {
    display: grid; grid-template-columns: 40px 1fr 1fr;
    gap: 2px 6px; align-items: center;
}
.ck2-av-col-hdr {
    font-size: 0.53rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--ck-muted); text-align: center;
    padding-bottom: 3px; border-bottom: 1px solid #D1D5DB;
}
.ck2-av-row-lbl {
    font-size: 0.55rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: var(--ck-muted); text-align: right;
    padding-right: 5px; border-right: 1px solid #D1D5DB; white-space: nowrap;
}
.ck2-av-val-od {
    font-size: 0.94rem; font-weight: 800; color: var(--od-dark);
    text-align: center; line-height: 1.3;
}
.ck2-av-val-og {
    font-size: 0.94rem; font-weight: 800; color: var(--og-dark);
    text-align: center; line-height: 1.3;
}
.ck2-av-empty { font-size: 0.80rem; color: #CBD5E1; text-align: center; font-weight: 600; }

/* Refraction & Keratometry sub-rows */
.ck2-sub-row {
    display: flex; align-items: baseline; gap: 6px;
    margin-top: 5px; padding-top: 5px;
    border-top: 1px dashed #D1D5DB;
}
.ck2-sub-lbl {
    font-size: 0.52rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--ck-muted); white-space: nowrap; flex-shrink: 0;
    min-width: 40px; text-align: right; padding-right: 5px;
}
.ck2-sub-val-od { font-size: 0.72rem; font-weight: 700; color: var(--od-dark); line-height: 1.35; }
.ck2-sub-val-og { font-size: 0.72rem; font-weight: 700; color: var(--og-dark); line-height: 1.35; }
.ck2-sub-empty  { font-size: 0.64rem; color: #CBD5E1; font-style: italic; }

/* ═══════════════════════════════════════════════════════════════
   COL 2 — BIOMÉCANIQUE & DÉPISTAGE
   ═══════════════════════════════════════════════════════════════ */
.ck2-bio-table { width: 100%; border-collapse: collapse; margin-bottom: 4px; }
.ck2-bio-table th {
    font-size: 0.52rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--ck-muted);
    padding: 3px 6px 4px 0; border-bottom: 2px solid #E2E8F0;
    text-align: left;
}
.ck2-bio-table th:not(:first-child) { text-align: center; }
.ck2-bio-table td { padding: 5px 6px 5px 0; border-bottom: 1px solid #F1F5F9; }
.ck2-bio-table tr:last-child td { border-bottom: none; }
.ck2-bio-eye-cell {
    display: flex; align-items: center; gap: 5px;
    font-size: 0.60rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.12em;
}
.ck2-bio-val {
    font-size: 0.96rem; font-weight: 800; text-align: center; line-height: 1;
    display: block;
}
.ck2-bio-unit {
    font-size: 0.54rem; color: var(--ck-muted); display: block; text-align: center;
    margin-top: 1px; line-height: 1;
}
.ck2-bio-val-od { color: var(--od-dark); }
.ck2-bio-val-og { color: var(--og-dark); }
.ck2-bio-alert {
    display: inline-block; font-size: 0.53rem; font-weight: 900;
    background: var(--od-bg); color: var(--od);
    border: 1px solid var(--od-border); border-radius: 3px;
    padding: 1px 4px; margin-left: 3px; letter-spacing: 0.04em;
    vertical-align: middle;
}
.ck2-bio-empty { font-size: 0.66rem; color: #CBD5E1; font-style: italic; text-align: center; display: block; }

/* Exam badges */
.ck2-exams-sep {
    margin-top: 9px; padding-top: 8px; border-top: 1px solid #E2E8F0;
}
.ck2-exams-lbl {
    font-size: 0.52rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--ck-muted); margin-bottom: 6px;
}
.ck2-chip {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.62rem; font-weight: 700;
    padding: 3px 8px; border-radius: 5px;
    border: 1px solid transparent; margin: 2px 2px 2px 0;
    line-height: 1.4; white-space: nowrap;
}
.ck2-chip-img  { background: #F5F3FF; color: #4C1D95; border-color: #C4B5FD; }
.ck2-chip-exam { background: #ECFDF5; color: #065F46; border-color: #6EE7B7; }
.ck2-chip-proc { background: #FFFBEB; color: #92400E; border-color: #FCD34D; }
.ck2-chip-grey { background: #F9FAFB; color: #374151; border-color: #D1D5DB; }
.ck2-chip-date {
    font-size: 0.54rem; font-weight: 500; opacity: 0.65;
    padding-left: 4px; border-left: 1px solid currentColor; margin-left: 2px;
}

/* ═══════════════════════════════════════════════════════════════
   COL 3 — TERRAIN MÉDICAL & DÉCISION
   ═══════════════════════════════════════════════════════════════ */
.ck2-section { margin-bottom: 10px; }
.ck2-section:last-child { margin-bottom: 0; }
.ck2-section-lbl {
    font-size: 0.52rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--ck-muted);
    padding-bottom: 4px; margin-bottom: 6px;
    border-bottom: 1px solid #E2E8F0; display: flex; align-items: center; gap: 6px;
}
.ck2-diag-box {
    background: #F0F7FF; border: 1px solid #BAE6FD;
    border-left: 4px solid #0284C7; border-radius: 6px;
    padding: 7px 11px;
    font-size: 0.82rem; font-weight: 700; color: #0C4A6E; line-height: 1.45;
}
.ck2-diag-empty { font-size: 0.75rem; color: var(--ck-muted); font-style: italic; }
.ck2-trt-group {
    font-size: 0.53rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.13em; color: var(--ck-muted);
    margin: 7px 0 3px; display: flex; align-items: center; gap: 6px;
}
.ck2-trt-group::after { content: ''; flex: 1; height: 1px; background: #E2E8F0; }
.ck2-trt-item {
    display: flex; align-items: baseline; gap: 6px;
    padding: 3px 0; border-bottom: 1px dashed #F1F5F9;
}
.ck2-trt-item:last-child { border-bottom: none; }
.ck2-trt-dot {
    width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; margin-top: 5px;
}
.ck2-trt-dot-local   { background: #059669; }
.ck2-trt-dot-systemic{ background: #D97706; }
.ck2-trt-date {
    font-size: 0.56rem; font-weight: 700; color: var(--ck-muted);
    white-space: nowrap; flex-shrink: 0; min-width: 36px;
}
.ck2-trt-name { font-size: 0.78rem; color: var(--ck-text); line-height: 1.4; }
.ck2-trt-empty { font-size: 0.73rem; color: var(--ck-muted); font-style: italic; }
.ck2-rdv-box {
    display: flex; align-items: flex-start; gap: 8px;
    background: #EDE9FE; border-radius: 7px; padding: 8px 11px;
    border: 1px solid #C4B5FD;
}
.ck2-rdv-icon { font-size: 0.95rem; flex-shrink: 0; margin-top: 1px; }
.ck2-rdv-text { font-size: 0.80rem; font-weight: 700; color: #4C1D95; line-height: 1.4; }
.ck2-rdv-empty { font-size: 0.73rem; color: var(--ck-muted); font-style: italic; }

/* Allergies */
.ck2-section-lbl-danger {
    color: #991B1B !important; border-bottom-color: #FECACA !important;
}
.ck2-allergy-box {
    display: flex; flex-direction: column; gap: 3px;
}
.ck2-allergy-item {
    display: flex; align-items: center; gap: 6px;
    background: #FEF2F2; border: 1px solid #FECACA;
    border-left: 3px solid #DC2626;
    border-radius: 5px; padding: 4px 9px;
}
.ck2-allergy-icon { font-size: 0.72rem; color: #DC2626; flex-shrink: 0; }
.ck2-allergy-name { font-size: 0.78rem; font-weight: 700; color: #991B1B; }

/* Antécédents tags */
.ck2-ant-wrap { display: flex; flex-wrap: wrap; gap: 4px; }
.ck2-ant-tag {
    display: inline-flex; align-items: center; gap: 4px;
    background: #F1F5F9; border: 1px solid #CBD5E1;
    border-radius: 5px; padding: 3px 8px;
    font-size: 0.74rem; font-weight: 600; color: #334155; line-height: 1.4;
}
.ck2-ant-date {
    font-size: 0.58rem; font-weight: 500; color: #64748B;
    border-left: 1px solid #94A3B8; padding-left: 5px; margin-left: 2px;
}

/* ═══════════════════════════════════════════════════════════════
   LEVEL 3 — HISTORY SECTION HEADER
   ═══════════════════════════════════════════════════════════════ */
.ck2-history-hdr {
    font-size: 0.62rem; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.13em; color: var(--ck-navy2);
    border-bottom: 2px solid var(--ck-navy2); padding-bottom: 5px;
    margin: 12px 0 8px; font-family: var(--ck-font);
    display: flex; align-items: center; gap: 7px;
}

/* ═══════════════════════════════════════════════════════════════
   BACKWARDS COMPAT — ck-* classes (used by _actes.py & legacy code)
   ═══════════════════════════════════════════════════════════════ */
.ck-header-strip {
    display: flex; align-items: center; gap: 0;
    background: #1B3A6B; padding: 6px 18px;
    font-family: var(--ck-font); flex-wrap: wrap;
}
.ck-header-strip-item {
    display: flex; align-items: center; gap: 6px;
    color: rgba(255,255,255,0.92);
    font-size: 0.71rem; font-weight: 600;
    letter-spacing: 0.04em; padding: 0 14px 0 0;
}
.ck-header-strip-item:not(:last-child)::after {
    content: '·'; margin-left: 14px; opacity: 0.45;
}
.ck-header-strip-label {
    font-size: 0.60rem; font-weight: 500; text-transform: uppercase;
    letter-spacing: 0.09em; opacity: 0.58; margin-right: 4px;
}
.ck-act-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.ck-chip {
    font-size: 0.65rem; font-weight: 700; padding: 2px 9px;
    border-radius: 4px; white-space: nowrap; line-height: 1.55;
    border: 1px solid transparent; letter-spacing: 0.02em;
}
.ck-chip-img  { background: #F5F3FF; color: #4C1D95; border-color: #C4B5FD; }
.ck-chip-exam { background: #ECFDF5; color: #065F46; border-color: #6EE7B7; }
.ck-chip-proc { background: #FFFBEB; color: #92400E; border-color: #FCD34D; }
.ck-chip-grey { background: #F9FAFB; color: #374151; border-color: #D1D5DB; }
.ck-card {
    background: var(--ck-card); border-radius: var(--ck-r);
    box-shadow: var(--ck-shadow); border: 1px solid var(--ck-border);
    overflow: hidden; margin-bottom: 1.2rem; font-family: var(--ck-font);
}
.ck-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 20px;
    background: linear-gradient(135deg, #1B3A6B 0%, #234DA8 100%);
    color: #fff; flex-wrap: wrap; gap: 6px;
}
.ck-head-title { font-size: 0.69rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; }
.ck-head-meta  { font-size: 0.67rem; opacity: 0.72; letter-spacing: 0.04em; }
.ck-head-contact { font-size: 0.65rem; opacity: 0.65; letter-spacing: 0.03em; margin-top: 2px; width: 100%; }
.ck-head-dossier { font-size: 0.62rem; opacity: 0.58; letter-spacing: 0.03em; margin-top: 1px; width: 100%; font-style: italic; }
.ck-lbl { font-size: 0.58rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.10em; color: var(--ck-muted); margin-bottom: 9px; display: flex; align-items: center; flex-wrap: wrap; gap: 2px; }
.ck-lbl-date { font-size: 0.56rem; font-weight: 500; text-transform: none; letter-spacing: 0.02em; color: var(--ck-muted); font-style: italic; margin-left: 4px; padding-left: 6px; border-left: 1px solid #CBD5E1; opacity: 0.80; }
.ck-val-main { font-size: 0.98rem; font-weight: 700; color: var(--ck-navy); line-height: 1.45; }
.ck-val { font-size: 0.85rem; font-weight: 600; color: var(--ck-text); line-height: 1.55; }
.ck-val-muted { font-size: 0.79rem; color: var(--ck-muted); font-style: italic; font-weight: 400; }
.ck-tag { font-size: 0.69rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid transparent; line-height: 1.45; display: inline-flex; align-items: center; gap: 0; }
.t-navy  { background: #EFF6FF; color: #1E3A8A; border-color: #BFDBFE; }
.t-teal  { background: #ECFDF5; color: #065F46; border-color: #6EE7B7; }
.t-red   { background: #FEF2F2; color: #991B1B; border-color: #FECACA; }
.t-amber { background: #FFFBEB; color: #92400E; border-color: #FCD34D; }
.t-grey  { background: #F9FAFB; color: #374151; border-color: #D1D5DB; }
.ck-tag-date { font-size: 0.60rem; font-weight: 400; opacity: 0.62; margin-left: 6px; padding-left: 6px; border-left: 1px solid currentColor; white-space: nowrap; letter-spacing: 0.01em; }
.ck-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 2px; }
.ck-num { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border-radius: 50%; background: var(--ck-navy); color: #fff; font-size: 0.58rem; font-weight: 900; flex-shrink: 0; margin-right: 5px; }
.ck-important-banner { background: #FFF7ED; border-left: 4px solid #F59E0B; border-bottom: 1px solid #FDE68A; padding: 12px 22px 12px 18px; font-family: var(--ck-font); }
.ck-important-banner-title { font-size: 0.63rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.10em; color: #92400E; margin-bottom: 5px; display: flex; align-items: center; gap: 6px; }
.ck-important-banner-body { font-size: 0.82rem; color: #78350F; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.ck-allergy-warn { display: flex; align-items: center; gap: 6px; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; padding: 5px 10px; margin-bottom: 6px; font-size: 0.69rem; font-weight: 700; color: #991B1B; }
.ck-trt-section { font-size: 0.57rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.10em; color: var(--ck-muted); margin: 8px 0 4px 0; padding-bottom: 2px; border-bottom: 1px solid var(--ck-border); }
.ck-trt-section:first-child { margin-top: 0; }
.ck-hist { max-height: 400px; overflow-y: auto; padding-right: 2px; margin-top: 2px; }
.ck-hist-row { display: flex; gap: 10px; align-items: baseline; padding: 4px 0; border-bottom: 1px dashed #EAECF0; font-family: var(--ck-font); }
.ck-hist-row:last-child { border-bottom: none; }
.ck-hist-dt { font-size: 0.63rem; font-weight: 700; color: var(--ck-muted); white-space: nowrap; min-width: 50px; letter-spacing: 0.01em; flex-shrink: 0; }
.ck-hist-txt { font-size: 0.81rem; color: var(--ck-text); line-height: 1.45; word-break: break-word; }
.ck-hist-txt-muted { font-size: 0.75rem; color: var(--ck-muted); margin-top: 2px; line-height: 1.4; font-style: italic; }
.ck-rdv-box { display: flex; align-items: flex-start; gap: 10px; background: #EDE9FE; border-radius: 8px; padding: 11px 15px; border: 1px solid #C4B5FD; }
.ck-rdv-icon { font-size: 1.15rem; flex-shrink: 0; margin-top: 1px; }
.ck-rdv-text { font-size: 0.88rem; font-weight: 700; color: #4C1D95; line-height: 1.45; }
.ck-rdv-none { font-size: 0.79rem; color: var(--ck-muted); font-style: italic; }
.ck-row { display: flex; border-bottom: 1px solid var(--ck-border); }
.ck-row:last-of-type { border-bottom: none; }
.ck-cell { flex: 1 1 0; padding: 16px 20px; border-right: 1px solid var(--ck-border); min-height: 96px; min-width: 0; }
.ck-cell:last-child { border-right: none; }
.ck-cell-teal { background: linear-gradient(180deg,#F0FDF4 0%,#FAFAFA 100%); }
.ck-cell-blue { background: linear-gradient(180deg,#EFF6FF 0%,#FAFAFA 100%); }
.ck-cell-rdv  { background: linear-gradient(180deg,#F5F3FF 0%,#FAFAFA 100%); }
.ck-cell-pio  { background: linear-gradient(180deg,#FFF7ED 0%,#FAFAFA 100%); }
.ck-cell-av   { background: linear-gradient(180deg,#F0F9FF 0%,#FAFAFA 100%); }
.ck-pio-grid { display: flex; gap: 12px; margin-top: 4px; flex-wrap: wrap; }
.ck-pio-eye { display: flex; flex-direction: column; align-items: flex-start; background: #FFF; border: 1px solid #FED7AA; border-radius: 8px; padding: 8px 14px; min-width: 68px; }
.ck-pio-eye.alert { border-color: #FCA5A5; background: #FEF2F2; }
.ck-pio-label { font-size: 0.58rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.09em; color: var(--ck-muted); margin-bottom: 3px; }
.ck-pio-val { font-size: 1.05rem; font-weight: 800; color: #92400E; line-height: 1.2; }
.ck-pio-val.alert { color: var(--ck-red); }
.ck-pio-unit { font-size: 0.62rem; color: var(--ck-muted); margin-top: 1px; }
.ck-av-grid { display: grid; grid-template-columns: auto 1fr 1fr; gap: 4px 10px; font-family: var(--ck-font); font-size: 0.78rem; align-items: center; margin-top: 2px; }
.ck-av-eye-label { font-size: 0.60rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ck-muted); padding: 0 6px; border-right: 2px solid var(--ck-border); text-align: right; white-space: nowrap; }
.ck-av-val { font-size: 0.82rem; font-weight: 700; color: var(--ck-navy); }
.ck-av-sub { font-size: 0.62rem; color: var(--ck-muted); margin-top: 1px; white-space: nowrap; }
.ck-av-header { font-size: 0.58rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ck-muted); text-align: center; }
</style>
"""


def _survival_banner_html(record: dict, data: dict) -> str:
    """Full-width dark banner: identity (left) | motif (centre) | alerts (right)."""

    # --- Identity zone ---
    identity   = data.get("identity_info", {})
    full_name  = identity.get("full_name") or _escape(_patient_name_fallback(record))
    dob        = identity.get("dob", "")
    age        = identity.get("age", "")
    patient_id = identity.get("patient_id", "")

    id_line = ""
    if patient_id:
        id_line = f'<div class="ck2-banner-id">ID · {_escape(patient_id)}</div>'

    meta_parts = []
    if dob:
        meta_parts.append(f"Né(e) le <b>{_escape(dob)}</b>")
    if age:
        meta_parts.append(f"<b>{_escape(age)} ans</b>")
    meta_html = (
        f'<div class="ck2-banner-meta">{" · ".join(meta_parts)}</div>'
        if meta_parts else ""
    )

    identity_html = (
        '<div class="ck2-banner-identity">'
        f'<div class="ck2-banner-name">{_escape(full_name) if full_name else "—"}</div>'
        + id_line + meta_html +
        '</div>'
    )

    # --- Motif zone ---
    motif      = data.get("motif", "")
    motif_date = data.get("motif_date", "")
    motif_text = _escape(motif[:80]) if motif else "Bilan ophtalmologique"
    date_hint  = (
        f'<div class="ck2-banner-motif-date">Motif le {_escape(motif_date)}</div>'
        if motif_date else ""
    )
    motif_html = (
        '<div class="ck2-banner-motif">'
        '<div class="ck2-banner-motif-label">Motif de consultation</div>'
        f'<div class="ck2-banner-motif-text">{motif_text}</div>'
        + date_hint +
        '</div>'
    )

    # --- Alerts zone ---
    ant       = data.get("antecedents_allergies", {})
    allergies = ant.get("allergies", [])
    important = data.get("important", "")

    alerts_html = ""
    if allergies:
        alg_labels = [
            _escape(a.get("label", "") if isinstance(a, dict) else str(a))
            for a in allergies[:2]
        ]
        alerts_html += (
            '<div class="ck2-alert-allergy">'
            '⚠&nbsp; ALLERGIE : ' + " / ".join(alg_labels) +
            '</div>'
        )

    if important:
        snippet = _escape(important[:72]) + ("…" if len(important) > 72 else "")
        alerts_html += (
            f'<div class="ck2-alert-important">📌 {snippet}</div>'
        )

    if not alerts_html:
        alerts_html = '<div class="ck2-alert-none">Aucune alerte active</div>'

    alerts_zone = (
        '<div class="ck2-banner-alerts">' + alerts_html + '</div>'
    )

    return (
        '<div class="ck2-banner">'
        + identity_html + motif_html + alerts_zone +
        '</div>'
    )


def _visual_function_card_html(data: dict) -> str:
    """Visual acuity + refraction formula + keratometry, OD then OG."""
    av      = data.get("visual_acuity", {})
    refrac  = data.get("refraction_detail", {})
    kerato  = data.get("keratometry", {})
    av_date = av.get("date", "") or refrac.get("date", "")

    date_label = (
        f'<span class="ck2-card-title-date">en date du {_escape(av_date)}</span>'
        if av_date else ""
    )

    header = (
        '<div class="ck2-card-header">'
        '<span class="ck2-card-icon">👁</span>'
        f'<span class="ck2-card-title">Fonction Visuelle</span>{date_label}'
        '</div>'
    )

    od_html = _eye_block_html(
        eye="od",
        av_sc=av.get("od_sc", ""), av_cc=av.get("od_cc", ""),
        refrac_eye=refrac.get("od", {}),
        kerato_eye=kerato.get("od", {}),
    )
    og_html = _eye_block_html(
        eye="og",
        av_sc=av.get("og_sc", ""), av_cc=av.get("og_cc", ""),
        refrac_eye=refrac.get("og", {}),
        kerato_eye=kerato.get("og", {}),
    )

    has_cc = bool(av.get("od_cc") or av.get("og_cc"))
    col_label = (
        '<div class="ck2-av-grid" style="grid-template-columns:40px 1fr 1fr;">'
        '<div></div>'
        '<div class="ck2-av-col-hdr">sc</div>'
        '<div class="ck2-av-col-hdr">cc</div>'
        '</div>'
    ) if has_cc else (
        '<div class="ck2-av-grid" style="grid-template-columns:40px 1fr;">'
        '<div></div>'
        '<div class="ck2-av-col-hdr">sc</div>'
        '</div>'
    )

    return (
        '<div class="ck2-card">'
        + header +
        '<div class="ck2-card-body">'
        + col_label + od_html + og_html +
        '</div></div>'
    )


def _eye_block_html(
    eye: str,
    av_sc: str, av_cc: str,
    refrac_eye: dict,
    kerato_eye: dict,
) -> str:
    """Build one eye's block (OD or OG) with AV + refraction + kerato."""
    eye_cls    = "ck2-eye-od" if eye == "od" else "ck2-eye-og"
    dot_cls    = "ck2-dot-od" if eye == "od" else "ck2-dot-og"
    lbl_cls    = "ck2-eye-lbl-od" if eye == "od" else "ck2-eye-lbl-og"
    val_cls    = "ck2-av-val-od" if eye == "od" else "ck2-av-val-og"
    sub_cls    = "ck2-sub-val-od" if eye == "od" else "ck2-sub-val-og"
    lbl_text   = "OD — Œil Droit" if eye == "od" else "OG — Œil Gauche"
    lbl_short  = "OD" if eye == "od" else "OG"

    header = (
        '<div class="ck2-eye-hdr">'
        f'<span class="{dot_cls}"></span>'
        f'<span class="{lbl_cls}">{lbl_short}</span>'
        f'<span class="ck2-eye-lbl-full">{lbl_text.split("—")[1].strip()}</span>'
        '</div>'
    )

    def _av_val(v: str) -> str:
        return (
            f'<span class="{val_cls}">{_escape(v)}</span>'
            if v else
            '<span class="ck2-av-empty">—</span>'
        )

    has_cc = bool(av_cc)
    if has_cc:
        av_grid = (
            '<div class="ck2-av-grid" style="grid-template-columns:40px 1fr 1fr;">'
            '<div class="ck2-av-row-lbl">AV</div>'
            f'<div style="text-align:center">{_av_val(av_sc)}</div>'
            f'<div style="text-align:center">{_av_val(av_cc)}</div>'
            '</div>'
        )
    else:
        av_grid = (
            '<div class="ck2-av-grid" style="grid-template-columns:40px 1fr;">'
            '<div class="ck2-av-row-lbl">AV</div>'
            f'<div style="text-align:center">{_av_val(av_sc)}</div>'
            '</div>'
        )

    # Refraction formula row
    refrac_str = _fmt_refraction(refrac_eye)
    refrac_html = (
        '<div class="ck2-sub-row">'
        '<span class="ck2-sub-lbl">Réfrac.</span>'
        f'<span class="{sub_cls}">{_escape(refrac_str)}</span>'
        '</div>'
    ) if refrac_str else (
        '<div class="ck2-sub-row">'
        '<span class="ck2-sub-lbl">Réfrac.</span>'
        '<span class="ck2-sub-empty">Non renseignée</span>'
        '</div>'
    )

    # Keratometry row
    kerato_str = _fmt_keratometry(kerato_eye)
    kerato_html = (
        '<div class="ck2-sub-row">'
        '<span class="ck2-sub-lbl">Kérato.</span>'
        f'<span class="{sub_cls}">{_escape(kerato_str)}</span>'
        '</div>'
    ) if kerato_str else ""

    return (
        f'<div class="{eye_cls}">'
        + header + av_grid + refrac_html + kerato_html +
        '</div>'
    )


def _fmt_refraction(eye: dict) -> str:
    """Format: '+4.00 Cyl -0.50 à 35°  Add +2.00' or empty string."""
    if not eye:
        return ""
    parts = []
    if eye.get("sph"):
        parts.append(eye["sph"])
    cyl  = eye.get("cyl", "")
    axis = eye.get("axis", "")
    if cyl and axis:
        parts.append(f"Cyl {cyl} à {axis}")
    elif cyl:
        parts.append(f"Cyl {cyl}")
    if eye.get("add"):
        parts.append(f"Add {eye['add']}")
    return "  ".join(parts)


def _fmt_keratometry(eye: dict) -> str:
    """Format: 'K1: 43.20  K2: 44.10  (× 90°)' or empty string."""
    if not eye:
        return ""
    parts = []
    if eye.get("k1"):
        parts.append(f"K1 {eye['k1']}")
    if eye.get("k2"):
        parts.append(f"K2 {eye['k2']}")
    if eye.get("km") and not (eye.get("k1") or eye.get("k2")):
        parts.append(f"Km {eye['km']}")
    if eye.get("axis") and (eye.get("k1") or eye.get("k2")):
        parts.append(f"× {eye['axis']}°")
    return "  /  ".join(parts[:2]) + (
        f"  ({parts[2]})" if len(parts) > 2 else ""
    ) if parts else ""


# CSS class per exam category (used by biomechanics card chips).
_BADGE_CSS_MAP: dict[str, str] = {
    "img":  "ck2-chip ck2-chip-img",
    "exam": "ck2-chip ck2-chip-exam",
    "proc": "ck2-chip ck2-chip-proc",
    "":     "ck2-chip ck2-chip-grey",
}


def _biomechanics_card_html(data: dict, actes_rows: list) -> str:
    """PIO + Pachymétrie + TO Brute + Cylindre cornéen + exam badges."""
    pio      = data.get("pio", {})
    pio_date = pio.get("date", "")

    # All biometric data from the free-text REFRACTION parser
    rt        = data.get("refraction_text", {}) or {}
    pachy     = rt.get("pachy", {}) or {}
    pachy_od  = pachy.get("od")
    pachy_og  = pachy.get("og")
    to_brute  = pachy.get("to_brute", {}) or {}
    to_od     = to_brute.get("od")
    to_og     = to_brute.get("og")
    kerato_rt = rt.get("kerato", {}) or {}
    cyl_od    = kerato_rt.get("od", {}).get("cyl_corneen", "")
    cyl_og    = kerato_rt.get("og", {}).get("cyl_corneen", "")

    # Also try keratometry dict (from tKERATO)
    kerato_struct = data.get("keratometry", {}) or {}

    date_label = (
        f'<span class="ck2-card-title-date">en date du {_escape(pio_date)}</span>'
        if pio_date else ""
    )
    header = (
        '<div class="ck2-card-header">'
        '<span class="ck2-card-icon">🔬</span>'
        f'<span class="ck2-card-title">Biomécanique &amp; Dépistage</span>{date_label}'
        '</div>'
    )

    od_val  = pio.get("od", "")
    og_val  = pio.get("og", "")
    has_any = bool(od_val or og_val or pachy_od is not None or pachy_og is not None)

    # Show TO Brute column only if at least one value is present
    show_to = (to_od is not None or to_og is not None)

    def _val_cell(val, unit: str, eye: str, alert_threshold: float = None) -> str:
        if val is None or val == "":
            return '<td><span class="ck2-bio-empty">—</span></td>'
        val_cls = "ck2-bio-val-od" if eye == "od" else "ck2-bio-val-og"
        alert_badge = ""
        if alert_threshold is not None:
            try:
                if float(str(val).replace(",", ".")) > alert_threshold:
                    alert_badge = '<span class="ck2-bio-alert">⚠ HTO</span>'
            except (ValueError, AttributeError):
                pass
        return (
            f'<td style="text-align:center">'
            f'<span class="ck2-bio-val {val_cls}">{_escape(str(val))}</span>'
            f'<span class="ck2-bio-unit">{unit}</span>'
            + alert_badge +
            '</td>'
        )

    if has_any:
        # Dynamic headers: always PIO + Pachy, add TO Brute only if data exists
        th_extra = '<th>TO Brute</th>' if show_to else ''
        pio_table = (
            '<table class="ck2-bio-table"><thead><tr>'
            f'<th></th><th>PIO</th><th>Pachymétrie</th>{th_extra}'
            '</tr></thead><tbody>'
        )
        for eye, od_label_cls, od_dot_cls, pio_v, pachy_v, to_v in [
            ("od", "ck2-eye-lbl-od", "ck2-dot-od", od_val, pachy_od, to_od),
            ("og", "ck2-eye-lbl-og", "ck2-dot-og", og_val, pachy_og, to_og),
        ]:
            pio_table += (
                f'<tr>'
                f'<td><div class="ck2-bio-eye-cell">'
                f'<span class="{od_dot_cls}"></span>'
                f'<span class="{od_label_cls}">{eye.upper()}</span>'
                f'</div></td>'
                + _val_cell(pio_v, "mmHg", eye, alert_threshold=21.0)
                + _val_cell(pachy_v, "µm", eye)
            )
            if show_to:
                pio_table += _val_cell(to_v, "mmHg", eye)
            pio_table += '</tr>'
        pio_table += '</tbody></table>'
    else:
        pio_table = (
            '<span style="font-size:0.75rem;color:#CBD5E1;font-style:italic;">'
            'Données biométriques non renseignées</span>'
        )

    # Cylindre cornéen section — shown only when data available
    cyl_section = ""
    if cyl_od or cyl_og:
        rows_html = ""
        for eye_lbl, cyl_val, dot_cls, val_cls in [
            ("OD", cyl_od, "ck2-dot-od", "ck2-bio-val-od"),
            ("OG", cyl_og, "ck2-dot-og", "ck2-bio-val-og"),
        ]:
            if cyl_val:
                rows_html += (
                    f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0;">'
                    f'<span class="{dot_cls}" style="width:7px;height:7px;border-radius:50%;flex-shrink:0;"></span>'
                    f'<span style="font-size:0.60rem;font-weight:800;text-transform:uppercase;'
                    f'letter-spacing:0.10em;color:var(--ck-muted);min-width:20px;">{eye_lbl}</span>'
                    f'<span class="{val_cls}" style="font-size:0.78rem;font-weight:700;">'
                    f'{_escape(cyl_val)}</span>'
                    f'</div>'
                )
        cyl_section = (
            '<div style="margin-top:8px;padding-top:7px;border-top:1px solid #E2E8F0;">'
            '<div style="font-size:0.52rem;font-weight:900;text-transform:uppercase;'
            'letter-spacing:0.14em;color:var(--ck-muted);margin-bottom:4px;">'
            'Cylindre cornéen</div>'
            + rows_html +
            '</div>'
        )

    # Recent exam badges
    seen_labels: set = set()
    chips_html  = ""
    for row in actes_rows[:8]:
        for label, cat in row.get("tech_actes", []):
            if label and label not in seen_labels:
                seen_labels.add(label)
                chip_cls = _BADGE_CSS_MAP.get(cat, "ck2-chip ck2-chip-grey")
                date_span = (
                    f'<span class="ck2-chip-date">{_escape(row["date_str"])}</span>'
                    if row.get("date_str") else ""
                )
                chips_html += (
                    f'<span class="{chip_cls}">{_escape(label)}{date_span}</span>'
                )

    exams_section = (
        '<div class="ck2-exams-sep">'
        '<div class="ck2-exams-lbl">Examens récents</div>'
        + (chips_html if chips_html else
           '<span style="font-size:0.70rem;color:#CBD5E1;font-style:italic;">Aucun examen enregistré</span>')
        + '</div>'
    )

    return (
        '<div class="ck2-card">'
        + header +
        '<div class="ck2-card-body">'
        + pio_table + cyl_section + exams_section +
        '</div></div>'
    )


def _terrain_card_html(data: dict) -> str:
    """Allergies + Antécédents + Diagnostic OPH + Traitements + Plan de suivi."""
    diag      = data.get("diagnostic", "")
    diag_date = data.get("diagnostic_date", "")
    trt_hist  = data.get("traitements_history", [])
    plan      = data.get("plan_suivi", "")
    ant       = data.get("antecedents_allergies", {})
    allergies = ant.get("allergies", [])
    antecedents = ant.get("antecedents", [])

    header = (
        '<div class="ck2-card-header">'
        '<span class="ck2-card-icon">📋</span>'
        '<span class="ck2-card-title">Terrain &amp; Décision</span>'
        '</div>'
    )

    # ── 1. Allergies (priorité absolue — toujours en premier) ─────────────────
    allergy_section = ""
    if allergies:
        allergy_items = ""
        for a in allergies[:4]:
            label = _escape(a.get("label", "") if isinstance(a, dict) else str(a))
            allergy_items += (
                f'<div class="ck2-allergy-item">'
                f'<span class="ck2-allergy-icon">⚠</span>'
                f'<span class="ck2-allergy-name">{label}</span>'
                f'</div>'
            )
        allergy_section = (
            '<div class="ck2-section">'
            '<div class="ck2-section-lbl ck2-section-lbl-danger">⚠&nbsp; Allergies</div>'
            f'<div class="ck2-allergy-box">{allergy_items}</div>'
            '</div>'
        )

    # ── 2. Antécédents ────────────────────────────────────────────────────────
    ant_section = ""
    if antecedents:
        ant_tags = ""
        for item in antecedents[:5]:
            label = _escape(item.get("label", "") if isinstance(item, dict) else str(item))
            date  = item.get("date", "") if isinstance(item, dict) else ""
            date_span = (
                f'<span class="ck2-ant-date">{_escape(date)}</span>'
                if date else ""
            )
            ant_tags += f'<span class="ck2-ant-tag">{label}{date_span}</span>'
        ant_section = (
            '<div class="ck2-section">'
            '<div class="ck2-section-lbl">Antécédents</div>'
            f'<div class="ck2-ant-wrap">{ant_tags}</div>'
            '</div>'
        )
    else:
        ant_section = (
            '<div class="ck2-section">'
            '<div class="ck2-section-lbl">Antécédents</div>'
            '<div class="ck2-diag-empty">Aucun renseigné</div>'
            '</div>'
        )

    # ── 3. Diagnostic OPH ─────────────────────────────────────────────────────
    diag_date_span = (
        f'<span class="ck2-card-title-date">&nbsp;({_escape(diag_date)})</span>'
        if diag_date else ""
    )
    diag_lbl = f'<div class="ck2-section-lbl">Diagnostic OPH{diag_date_span}</div>'
    if diag:
        diag_content = f'<div class="ck2-diag-box">{_escape(diag)}</div>'
    else:
        diag_content = '<div class="ck2-diag-empty">Non renseigné</div>'
    diag_section = f'<div class="ck2-section">{diag_lbl}{diag_content}</div>'

    # ── 4. Traitements ────────────────────────────────────────────────────────
    trt_lbl     = '<div class="ck2-section-lbl">Traitements</div>'
    trt_content = _traitements_html(trt_hist)
    trt_section = f'<div class="ck2-section">{trt_lbl}{trt_content}</div>'

    # ── 5. Plan de suivi ──────────────────────────────────────────────────────
    plan_lbl = '<div class="ck2-section-lbl">Plan de suivi &amp; Prochain RDV</div>'
    if plan:
        plan_content = (
            '<div class="ck2-rdv-box">'
            '<span class="ck2-rdv-icon">📅</span>'
            f'<span class="ck2-rdv-text">{_escape(plan)}</span>'
            '</div>'
        )
    else:
        plan_content = '<div class="ck2-rdv-empty">Non planifié</div>'
    plan_section = f'<div class="ck2-section">{plan_lbl}{plan_content}</div>'

    return (
        '<div class="ck2-card">'
        + header +
        '<div class="ck2-card-body">'
        + allergy_section + ant_section + diag_section + trt_section + plan_section +
        '</div></div>'
    )


def _traitements_html(trt_hist: list) -> str:
    if not trt_hist:
        return '<div class="ck2-trt-empty">Aucun traitement renseigné</div>'

    local_items    = [i for i in trt_hist if i.get("type") == "local"]
    systemic_items = [i for i in trt_hist if i.get("type") != "local"]

    def _items_html(items: list, dot_cls: str) -> str:
        html = ""
        for item in items:
            dt   = _escape(item.get("date", "") or "—")
            name = _escape(item.get("label", ""))
            html += (
                '<div class="ck2-trt-item">'
                f'<span class="ck2-trt-dot {dot_cls}"></span>'
                f'<span class="ck2-trt-date">{dt}</span>'
                f'<span class="ck2-trt-name">{name}</span>'
                '</div>'
            )
        return html

    html = ""
    if local_items and systemic_items:
        html += (
            '<div class="ck2-trt-group">💧 Collyres / Locaux</div>'
            + _items_html(local_items, "ck2-trt-dot-local")
            + '<div class="ck2-trt-group">💊 Systémiques</div>'
            + _items_html(systemic_items, "ck2-trt-dot-systemic")
        )
    elif local_items:
        html += (
            '<div class="ck2-trt-group">💧 Collyres / Locaux</div>'
            + _items_html(local_items, "ck2-trt-dot-local")
        )
    else:
        html += (
            '<div class="ck2-trt-group">💊 Systémiques</div>'
            + _items_html(systemic_items, "ck2-trt-dot-systemic")
        )
    return html


# Legacy helpers — kept for _actes.py and external callers.

def _patient_name_fallback(record: dict) -> str:
    id_df = _safe_df(record, "identity")
    if id_df is None:
        return ""
    row = id_df.iloc[0]
    nom    = _val(row.get("NOM"), "")
    prenom = _val(row.get("Prénom") or row.get("PRENOM") or row.get("Prenom"), "")
    parts  = [p for p in (nom, prenom) if p and p != "—"]
    return " ".join(parts)


def _patient_header_strip_html(record: dict) -> str:
    """Legacy compact identity strip for backwards compatibility."""
    id_df      = _safe_df(record, "identity")
    patient_id = "—"
    if id_df is not None and not id_df.empty:
        raw_id = id_df.iloc[0].get("Code patient")
        if raw_id is not None and not _is_null_val(raw_id):
            patient_id = _escape(str(raw_id).strip())

    n_c       = _n_consult(record)
    last_date = _last_consult_date(record)

    def _item(label: str, value: str) -> str:
        return (
            f'<span class="ck-header-strip-item">'
            f'<span class="ck-header-strip-label">{label}</span>'
            f'{value}'
            f'</span>'
        )

    return (
        '<div class="ck-header-strip">'
        + _item("ID Patient", patient_id)
        + _item("Consultations", str(n_c))
        + _item("Dernière visite", _escape(last_date))
        + '</div>'
    )


# Legacy _ck_* helpers used by _actes.py.

def _ck_lbl(num: int, text: str, date_str: str = "") -> str:
    date_mention = (
        f'<span class="ck-lbl-date">En date du {_escape(date_str)}</span>'
        if date_str else ""
    )
    return (
        f'<div class="ck-lbl">'
        f'<span class="ck-num">{num}</span>{text}{date_mention}'
        f'</div>'
    )


def _ck_tags(items, cls: str) -> str:
    if not items:
        return '<span class="ck-val-muted">Aucun renseigné</span>'
    chips = []
    for item in items:
        if isinstance(item, dict):
            label    = _escape(item.get("label", ""))
            date_val = item.get("date", "")
            badge    = (
                f'<span class="ck-tag-date">{_escape(date_val)}</span>'
                if date_val else ""
            )
            chips.append(f'<span class="ck-tag {cls}">{label}{badge}</span>')
        else:
            chips.append(f'<span class="ck-tag {cls}">{_escape(str(item))}</span>')
    return '<div class="ck-tags">' + "".join(chips) + '</div>'


def _ck_mixed_tags(antecedents: list, allergies: list) -> str:
    has_ant = bool(antecedents)
    has_alg = bool(allergies)
    if not has_ant and not has_alg:
        return '<span class="ck-val-muted">Aucun renseigné</span>'
    html = ""
    if has_alg:
        alg_labels = [
            _escape(item.get("label", "") if isinstance(item, dict) else str(item))
            for item in allergies
        ]
        html += (
            '<div class="ck-allergy-warn">⚠ Allergie : '
            + " / ".join(alg_labels) + '</div>'
        )
    html += '<div class="ck-tags">'
    for item in antecedents:
        if isinstance(item, dict):
            label = _escape(item.get("label", ""))
            badge = (
                f'<span class="ck-tag-date">{_escape(item.get("date", ""))}</span>'
                if item.get("date") else ""
            )
            html += f'<span class="ck-tag t-navy">{label}{badge}</span>'
        else:
            html += f'<span class="ck-tag t-navy">{_escape(str(item))}</span>'
    for item in allergies:
        if isinstance(item, dict):
            label = _escape(item.get("label", ""))
            badge = (
                f'<span class="ck-tag-date">{_escape(item.get("date", ""))}</span>'
                if item.get("date") else ""
            )
            html += f'<span class="ck-tag t-red">⚠ {label}{badge}</span>'
        else:
            html += f'<span class="ck-tag t-red">⚠ {_escape(str(item))}</span>'
    html += '</div>'
    return html


def _ck_rdv(plan: str) -> str:
    if not plan:
        return '<span class="ck-rdv-none">Non planifié</span>'
    return (
        '<div class="ck-rdv-box">'
        '<span class="ck-rdv-icon">📅</span>'
        f'<span class="ck-rdv-text">{_escape(plan)}</span>'
        '</div>'
    )


def _ck_important_banner(text: str) -> str:
    if not text:
        return ""
    return (
        '<div class="ck-important-banner">'
        '<div class="ck-important-banner-title">⚠️&nbsp; Note clinique importante</div>'
        f'<div class="ck-important-banner-body">{_escape(text)}</div>'
        '</div>'
    )


def _ck_hist_block(items: list[dict], mode: str = "traitement") -> str:
    if not items:
        return '<span class="ck-val-muted">Aucun renseigné</span>'
    rows_html = ""
    for item in items:
        if mode == "traitement":
            dt_label = _escape(item.get("date", "")) or "—"
            txt      = _escape(item.get("label", ""))
            rows_html += (
                f'<div class="ck-hist-row">'
                f'<span class="ck-hist-dt">{dt_label}</span>'
                f'<span class="ck-hist-txt">{txt}</span>'
                f'</div>'
            )
        else:
            dt_raw  = item.get("date", "")
            dt_label = f"Le {_escape(dt_raw)}" if dt_raw else "—"
            ord_txt  = _escape(item.get("ordonnance", ""))
            aut_txt  = _escape(item.get("autres", ""))
            body     = ord_txt or aut_txt
            sub      = (
                f'<div class="ck-hist-txt-muted">{aut_txt}</div>'
                if ord_txt and aut_txt else ""
            )
            rows_html += (
                f'<div class="ck-hist-row">'
                f'<span class="ck-hist-dt">{dt_label}</span>'
                f'<div><div class="ck-hist-txt">{body}</div>{sub}</div>'
                f'</div>'
            )
    return f'<div class="ck-hist">{rows_html}</div>'


def _ck_av_block(av: dict) -> str:
    od_sc = av.get("od_sc", "")
    od_cc = av.get("od_cc", "")
    og_sc = av.get("og_sc", "")
    og_cc = av.get("og_cc", "")
    if not any([od_sc, od_cc, og_sc, og_cc]):
        return '<span class="ck-val-muted">Non renseignée</span>'

    def _fmt_av(v: str) -> str:
        return _escape(v) if v else '<span style="color:#9CA3AF">—</span>'

    has_cc = bool(od_cc or og_cc)
    if has_cc:
        html = (
            '<div class="ck-av-grid">'
            '<div></div>'
            '<div class="ck-av-header">sc</div>'
            '<div class="ck-av-header">cc</div>'
            f'<div class="ck-av-eye-label">OD</div>'
            f'<div class="ck-av-val">{_fmt_av(od_sc)}</div>'
            f'<div class="ck-av-val">{_fmt_av(od_cc)}</div>'
            f'<div class="ck-av-eye-label">OG</div>'
            f'<div class="ck-av-val">{_fmt_av(og_sc)}</div>'
            f'<div class="ck-av-val">{_fmt_av(og_cc)}</div>'
            '</div>'
        )
    else:
        html = (
            '<div class="ck-av-grid" style="grid-template-columns:auto 1fr;">'
            '<div></div>'
            '<div class="ck-av-header">sc</div>'
            f'<div class="ck-av-eye-label">OD</div>'
            f'<div class="ck-av-val">{_fmt_av(od_sc)}</div>'
            f'<div class="ck-av-eye-label">OG</div>'
            f'<div class="ck-av-val">{_fmt_av(og_sc)}</div>'
            '</div>'
        )
    src = av.get("source", "")
    src_note = (
        f'<div class="ck-av-sub" style="margin-top:6px;">Source : {_escape(src)}</div>'
        if src else ""
    )
    return html + src_note


def _ck_pio_block(pio: dict) -> str:
    od = pio.get("od", "")
    og = pio.get("og", "")
    if not od and not og:
        return '<span class="ck-val-muted">Non renseignée</span>'

    def _tile(label: str, val: str) -> str:
        is_alert = False
        try:
            if float(val.replace(",", ".")) > 21:
                is_alert = True
        except (ValueError, AttributeError):
            pass
        alert_cls = " alert" if is_alert else ""
        icon      = "⚠ " if is_alert else ""
        return (
            f'<div class="ck-pio-eye{alert_cls}">'
            f'<span class="ck-pio-label">{label}</span>'
            f'<span class="ck-pio-val{alert_cls}">{icon}{_escape(val) if val else "—"}</span>'
            f'<span class="ck-pio-unit">mmHg</span>'
            f'</div>'
        )

    return (
        '<div class="ck-pio-grid">'
        + (_tile("OD", od) if od else "")
        + (_tile("OG", og) if og else "")
        + '</div>'
    )


def _ck_traitements_block(trt_history: list[dict]) -> str:
    if not trt_history:
        return '<span class="ck-val-muted">Aucun renseigné</span>'

    local_items    = [i for i in trt_history if i.get("type") == "local"]
    systemic_items = [i for i in trt_history if i.get("type") != "local"]

    def _render_items(items: list[dict]) -> str:
        rows = ""
        for item in items:
            dt_label = _escape(item.get("date", "")) or "—"
            txt      = _escape(item.get("label", ""))
            rows += (
                f'<div class="ck-hist-row">'
                f'<span class="ck-hist-dt">{dt_label}</span>'
                f'<span class="ck-hist-txt">{txt}</span>'
                f'</div>'
            )
        return rows

    html = '<div class="ck-hist">'
    if local_items and systemic_items:
        html += '<div class="ck-trt-section">Collyres / Locaux</div>'
        html += _render_items(local_items)
        html += '<div class="ck-trt-section">Systémiques</div>'
        html += _render_items(systemic_items)
    else:
        html += _render_items(trt_history)
    html += '</div>'
    return html


# Legacy 360° card — kept for backwards compatibility.

def _360_card_html(data: dict) -> str:
    """Legacy 360° card — kept for backwards compatibility. New layout uses column cards."""
    ant           = data["antecedents_allergies"]
    plan          = data["plan_suivi"]
    diag          = data["diagnostic"]
    diag_date     = data.get("diagnostic_date", "")
    n_c           = data["n_consult"]
    date          = data["last_consult_date"]
    important     = data.get("important", "")
    contact       = data.get("contact", {"telephone": "", "adresse_par": ""})
    date_creation = data.get("date_creation", "")
    trt_history   = data.get("traitements_history", [])
    presc_history = data.get("prescriptions_history", [])
    av            = data.get("visual_acuity", {})
    pio           = data.get("pio", {})

    contact_parts = []
    if contact.get("telephone"):
        contact_parts.append(f"📞 {_escape(contact['telephone'])}")
    if contact.get("adresse_par"):
        contact_parts.append(f"Réf. : {_escape(contact['adresse_par'])}")
    contact_line = (
        f'<div class="ck-head-contact">{" &nbsp;·&nbsp; ".join(contact_parts)}</div>'
        if contact_parts else ""
    )
    dossier_line = (
        f'<div class="ck-head-dossier">Dossier ouvert le : {_escape(date_creation)}</div>'
        if date_creation else ""
    )
    header = (
        '<div class="ck-head"><div>'
        '<span class="ck-head-title">Profil Patient 360°</span>'
        + contact_line + dossier_line +
        '</div>'
        f'<span class="ck-head-meta">Dernière consultation : {date}'
        f' &nbsp;·&nbsp; {n_c} visite(s)</span>'
        '</div>'
    )
    important_html = _ck_important_banner(important)

    row1_cells = []
    av_date = av.get("date", "")
    row1_cells.append(
        '<div class="ck-cell ck-cell-av">'
        + _ck_lbl(1, "Acuité Visuelle", av_date)
        + _ck_av_block(av)
        + '</div>'
    )
    if pio.get("od") or pio.get("og"):
        pio_date = pio.get("date", "")
        row1_cells.append(
            '<div class="ck-cell ck-cell-pio">'
            + _ck_lbl(2, "PIO", pio_date)
            + _ck_pio_block(pio)
            + '</div>'
        )
    if ant["antecedents"] or ant["allergies"]:
        row1_cells.append(
            '<div class="ck-cell">'
            + _ck_lbl(3, "Antécédents &amp; Allergies")
            + _ck_mixed_tags(ant["antecedents"], ant["allergies"])
            + '</div>'
        )
    row1 = '<div class="ck-row">' + "".join(row1_cells) + '</div>' if row1_cells else ""

    row2_cells = []
    row2_cells.append(
        '<div class="ck-cell ck-cell-teal">'
        + _ck_lbl(4, "Traitements")
        + _ck_traitements_block(trt_history)
        + '</div>'
    )
    if diag:
        row2_cells.append(
            '<div class="ck-cell ck-cell-blue">'
            + _ck_lbl(5, "Diagnostic OPH", diag_date)
            + f'<div class="ck-val">{_escape(diag)}</div>'
            + '</div>'
        )
    if plan:
        row2_cells.append(
            '<div class="ck-cell ck-cell-rdv">'
            + _ck_lbl(6, "Plan de suivi")
            + _ck_rdv(plan)
            + '</div>'
        )
    row2 = '<div class="ck-row">' + "".join(row2_cells) + '</div>' if row2_cells else ""

    row3 = ""
    if presc_history:
        row3 = (
            '<div class="ck-row">'
            '<div class="ck-cell" style="flex:1;">'
            + _ck_lbl(7, "Prescriptions")
            + _ck_hist_block(presc_history, mode="prescription")
            + '</div>'
            '</div>'
        )

    return (
        '<div class="ck-card">'
        + header + important_html + row1 + row2 + row3
        + '</div>'
    )