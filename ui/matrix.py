"""Vistas de solo lectura de la flota: tabla de contramedidas (plan de acción)
y matriz camión × contramedida (equivalente a la hoja «Top Page» del Excel).
Las usa la vista pública y la del administrador."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core import config
from core.project import Project
from ui.common import T, esc, pill_html

SHORT = {"closed": "✓", "executed": "E", "in_progress": "◐", "not_started": "·", "na": "N/A"}


def action_plan_table(p: Project, t: T, key: str) -> None:
    c = p.cms
    df = pd.DataFrame({
        t("col_no"): c.order,
        t("countermeasure"): c["name"],
        t("responsible"): c.owner,
        t("target"): c.target,
        t("executed"): c.executed.astype(str) + " / " + c.n.astype(str),
        t("fleet_pct"): c.pct * 100,
        t("closed_pct"): c.close_pct * 100,
        t("status"): c.status.map(lambda s: t("cst_" + s)),
    })
    st.dataframe(
        df, hide_index=True, width="stretch", key=key,
        column_config={
            t("fleet_pct"): st.column_config.ProgressColumn(t("fleet_pct"), format="%.0f%%", min_value=0, max_value=100),
            t("closed_pct"): st.column_config.ProgressColumn(t("closed_pct"), format="%.0f%%", min_value=0, max_value=100),
            t("target"): st.column_config.DateColumn(t("target"), format="DD-MMM-YY"),
            t("col_no"): st.column_config.NumberColumn(t("col_no"), width="small"),
        },
    )


def legend(t: T) -> None:
    items = "".join(
        f'<span style="margin-right:14px">{pill_html(t, s)} <small style="color:#888">{esc(SHORT[s])}</small></span>'
        for s in config.RECORD_STATUSES
    )
    st.markdown(f'<div style="margin:4px 0 8px">{items}</div>', unsafe_allow_html=True)


def matrix_view(p: Project, t: T, key: str, model: str | None = None) -> None:
    """Camión × contramedida, coloreado por estado (como la hoja Top Page)."""
    recs = p.records
    if model:
        fleets = set(p.trucks[p.trucks.model == model].fleet)
        recs = recs[recs.fleet.isin(fleets)]
    if recs.empty:
        st.info(t("no_data"))
        return
    names = p.cms.set_index("cm_id")["order"].astype(str) + ". " + p.cms.set_index("cm_id")["name"]
    status = recs.pivot_table(index="fleet", columns="cm_id", values="status", aggfunc="first")
    fleets = [f for f in p.fleets() if f in status.index]
    cm_ids = [c for c in p.cms.cm_id if c in status.columns]
    status = status.reindex(index=fleets, columns=cm_ids)
    shown = status.apply(lambda col: col.map(lambda s: SHORT.get(s, "") if isinstance(s, str) else ""))
    tr = p.trucks.set_index("fleet")
    shown.insert(0, t("executed"), [f"{tr.at[f, 'executed']}/{tr.at[f, 'n']}" for f in fleets])
    shown.columns = [t("executed")] + [names[c] for c in cm_ids]
    colors = status.apply(lambda col: col.map(
        lambda s: f"background-color:{config.STATUS_COLORS.get(s, '#FFFFFF')};color:{'#1A1A1A' if s in ('na', 'not_started') else '#FFFFFF'};text-align:center"
        if isinstance(s, str) else ""))
    colors.insert(0, "_e", "font-weight:600")
    colors.columns = shown.columns

    styler = shown.style.apply(lambda _: colors, axis=None)
    legend(t)
    st.dataframe(styler, width="stretch", height=min(38 + 35 * len(shown), 720), key=key)
