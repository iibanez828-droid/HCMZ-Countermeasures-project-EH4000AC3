"""Vista del supervisor: registrar el avance de cada camión en cada contramedida
(planificado, pasos ejecutados, FIR, reporte, fechas, orden de trabajo y notas).

Dos formas de trabajar:
- Por contramedida: todos los camiones de una contramedida en una tabla.
- Por camión: todas las contramedidas de un camión en una tabla.
Solo se guardan las filas que cambiaron; cada fila cambiada es un evento nuevo.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.events import write_event
from ui.common import Ctx, cm_badge, cm_label, fmt_ts, note, safe_write, truck_badge, truck_label, user_name

TEXT_FIELDS = ("work_order", "note")
DATE_FIELDS = ("planned_date", "exec_date")
BOOL_FIELDS = ("planned", "fir", "report", "na")


def _nonce(key: str) -> int:
    return st.session_state.setdefault(f"nonce_{key}", 0)


def _bump(key: str) -> None:
    st.session_state[f"nonce_{key}"] = _nonce(key) + 1


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip()


def _iso(value) -> str:
    if value is None or value is pd.NaT or (isinstance(value, float) and value != value):
        return ""
    if isinstance(value, (date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


# ─── Página ───────────────────────────────────────────────────────────────
def render(ctx: Ctx) -> None:
    t = ctx.t
    mode = st.segmented_control(t("work_by"), ["cm", "truck"], default="cm", key="sup_mode",
                                format_func=lambda m: t("work_by_" + m)) or "cm"
    if mode == "cm":
        by_countermeasure(ctx)
    else:
        by_truck(ctx)


def by_countermeasure(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    if p.cms.empty:
        note(t("no_data"))
        return
    c1, c2, c3 = st.columns([2.2, 1.2, 1])
    cm_id = c1.selectbox(t("countermeasure"), p.cms.cm_id.tolist(), key="sup_cm", format_func=lambda c: cm_label(ctx, c))
    status = c2.selectbox(t("filter_status"), ["all", "not_started", "in_progress", "executed", "closed", "na"],
                          key="sup_cm_filter", format_func=lambda s: t("all") if s == "all" else t("st_" + s))
    search = c3.text_input(t("search_fleet"), key="sup_cm_q").strip().upper()
    cm_badge(ctx, cm_id)

    recs = p.cm_records(cm_id)
    if status != "all":
        recs = recs[recs.status == status]
    if search:
        recs = recs[recs.fleet.str.upper().str.contains(search) | recs.work_order.astype(str).str.contains(search)]
    steps = list(p.cm_row(cm_id).steps)
    records_editor(ctx, recs, steps, key=f"cm_{cm_id}_{status}_{search}", first="fleet")
    history(ctx, cm_id=cm_id)


def by_truck(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    fleets = p.fleets()
    if not fleets:
        note(t("no_data"))
        return
    fleet = st.selectbox(t("truck"), fleets, key="sup_truck", format_func=lambda f: truck_label(ctx, f))
    truck_badge(ctx, fleet)
    note(t("truck_mode_help"))
    records_editor(ctx, p.truck_records(fleet), None, key=f"truck_{fleet}", first="cm")
    history(ctx, fleet=fleet)


# ─── Tabla editable ───────────────────────────────────────────────────────
def records_editor(ctx: Ctx, recs: pd.DataFrame, steps: list[str] | None, key: str, first: str) -> None:
    """steps=None → modo por camión: un solo «Ejecutado» que marca todos los pasos."""
    t, p = ctx.t, ctx.project
    if recs.empty:
        note(t("no_rows"))
        return
    tz = p.settings.get("timezone", "UTC")
    rows = []
    for _, r in recs.iterrows():
        row = {"_cm": r.cm_id, "_fleet": r.fleet, "_n": len(r.steps)}
        if first == "fleet":
            row["fleet"] = r.fleet
            row["model"] = r.model
        else:
            row["cm"] = f"{r.order}. {r.cm_name}"
        row["planned"] = bool(r.planned)
        if steps is None:
            row["executed"] = bool(r.steps) and all(r.steps)
        else:
            for i, _ in enumerate(steps):
                row[f"s{i}"] = bool(r.steps[i]) if i < len(r.steps) else False
        row.update({"fir": bool(r.fir), "report": bool(r.report), "planned_date": r.planned_date,
                    "work_order": r.work_order, "exec_date": r.exec_date, "note": r.note, "na": bool(r.na),
                    "status": t("st_" + r.status), "progress": r.progress * 100,
                    "updated": f"{fmt_ts(r.last_ts, tz)} · {user_name(ctx, r.last_user)}" if r.last_ts else ""})
        rows.append(row)
    df = pd.DataFrame(rows)

    cfg = {
        "_cm": None, "_fleet": None, "_n": None,
        "fleet": st.column_config.TextColumn(t("truck"), disabled=True, pinned=True),
        "model": st.column_config.TextColumn(t("model"), disabled=True),
        "cm": st.column_config.TextColumn(t("countermeasure"), disabled=True, pinned=True, width="large"),
        "planned": st.column_config.CheckboxColumn(t("planned")),
        "executed": st.column_config.CheckboxColumn(t("executed")),
        "fir": st.column_config.CheckboxColumn(t("fir")),
        "report": st.column_config.CheckboxColumn(t("report")),
        "planned_date": st.column_config.DateColumn(t("planned_date"), format="DD-MMM-YY"),
        "work_order": st.column_config.TextColumn(t("work_order")),
        "exec_date": st.column_config.DateColumn(t("exec_date"), format="DD-MMM-YY"),
        "note": st.column_config.TextColumn(t("note"), width="medium"),
        "na": st.column_config.CheckboxColumn(t("na"), help=t("na_help"), disabled=not ctx.can_admin),
        "status": st.column_config.TextColumn(t("status"), disabled=True),
        "progress": st.column_config.ProgressColumn(t("progress"), format="%.0f%%", min_value=0, max_value=100),
        "updated": st.column_config.TextColumn(t("last_update"), disabled=True),
    }
    for i, label in enumerate(steps or []):
        cfg[f"s{i}"] = st.column_config.CheckboxColumn(label, help=t("step_help"))

    edited = st.data_editor(df, hide_index=True, width="stretch", column_config=cfg, num_rows="fixed",
                            disabled=["status", "progress", "updated"], key=f"ed_{key}_{_nonce(key)}",
                            height=min(40 + 35 * len(df), 640))

    changes = _diff(df, edited, steps)
    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    c2.caption(t("pending_changes", n=len(changes)) if changes else t("autofill_help"))
    if c1.button(t("save_changes"), type="primary", icon=":material/save:", disabled=not changes, key=f"save_{key}"):
        def write():
            for (cm_id, fleet), values in changes:
                write_event(ctx.store, "record", {"cm": cm_id, "fleet": fleet, "values": values}, ctx.user.username,
                            f"{fleet}-{cm_id}")
        if safe_write(ctx, write, t("saved_rows", n=len(changes))):
            _bump(key)
            st.rerun()


def _diff(before: pd.DataFrame, after: pd.DataFrame, steps: list[str] | None) -> list[tuple[tuple[str, str], dict]]:
    """Filas cambiadas → [((cm, camión), {campo: valor nuevo})]."""
    out = []
    today = date.today().isoformat()
    for i in range(len(before)):
        b, a = before.iloc[i], after.iloc[i]
        vals: dict = {}
        for f in BOOL_FIELDS:
            if bool(a[f]) != bool(b[f]):
                vals[f] = bool(a[f])
        for f in TEXT_FIELDS:
            if _clean(a[f]) != _clean(b[f]):
                vals[f] = _clean(a[f])
        for f in DATE_FIELDS:
            if _iso(a[f]) != _iso(b[f]):
                vals[f] = _iso(a[f])
        if steps is None:
            if bool(a["executed"]) != bool(b["executed"]):
                vals["steps"] = [bool(a["executed"])] * int(b["_n"])
        else:
            new = [bool(a[f"s{k}"]) for k in range(len(steps))]
            if new != [bool(b[f"s{k}"]) for k in range(len(steps))]:
                vals["steps"] = new
        if not vals:
            continue
        # Al marcar todos los pasos de ejecución: fecha de ejecución = hoy (si está vacía) y planificado
        all_done = vals.get("steps") and all(vals["steps"])
        if all_done:
            if not _iso(a["exec_date"]):
                vals["exec_date"] = today
            if not bool(a["planned"]):
                vals["planned"] = True
        if vals.get("planned_date") and not bool(a["planned"]):
            vals["planned"] = True
        out.append(((b["_cm"], b["_fleet"]), vals))
    return out


# ─── Historial ────────────────────────────────────────────────────────────
def history(ctx: Ctx, cm_id: str | None = None, fleet: str | None = None) -> None:
    t, p = ctx.t, ctx.project
    log = p.log
    if cm_id:
        log = log[log.cm_id == cm_id]
    if fleet:
        log = log[log.fleet == fleet]
    with st.expander(t("history_n", n=len(log)), icon=":material/history:"):
        if log.empty:
            st.caption(t("no_history"))
            return
        tz = p.settings.get("timezone", "UTC")
        show = log.head(200).assign(ts=lambda d: d.ts.map(lambda x: fmt_ts(x, tz)),
                                    user=lambda d: d.user.map(lambda u: user_name(ctx, u)))
        st.dataframe(show[["ts", "user", "fleet", "countermeasure", "change", "note"]], hide_index=True, width="stretch",
                     column_config={"ts": t("when"), "user": t("who"), "fleet": t("truck"),
                                    "countermeasure": t("countermeasure"), "change": t("change"), "note": t("note")})

