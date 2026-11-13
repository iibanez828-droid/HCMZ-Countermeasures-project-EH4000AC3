"""Diagramas de Gantt de la vista pública.

- Flota: una barra por contramedida, desde su primera fecha planificada/ejecutada
  hasta la fecha meta. La parte rellena es el % de la flota ejecutado.
- Camión: una barra por contramedida aplicable a ese camión, en la misma
  ventana; la parte rellena es el avance de ese camión. Marcas: ○ fecha
  planificada, ◆ fecha de ejecución. Encima va un tablero con su resumen.

Los colores son los mismos que la barra de avance del reporte PDF (verde
terminada, rojo vencida, naranja en curso). La línea vertical marca hoy.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config
from core.executive_report import build_truck_pdf
from core.project import (Project, fmt_hours, forecast, trucks_phrase, last_update, timeline, truck_downtime, truck_scoreboard,
                          truck_timeline)
from ui.common import T, esc, fmt_date, fmt_pct, fmt_ts, kpi_cards, pdf_download, user_name_plain

ROW_PX = 30
DAY_MS = 86_400_000


def _ms(days: int) -> int:
    return days * DAY_MS


def _grey(text: str) -> None:
    st.markdown(f'<div style="color:#AAAAAA;font-size:.78rem;margin-top:-6px">{esc(text)}</div>',
                unsafe_allow_html=True)


def _bars(p: Project, t: T, tl: pd.DataFrame, hover: list[str], end_text: list[str],
          text_colors: list[str] | None = None) -> go.Figure:
    """Barras grises (inicio → meta) con la parte rellena en color, % al final y línea de hoy."""
    labels = tl.label.tolist()
    starts = [d.isoformat() for d in tl.start]
    fig = go.Figure()
    fig.add_bar(y=labels, base=starts, x=[_ms((e - s).days) for s, e in zip(tl.start, tl.end)], orientation="h",
                marker=dict(color=config.BAR_BASE), hovertext=hover, hoverinfo="text", showlegend=False)
    fig.add_bar(y=labels, base=starts, x=[_ms((f - s).days) for s, f in zip(tl.start, tl.fill_end)], orientation="h",
                marker=dict(color=tl.color.tolist()), hovertext=hover, hoverinfo="text", showlegend=False)
    fig.add_scatter(y=labels, x=[(e + timedelta(days=6)).isoformat() for e in tl.end], mode="text", text=end_text,
                    textposition="middle right", textfont=dict(size=12, color=text_colors or config.BLACK),
                    hoverinfo="skip", showlegend=False)
    today = p.today.isoformat()
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper",
                  line=dict(color=config.BLACK, width=1.5, dash="dot"))
    fig.add_annotation(x=today, y=0, yref="paper", yanchor="top", text=f"{t('today')} {fmt_date(p.today)}",
                       showarrow=False, font=dict(size=11, color=config.BLACK))
    x0 = min(tl.start) - timedelta(days=20)
    x1 = max(max(tl.end), p.today) + timedelta(days=90)
    fig.update_layout(
        barmode="overlay", bargap=0.35, height=ROW_PX * len(tl) + 90,
        margin=dict(l=10, r=10, t=30, b=34), plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        font=dict(family="Barlow, sans-serif", color=config.BLACK),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        xaxis=dict(type="date", range=[x0.isoformat(), x1.isoformat()], showgrid=True, gridcolor="#EFEFEF",
                   tickformat="%b-%y", side="top"),
        yaxis=dict(autorange="reversed", automargin=True, ticks="", tickfont=dict(size=12)),
    )
    return fig


# ─── Flota ────────────────────────────────────────────────────────────────
def gantt_figure(p: Project, t: T) -> go.Figure:
    tl = timeline(p)
    hover = [
        f"<b>{esc(r.label)}</b><br>{t('gantt_start')}: {fmt_date(r.start)}<br>"
        f"{t('target')}: {fmt_date(r.end) if r.has_target else t('cst_no_target')}<br>"
        f"{t('executed')}: {r.executed} / {r.n} · {r.pct:.0%}<br>{t('status')}: {t('cst_' + r.status)}<br>"
        f"{t('wh_hours')}: {fmt_hours(r.hours) + ' h' if r.hours == r.hours and r.hours is not None else '—'} · "
        f"{t('wh_remaining')}: {fmt_hours(r.remaining_h)} h"
        for r in tl.itertuples()
    ]
    end_text = [f"<b>{pct:.0%}</b>" + ("" if has else f" · {t('cst_no_target')}")
                + (f" · {t('h_left', h=fmt_hours(rh))}" if rh > 0 else "")
                for pct, has, rh in zip(tl.pct, tl.has_target, tl.remaining_h)]
    return _bars(p, t, tl, hover, end_text)


def forecast_cards(p: Project, t: T) -> None:
    """Tablero del Gantt de la flota: horas pendientes, tiempo al 100 % y fecha estimada."""
    f = forecast(p)
    sub = t("fc_remaining_sub", jobs=f["pending_jobs"], trucks=f["trucks_pending"])
    if f["no_estimate_jobs"]:
        sub += " · " + t("fc_missing", n=f["no_estimate_jobs"])
    kpi_cards([
        (t("fc_remaining"), f"{fmt_hours(f['remaining_h'])} h", sub, ""),
        (t("fc_days"), t("fc_days_val", d=f["days"]),
         t("fc_days_sub", hpd=fmt_hours(f["hours_per_day"]), par=fmt_hours(f["parallel"])), "blue"),
        (t("fc_finish"), fmt_date(f["finish"]), t("fc_finish_sub", trucks=trucks_phrase(f["parallel"]), n=fmt_hours(f["parallel"])), "green"),
    ])


def gantt_view(p: Project, t: T, key: str) -> None:
    if p.cms.empty:
        st.info(t("no_data"))
        return
    forecast_cards(p, t)
    st.plotly_chart(gantt_figure(p, t), width="stretch", key=key, config={"displayModeBar": False})
    updated = last_update(p)
    when = fmt_ts(updated, p.settings.get("timezone", "UTC")) if updated else "—"
    _grey(f'{t("gantt_updated", when=when)} · {t("gantt_help")}')


# ─── Camión ───────────────────────────────────────────────────────────────
def truck_gantt_figure(p: Project, t: T, fleet: str) -> go.Figure:
    tl = truck_timeline(p, fleet)
    yes, no = "✓", "—"
    hover = [
        f"<b>{fleet} · {esc(r.label)}</b><br>{t('status')}: {t('st_' + r.status)}<br>"
        f"{t('steps_short')}: {r.steps_done}/{r.steps_n} · {t('progress')}: {r.progress:.0%}<br>"
        f"{t('planned_date')}: {fmt_date(r.planned_date)} · {t('exec_date')}: {fmt_date(r.exec_date)}<br>"
        f"{t('work_order')}: {esc(r.work_order or '—')} · FIR: {yes if r.fir else no} · "
        f"{t('report')}: {yes if r.report else no}<br>"
        f"{t('target')}: {fmt_date(r.target) if r.has_target else t('cst_no_target')}<br>"
        f"{t('wh_hours')}: {fmt_hours(r.hours) + ' h' if r.hours is not None else '—'} · "
        f"{t('wh_remaining')}: {fmt_hours(r.remaining_h)} h"
        for r in tl.itertuples()
    ]
    end_text = [f"<b>{pr:.0%}</b> · {t('st_' + s)}" + (f" · {t('cst_overdue')}" if b == "overdue" else "")
                + (f" · {t('h_left', h=fmt_hours(rh))}" if rh > 0 else "")
                for pr, s, b, rh in zip(tl.progress, tl.status, tl.bar_status, tl.remaining_h)]
    # Vencido sin ejecutar: texto en rojo (se ve aunque el avance sea 0 %)
    text_colors = [config.STATUS_COLORS["overdue"] if b == "overdue" else config.BLACK for b in tl.bar_status]
    fig = _bars(p, t, tl, hover, end_text, text_colors)
    # Marcas: ○ fecha planificada, ◆ fecha de ejecución
    for col, symbol, name in (("planned_date", "circle-open", t("planned_date")), ("exec_date", "diamond", t("exec_date"))):
        sel = tl[tl[col].map(lambda d: isinstance(d, date))]
        if not sel.empty:
            fig.add_scatter(y=sel.label, x=[d.isoformat() for d in sel[col]], mode="markers", name=name,
                            marker=dict(symbol=symbol, size=11, color=config.BLACK, line=dict(width=2, color=config.BLACK)),
                            hovertemplate=f"{name}: %{{x|%d-%b-%Y}}<extra></extra>", showlegend=False)
    x0 = min([*tl.start, *[d for d in [*tl.planned_date, *tl.exec_date] if isinstance(d, date)]]) - timedelta(days=20)
    x1 = max(max(tl.end), p.today) + timedelta(days=210)  # espacio para «100% · Closed out»
    fig.update_xaxes(range=[x0.isoformat(), x1.isoformat()])
    return fig


def scoreboard(p: Project, t: T, fleet: str) -> dict:
    s = truck_scoreboard(p, fleet)
    nxt = f"{fmt_date(s['next_date'])}" if s["next_date"] else "—"
    kpi_cards([
        (t("sb_executed"), f"{s['executed']} / {s['n']}",
         t("sb_executed_sub", e=s["executed"], n=s["n"], na=s["na"]), ""),
        (t("sb_closed"), str(s["closed"]), t("sb_closed_sub", c=s["closed"], d=s["docs_open"]), "green"),
        (t("sb_pending"), str(s["pending"]),
         t("sb_pending_sub", ip=s["in_progress"], ns=s["not_started"], late=s["late"]), "red" if s["late"] else ""),
        (t("sb_progress"), fmt_pct(s["progress"]), f"{t('kpi_executed')}: {fmt_pct(s['pct'])}", "blue"),
        (t("sb_next"), nxt, s["next_cm"] or t("sb_next_none"), ""),
    ])
    d = truck_downtime(p, fleet)
    sub = t("sb_downtime_sub", d=fmt_hours(round(d["days"], 1)), hpd=fmt_hours(d["hours_per_day"]))
    if d["no_estimate"]:
        sub += " · " + t("fc_missing", n=d["no_estimate"])
    kpi_cards([(t("sb_downtime"), t("sb_downtime_val", h=fmt_hours(d["hours"])), sub, "red" if d["hours"] else "green")])
    return s


def truck_detail_table(p: Project, t: T, fleet: str, key: str) -> None:
    tl = truck_timeline(p, fleet)
    df = pd.DataFrame({
        t("countermeasure"): tl.label,
        t("status"): tl.status.map(lambda s: t("st_" + s)),
        t("steps_short"): [f"{d}/{n}" for d, n in zip(tl.steps_done, tl.steps_n)],
        t("progress"): tl.progress * 100,
        t("planned_date"): tl.planned_date,
        t("exec_date"): tl.exec_date,
        t("work_order"): tl.work_order,
        t("fir"): tl.fir,
        t("report"): tl.report,
        t("target"): tl.target,
        t("wh_hours"): tl.hours,
        t("wh_remaining"): tl.remaining_h.round(1),
        t("note"): tl.note,
    })
    st.dataframe(df, hide_index=True, width="stretch", key=key, column_config={
        t("progress"): st.column_config.ProgressColumn(t("progress"), format="%.0f%%", min_value=0, max_value=100),
        t("planned_date"): st.column_config.DateColumn(t("planned_date"), format="DD-MMM-YY"),
        t("exec_date"): st.column_config.DateColumn(t("exec_date"), format="DD-MMM-YY"),
        t("target"): st.column_config.DateColumn(t("target"), format="DD-MMM-YY"),
        t("fir"): st.column_config.CheckboxColumn(t("fir")),
        t("report"): st.column_config.CheckboxColumn(t("report")),
        t("wh_hours"): st.column_config.NumberColumn(t("wh_hours"), format="%.1f h"),
        t("wh_remaining"): st.column_config.NumberColumn(t("wh_remaining"), format="%.1f h"),
    })


def truck_view(p: Project, t: T, key: str, users: dict | None = None, store=None, user=None) -> None:
    fleets = p.fleets()
    if not fleets:
        st.info(t("no_data"))
        return
    tr = p.trucks.set_index("fleet")
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    fleet = c1.selectbox(t("pick_truck"), fleets, key=f"{key}_pick",
                         format_func=lambda f: f"{f} · {tr.at[f, 'model'] or '—'} · {tr.at[f, 'serial'] or '—'}")
    if store is not None:
        pdf_download(c2, t("dl_truck_pdf"), lambda rid, by: build_truck_pdf(p, fleet, users, rid, by),
                     f"HCM_Truck_Report_{fleet}_{p.today:%Y%m%d}.pdf", f"{key}_pdf_{fleet}",
                     store=store, user=user, kind="truck report", fleet=fleet, printed_by_public=t("public_user"))
    s = scoreboard(p, t, fleet)
    if s["n"] == 0:
        st.info(t("no_truck_cms"))
        return
    st.plotly_chart(truck_gantt_figure(p, t, fleet), width="stretch", key=f"{key}_gantt",
                    config={"displayModeBar": False})
    when = fmt_ts(s["last_ts"], p.settings.get("timezone", "UTC")) if s["last_ts"] else "—"
    who = user_name_plain(users or {}, s["last_user"]) if s["last_user"] else "—"
    _grey(f'{t("truck_updated", fleet=fleet, when=when, who=who)} · {t("truck_gantt_help")}')
    truck_detail_table(p, t, fleet, f"{key}_table")
