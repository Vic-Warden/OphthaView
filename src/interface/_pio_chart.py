# IOP temporal evolution chart (Plotly) and Streamlit renderer.

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

from _extractors import _extract_pio_history

# IOP threshold above which ocular hypertension is flagged
_PIO_NORMAL_LIMIT = 21.0

# Trace colours — OD blue / OG red (standard ophthalmology convention)
_PIO_COLOR_OD = "#1D4ED8"
_PIO_COLOR_OG = "#B91C1C"


# Build a Plotly figure showing IOP evolution over time.
# history: DataFrame[date, od, og] sorted ascending. show_od/show_og toggle each trace.
# Uses a white background so the chart renders correctly on any Streamlit theme.
# Min/max annotations are merged when both eyes share the same extremum.
def _build_pio_fig(
    history: pd.DataFrame,
    show_od: bool = True,
    show_og: bool = True,
) -> "go.Figure":
    dates     = history["date"]
    od_series = history["od"]
    og_series = history["og"]

    visible_vals = []
    if show_od:
        visible_vals.append(od_series)
    if show_og:
        visible_vals.append(og_series)
    all_visible = pd.concat(visible_vals).dropna() if visible_vals else pd.Series(dtype=float)
    y_max = float(all_visible.max()) + 4 if not all_visible.empty else 30
    y_min = max(0.0, float(all_visible.min()) - 4) if not all_visible.empty else 0

    fig = go.Figure()

    if show_od and od_series.notna().any():
        fig.add_trace(go.Scatter(
            x=dates, y=od_series,
            mode="lines+markers", name="OD — Œil Droit",
            line=dict(color=_PIO_COLOR_OD, width=2.5),
            marker=dict(size=8, color=_PIO_COLOR_OD, line=dict(width=2, color="#FFFFFF")),
            hovertemplate=(
                f"<b style='color:{_PIO_COLOR_OD}'>OD</b>"
                " : <b>%{y:.1f} mmHg</b><br>"
                "<span style='color:#6B7280'>%{x|%d/%m/%Y}</span><extra></extra>"
            ),
        ))

    if show_og and og_series.notna().any():
        fig.add_trace(go.Scatter(
            x=dates, y=og_series,
            mode="lines+markers", name="OG — Œil Gauche",
            line=dict(color=_PIO_COLOR_OG, width=2.5),
            marker=dict(size=8, color=_PIO_COLOR_OG, line=dict(width=2, color="#FFFFFF")),
            hovertemplate=(
                f"<b style='color:{_PIO_COLOR_OG}'>OG</b>"
                " : <b>%{y:.1f} mmHg</b><br>"
                "<span style='color:#6B7280'>%{x|%d/%m/%Y}</span><extra></extra>"
            ),
        ))

    # Add a styled callout annotation at the given data point.
    def _add_annotation(val, date, label_text, border_color, ay):
        fig.add_annotation(
            x=date, y=val,
            text=(
                f"<b>{label_text}</b><br>"
                f"<span style='color:#6B7280;font-size:10px'>{date.strftime('%d/%m/%Y')}</span>"
            ),
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor=border_color, ax=0, ay=ay,
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=border_color, borderwidth=1.5, borderpad=4,
            font=dict(size=11, color="#111111"),
        )

    if not all_visible.empty:
        points: list[dict] = []
        if show_od:
            for d, v in zip(dates, od_series):
                if pd.notna(v):
                    points.append({"date": d, "val": float(v), "eye": "od"})
        if show_og:
            for d, v in zip(dates, og_series):
                if pd.notna(v):
                    points.append({"date": d, "val": float(v), "eye": "og"})

        global_max = max(p["val"] for p in points)
        global_min = min(p["val"] for p in points)

        # Pick the date with the most eyes at target_val, then render a merged or per-eye annotation.
        def _resolve_annotation(target_val: float, ay: int) -> None:
            matches = [p for p in points if p["val"] == target_val]
            by_date: dict = {}
            for p in matches:
                by_date.setdefault(p["date"], set()).add(p["eye"])
            best_date  = max(by_date, key=lambda d: len(by_date[d]))
            eyes       = by_date[best_date]
            if "od" in eyes and "og" in eyes:
                label, border = f"OD = OG = {target_val:.1f} mmHg", "#6B7280"
            elif "od" in eyes:
                label, border = f"OD : {target_val:.1f} mmHg", _PIO_COLOR_OD
            else:
                label, border = f"OG : {target_val:.1f} mmHg", _PIO_COLOR_OG
            _add_annotation(target_val, best_date, label, border, ay)

        _resolve_annotation(global_max, ay=-40)
        if global_min != global_max:
            _resolve_annotation(global_min, ay=40)

    # Explicit colour constants keep the chart readable on any Streamlit theme
    _FONT_COLOR  = "#111111"
    _GRID_COLOR  = "#E5E7EB"
    _FONT_FAMILY = "'Segoe UI', Arial, sans-serif"

    fig.update_layout(
        height=300,
        margin=dict(l=4, r=12, t=36, b=4),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
            font=dict(size=11, color=_FONT_COLOR, family=_FONT_FAMILY),
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#D1D5DB", borderwidth=1,
        ),
        xaxis=dict(
            title=None, showgrid=False, showline=True, linecolor="#9CA3AF", linewidth=1,
            tickformat="%b %Y", tickfont=dict(size=10, color=_FONT_COLOR, family=_FONT_FAMILY),
            ticks="outside", ticklen=4, tickcolor="#9CA3AF",
        ),
        yaxis=dict(
            title=dict(text="PIO (mmHg)", font=dict(size=10, color=_FONT_COLOR, family=_FONT_FAMILY)),
            tickfont=dict(size=10, color=_FONT_COLOR, family=_FONT_FAMILY),
            showgrid=True, gridcolor=_GRID_COLOR, gridwidth=1,
            showline=True, linecolor="#9CA3AF", linewidth=1,
            range=[y_min, y_max], zeroline=False,
            ticks="outside", ticklen=4, tickcolor="#9CA3AF",
        ),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor="#D1D5DB",
            font=dict(size=11, color=_FONT_COLOR, family=_FONT_FAMILY),
        ),
        font=dict(family=_FONT_FAMILY, color=_FONT_COLOR),
    )

    return fig


# Render the IOP section in Streamlit: KPI tiles for the last visit + three chart tabs (OD+OG / OD / OG).
def _render_pio_chart(record: dict) -> None:
    history = _extract_pio_history(record)

    if history.empty:
        st.markdown(
            '<div style="font-size:0.80rem;color:#6B7280;font-style:italic;padding:8px 0 4px 0;">'
            '📊 Aucune donnée PIO historisée disponible pour ce patient.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    last = history.iloc[-1]
    prev = history.iloc[-2] if len(history) >= 2 else None

    def _delta(col: str) -> float | None:
        if prev is None:
            return None
        curr_v, prev_v = last[col], prev[col]
        if pd.isna(curr_v) or pd.isna(prev_v):
            return None
        return round(float(curr_v) - float(prev_v), 1)

    def _fmt_val(v) -> str:
        return f"{v:.0f} mmHg" if not pd.isna(v) else "—"

    def _delta_label(d: float | None) -> str | None:
        if d is None:
            return None
        return f"{'+'if d > 0 else ''}{d:.1f} vs visite préc."

    col_od, col_og, _ = st.columns([1, 1, 2])

    with col_od:
        od_val = last["od"]
        st.metric(
            label="PIO — Œil Droit (OD)",
            value=_fmt_val(od_val) if not pd.isna(od_val) else "—",
            delta=_delta_label(_delta("od")),
            delta_color="inverse",
            help="Pression intra-oculaire OD. Seuil normal : ≤ 21 mmHg.",
        )
        if not pd.isna(od_val) and float(od_val) > _PIO_NORMAL_LIMIT:
            st.markdown(
                '<span style="font-size:0.72rem;color:#DC2626;font-weight:700;">⚠ Hypertonie OD</span>',
                unsafe_allow_html=True,
            )

    with col_og:
        og_val = last["og"]
        st.metric(
            label="PIO — Œil Gauche (OG)",
            value=_fmt_val(og_val) if not pd.isna(og_val) else "—",
            delta=_delta_label(_delta("og")),
            delta_color="inverse",
            help="Pression intra-oculaire OG. Seuil normal : ≤ 21 mmHg.",
        )
        if not pd.isna(og_val) and float(og_val) > _PIO_NORMAL_LIMIT:
            st.markdown(
                '<span style="font-size:0.72rem;color:#DC2626;font-weight:700;">⚠ Hypertonie OG</span>',
                unsafe_allow_html=True,
            )

    if not _PLOTLY_AVAILABLE:
        st.info("Installez plotly (`pip install plotly`) pour afficher le graphique d'évolution.")
        return

    caption = (
        f"{len(history)} mesure(s) disponible(s)  ·  "
        "OD = Œil Droit (bleu)  ·  OG = Œil Gauche (rouge)"
    )
    cfg = {"displayModeBar": False, "responsive": True}

    tab_both, tab_od, tab_og = st.tabs(["OD + OG", "OD seul", "OG seul"])

    with tab_both:
        st.plotly_chart(_build_pio_fig(history, show_od=True, show_og=True),
                        use_container_width=True, config=cfg)
        st.caption(caption)

    with tab_od:
        if history["od"].notna().any():
            st.plotly_chart(_build_pio_fig(history, show_od=True, show_og=False),
                            use_container_width=True, config=cfg)
            st.caption(caption)
        else:
            st.info("Aucune mesure OD disponible.")

    with tab_og:
        if history["og"].notna().any():
            st.plotly_chart(_build_pio_fig(history, show_od=False, show_og=True),
                            use_container_width=True, config=cfg)
            st.caption(caption)
        else:
            st.info("Aucune mesure OG disponible.")
