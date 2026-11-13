"""Vista del administrador (7 pestañas): resumen y alertas, Top Page (matriz),
avance, contramedidas (plan de acción), camiones, reportes y configuración."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd
import streamlit as st

from core import config
from core.events import write_event
from core.project import fmt_hours
from core.executive_report import alert_text, build_executive_pdf
from core.reports import build_excel, status_csv
from storage.base import StorageError
from ui import supervisor
from ui.common import (PUBLIC_USER, Ctx, cm_label, esc, fleet_kpis, fmt_ts, new_report_id, note, password_form,
                       pdf_download, safe_write, section, user_name)
from ui.gantt import forecast_cards
from ui.matrix import action_plan_table, matrix_view


def render(ctx: Ctx) -> None:
    t = ctx.t
    tabs = st.tabs([t("tab_summary"), t("tab_matrix"), t("tab_progress"), t("tab_cms"), t("tab_hours"),
                    t("tab_trucks"), t("tab_reports"), t("tab_settings")])
    with tabs[0]:
        summary(ctx)
    with tabs[1]:
        top_page(ctx)
    with tabs[2]:
        supervisor.render(ctx)
    with tabs[3]:
        countermeasures(ctx)
    with tabs[4]:
        working_hours(ctx)
    with tabs[5]:
        trucks(ctx)
    with tabs[6]:
        reports(ctx)
        print_register(ctx)
    with tabs[7]:
        settings(ctx)


# ─── Resumen ──────────────────────────────────────────────────────────────
ALERT_CLASS = {"overdue": "", "planned_missed": "", "due_soon": "orange", "docs_pending": "blue"}


def summary(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    fleet_kpis(t, p)
    alerts = p.alerts()
    section(t("alerts_n", n=len(alerts)))
    if not alerts:
        note(t("no_alerts"))
    names = dict(zip(p.cms.cm_id, p.cms["name"]))
    for a in alerts:
        st.markdown(f'<div class="alert {ALERT_CLASS[a["type"]]}"><b>{esc(names.get(a["cm"], a["cm"]))} · '
                    f'{esc(t("alert_title_" + a["type"]))}</b><br>{esc(alert_text(t, a))}</div>', unsafe_allow_html=True)
    section(t("action_plan"))
    action_plan_table(p, t, "adm_plan")
    section(t("recent_changes"))
    log = p.log.head(15)
    if log.empty:
        st.caption(t("no_history"))
    else:
        tz = p.settings.get("timezone", "UTC")
        st.dataframe(log.assign(ts=log.ts.map(lambda x: fmt_ts(x, tz)), user=log.user.map(lambda u: user_name(ctx, u)))
                     [["ts", "user", "kind", "fleet", "countermeasure", "change"]], hide_index=True, width="stretch",
                     column_config={"ts": t("when"), "user": t("who"), "kind": t("kind"), "fleet": t("truck"),
                                    "countermeasure": t("countermeasure"), "change": t("change")})


def top_page(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    models = sorted(m for m in p.trucks.model.unique() if m)
    model = st.segmented_control(t("model"), ["all"] + models, default="all", key="adm_mx_model",
                                 format_func=lambda m: t("all") if m == "all" else m) or "all"
    matrix_view(p, t, "adm_matrix", None if model == "all" else model)


# ─── Contramedidas ────────────────────────────────────────────────────────
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "cm"


def countermeasures(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    section(t("edit_cm"))
    cm_id = st.selectbox(t("countermeasure"), p.cms.cm_id.tolist(), key="adm_cm", format_func=lambda c: cm_label(ctx, c))
    c = p.cm_row(cm_id)
    with st.form(f"meta_{cm_id}"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input(t("name"), c["name"])
        model = c2.text_input(t("model"), c.model)
        owner = c3.text_input(t("responsible"), c.owner)
        c4, c5 = st.columns(2)
        target = c4.date_input(t("target"), c.target, format="DD/MM/YYYY")
        duration = c5.text_input(t("duration"), c.duration, help=t("duration_help"))
        action = st.text_area(t("action_required"), c.action)
        st.caption(t("steps_fixed", steps=", ".join(c.steps)))
        if st.form_submit_button(t("save"), type="primary", icon=":material/save:"):
            values = {"name": name.strip() or c["name"], "model": model.strip(), "owner": owner.strip(),
                      "target": target.isoformat() if isinstance(target, date) else "",
                      "duration": duration.strip(), "action": action.strip()}
            current = {"name": c["name"], "model": c.model or "", "owner": c.owner or "",
                       "target": c.target.isoformat() if c.target else "", "duration": c.duration or "",
                       "action": c.action or ""}
            changed = {k: v for k, v in values.items() if v != current[k]}
            if not changed:
                st.info(t("no_changes"))
            elif safe_write(ctx, lambda: write_event(ctx.store, "meta", {"cm": cm_id, "values": changed},
                                                     ctx.user.username, cm_id), t("saved")):
                st.rerun()

    section(t("add_cm"))
    with st.form("add_cm", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input(t("name"))
        model = c2.text_input(t("model"), "EH4000AC-3")
        owner = c3.text_input(t("responsible"))
        c4, c5, c6 = st.columns(3)
        target = c4.date_input(t("target"), None, format="DD/MM/YYYY")
        duration = c5.text_input(t("duration"))
        steps = c6.text_input(t("steps"), "Executed", help=t("steps_help"))
        action = st.text_area(t("action_required"))
        copy_from = st.selectbox(t("copy_trucks_from"), [""] + p.cms.cm_id.tolist(),
                                 format_func=lambda x: t("no_trucks") if not x else cm_label(ctx, x))
        if st.form_submit_button(t("add_cm"), type="primary", icon=":material/add:"):
            if not name.strip():
                st.error(t("err_name"))
            else:
                new_id, n = _slug(name), 2
                while new_id in set(p.cms.cm_id) | set(p.removed_cms):
                    new_id, n = f"{_slug(name)}-{n}", n + 1
                fleets = [] if not copy_from else [
                    {"fleet": r.fleet, "serial": r.serial, "model": r.model, "na": bool(r.na)}
                    for _, r in p.cm_records(copy_from).iterrows()]
                payload = {"action": "add_cm", "cm": new_id, "fleets": fleets, "values": {
                    "name": name.strip(), "model": model.strip(), "owner": owner.strip(),
                    "target": target.isoformat() if isinstance(target, date) else "", "duration": duration.strip(),
                    "action": action.strip(), "steps": [s.strip() for s in steps.split(",") if s.strip()]}}
                if safe_write(ctx, lambda: write_event(ctx.store, "scope", payload, ctx.user.username, new_id),
                              t("cm_added", name=name.strip())):
                    st.rerun()

    section(t("remove_cm"))
    with st.form("rm_cm"):
        rm = st.selectbox(t("countermeasure"), p.cms.cm_id.tolist(), format_func=lambda c: cm_label(ctx, c), key="rm_cm_sel")
        sure = st.checkbox(t("confirm_remove_cm"))
        if st.form_submit_button(t("remove_cm"), icon=":material/delete:"):
            if not sure:
                st.error(t("err_confirm"))
            elif safe_write(ctx, lambda: write_event(ctx.store, "scope", {"action": "remove_cm", "cm": rm},
                                                     ctx.user.username, rm), t("cm_removed")):
                st.rerun()


# ─── Horas de trabajo ─────────────────────────────────────────────────────
def working_hours(ctx: Ctx) -> None:
    """Horas estimadas por camión de cada contramedida (editables en cualquier momento),
    capacidad para el pronóstico y parada estimada por camión."""
    t, p = ctx.t, ctx.project
    forecast_cards(p, t)
    section(t("wh_title"))
    note(esc(t("wh_help")))
    c = p.cms
    df = pd.DataFrame({"cm_id": c.cm_id, "no": c.order, "name": c["name"], "hours": c.hours.astype(float),
                       "pending": c.pending_n, "remaining": c.remaining_h.round(1)})
    nonce = st.session_state.setdefault("wh_nonce", 0)
    edited = st.data_editor(
        df, hide_index=True, width="stretch", num_rows="fixed", key=f"wh_editor_{nonce}",
        disabled=["no", "name", "pending", "remaining"], height=min(40 + 35 * len(df), 760),
        column_config={
            "cm_id": None,
            "no": st.column_config.NumberColumn(t("col_no"), width="small"),
            "name": st.column_config.TextColumn(t("countermeasure"), width="large"),
            "hours": st.column_config.NumberColumn(t("wh_hours"), min_value=0.0, max_value=1000.0, step=0.5,
                                                   format="%.1f h"),
            "pending": st.column_config.NumberColumn(t("wh_pending")),
            "remaining": st.column_config.NumberColumn(t("wh_remaining"), format="%.1f h"),
        })
    changes = []
    for (_, b), (_, a) in zip(df.iterrows(), edited.iterrows()):
        old = None if pd.isna(b.hours) else float(b.hours)
        new = None if pd.isna(a.hours) else float(a.hours)
        if old != new:
            changes.append((b.cm_id, "" if new is None else f"{fmt_hours(new)} h"))
    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    if changes:
        c2.caption(t("pending_changes", n=len(changes)))
    if c1.button(t("save"), type="primary", icon=":material/save:", disabled=not changes, key="wh_save"):
        def write():
            for cm_id, duration in changes:
                write_event(ctx.store, "meta", {"cm": cm_id, "values": {"duration": duration}},
                            ctx.user.username, cm_id)
        if safe_write(ctx, write, t("wh_saved", n=len(changes))):
            st.session_state["wh_nonce"] = nonce + 1
            st.rerun()

    missing = c[c.hours.isna() & (c.pending_n > 0)]["name"].tolist()
    if missing:
        st.warning(t("wh_no_estimate", names=", ".join(missing)), icon=":material/warning:")

    section(t("wh_capacity"))
    s = p.settings
    with st.form("wh_capacity"):
        c1, c2 = st.columns(2)
        hpd = c1.number_input(t("wh_hpd"), 1.0, 24.0, float(s.get("hours_per_day", 12)), 0.5, help=t("wh_hpd_help"))
        par = c2.number_input(t("wh_parallel"), 1, 50, int(float(s.get("parallel_trucks", config.DEFAULT_SETTINGS["parallel_trucks"]))), 1,
                              help=t("wh_parallel_help"))
        if st.form_submit_button(t("save_settings"), type="primary", icon=":material/save:"):
            values = {"hours_per_day": float(hpd), "parallel_trucks": int(par)}
            if safe_write(ctx, lambda: write_event(ctx.store, "settings", {"values": values}, ctx.user.username),
                          t("settings_saved")):
                st.rerun()

    section(t("wh_downtime_table"))
    hpd_now = max(float(s.get("hours_per_day", 12) or 12), 1.0)
    tr = p.trucks[p.trucks.remaining_h > 0].sort_values("remaining_h", ascending=False)
    if tr.empty:
        note(esc(t("no_data")))
        return
    st.dataframe(pd.DataFrame({"fleet": tr.fleet, "model": tr.model, "pending": tr.pending,
                               "hours": tr.remaining_h.round(1), "days": (tr.remaining_h / hpd_now).round(1)}),
                 hide_index=True, width="stretch", height=min(40 + 35 * len(tr), 420),
                 column_config={"fleet": t("truck"), "model": t("model"), "pending": t("sb_pending"),
                                "hours": st.column_config.NumberColumn(t("sb_downtime"), format="%.1f h"),
                                "days": st.column_config.NumberColumn(t("wh_days"), format="%.1f")})


# ─── Camiones ─────────────────────────────────────────────────────────────
def trucks(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    section(t("fleet_summary"))
    tr = p.trucks
    st.dataframe(tr.assign(pct=tr.pct * 100), hide_index=True, width="stretch", height=320,
                 column_config={"fleet": t("truck"), "serial": t("serial"), "model": t("model"), "n": t("applicable"),
                                "executed": t("executed"), "closed": t("closed_out"),
                                "pct": st.column_config.ProgressColumn(t("fleet_pct"), format="%.0f%%", min_value=0, max_value=100),
                                "pending": t("sb_pending"),
                                "remaining_h": st.column_config.NumberColumn(t("sb_downtime"), format="%.1f h")})
    cm_ids = p.cms.cm_id.tolist()
    section(t("add_truck"))
    with st.form("add_truck", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        fleet = c1.text_input(t("truck"), placeholder="RD232")
        serial = c2.text_input(t("serial"))
        model = c3.text_input(t("model"), "EH4000AC-3")
        cms = st.multiselect(t("applies_to"), cm_ids, default=cm_ids, format_func=lambda c: cm_label(ctx, c))
        if st.form_submit_button(t("add_truck"), type="primary", icon=":material/add:"):
            f = re.sub(r"\s+", "", fleet).upper()
            if not re.fullmatch(r"[A-Z0-9_-]{2,12}", f):
                st.error(t("err_fleet"))
            elif not cms:
                st.error(t("err_pick_cm"))
            else:
                payload = {"action": "add_truck", "fleet": f, "serial": serial.strip(), "model": model.strip(), "cms": cms}
                if safe_write(ctx, lambda: write_event(ctx.store, "scope", payload, ctx.user.username, f),
                              t("truck_added", fleet=f)):
                    st.rerun()
    section(t("remove_truck"))
    fleets = p.fleets()
    rm = st.selectbox(t("truck"), fleets, key="rm_truck")
    present = sorted(p.records[p.records.fleet == rm].cm_id.unique(), key=lambda c: p.cm_row(c).order) if rm else []
    with st.form("rm_truck"):
        cms = st.multiselect(t("remove_from"), present, default=present, format_func=lambda c: cm_label(ctx, c))
        sure = st.checkbox(t("confirm_remove_truck"))
        if st.form_submit_button(t("remove_truck"), icon=":material/delete:"):
            if not sure or not cms:
                st.error(t("err_confirm"))
            elif safe_write(ctx, lambda: write_event(ctx.store, "scope", {"action": "remove_truck", "fleet": rm, "cms": cms},
                                                     ctx.user.username, rm), t("truck_removed", fleet=rm)):
                st.rerun()
    note(t("na_tip"))


# ─── Reportes ─────────────────────────────────────────────────────────────
def reports(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    stamp = f"{p.today:%Y%m%d}"
    section(t("downloads"))
    c1, c2, c3 = st.columns(3)
    xlsx = build_excel(p)
    c1.download_button(t("dl_excel"), xlsx, f"HCM_Countermeasures_{stamp}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/table:",
                       width="stretch", on_click="ignore")
    pdf_download(c2, t("dl_pdf"), lambda rid, by: build_executive_pdf(p, rid, by),
                 f"HCM_Countermeasure_Action_Plan_{stamp}.pdf", "adm_plan_pdf",
                 store=ctx.store, user=ctx.user, kind="action plan")
    c3.download_button(t("dl_csv"), status_csv(p), f"HCM_Countermeasure_records_{stamp}.csv", "text/csv",
                       icon=":material/download:", width="stretch", on_click="ignore")
    section(t("publish"))
    note(t("publish_help"))
    if st.button(t("publish_btn"), icon=":material/cloud_upload:"):
        pdf = build_executive_pdf(p, new_report_id(), f"{ctx.user.name} ({ctx.user.username})")
        try:
            with st.spinner(t("saving")):
                ctx.store.write(f"reports/{stamp}_HCM_Countermeasures.xlsx", xlsx, f"[app] reporte Excel · por {ctx.user.username}")
                ctx.store.write(f"reports/{stamp}_HCM_Action_Plan.pdf", pdf, f"[app] reporte PDF · por {ctx.user.username}")
            st.success(t("published", where=f"reports/{stamp}_…"))
        except StorageError as exc:
            st.error(f"{t('save_failed')} {exc}")


def print_register(ctx: Ctx) -> None:
    """Registro de impresión: cada PDF descargado con su ID, quién y cuándo."""
    t, p = ctx.t, ctx.project
    section(t("print_register"))
    note(esc(t("print_register_help")))
    log = p.log[p.log.kind == "report"]
    if log.empty:
        st.caption(t("no_prints"))
        return
    tz = p.settings.get("timezone", "UTC")
    ids = log.change.str.extract(r"ID (\S+)")[0].fillna("")
    kinds = log.change.str.extract(r"printed (.+?) PDF")[0].fillna("")
    st.dataframe(pd.DataFrame({
        "id": ids, "ts": log.ts.map(lambda x: fmt_ts(x, tz)),
        "user": log.user.map(lambda u: t("public_user") if u == PUBLIC_USER else f"{user_name(ctx, u)} ({u})"),
        "report": kinds, "fleet": log.fleet}), hide_index=True, width="stretch", height=min(40 + 35 * len(log), 420),
        column_config={"id": t("report_id"), "ts": t("when"), "user": t("who"), "report": t("report_type"),
                       "fleet": t("truck")})


# ─── Configuración ────────────────────────────────────────────────────────
def settings(ctx: Ctx) -> None:
    t, p = ctx.t, ctx.project
    s = p.settings
    section(t("settings"))
    with st.form("settings"):
        c1, c2 = st.columns(2)
        tz = c1.text_input(t("set_tz"), s.get("timezone", "Africa/Lusaka"), help=t("set_tz_help"))
        soon = c2.number_input(t("set_due_soon"), 1, 365, int(s.get("due_soon_days", 45)), help=t("set_due_soon_help"))
        if st.form_submit_button(t("save_settings"), type="primary", icon=":material/save:"):
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(tz.strip())
            except Exception:
                st.error(t("err_settings", items=t("set_tz")))
            else:
                values = {"timezone": tz.strip(), "due_soon_days": int(soon)}
                if safe_write(ctx, lambda: write_event(ctx.store, "settings", {"values": values}, ctx.user.username),
                              t("settings_saved")):
                    st.rerun()
    st.caption(t("data_location", where=ctx.store.label))
    if ctx.user.is_admin:
        section(t("change_password"))
        password_form(ctx, "adm_pw")
    st.caption(f"{config.PROJECT_NAME} · {config.FLEET}")
