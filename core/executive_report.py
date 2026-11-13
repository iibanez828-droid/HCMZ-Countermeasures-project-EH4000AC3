"""Reportes en PDF con membrete LANDCROS.

- Plan de acción (build_executive_pdf): página 1 = Gantt de la flota con el
  pronóstico de horas; después el resumen, la lista de contramedidas
  («HCM Counter Measure Tasklist – Action Plan») y las alertas.
- Reporte de un camión (build_truck_pdf): tablero, Gantt del camión y detalle.

Los Gantt se dibujan directamente en el PDF (sin imágenes), con los mismos
colores que la app: verde terminado, rojo vencido, naranja en curso.
"""

from __future__ import annotations

from datetime import date, timedelta

from fpdf import FPDF

from core import config
from core.i18n import translator
from core.project import (Project, fmt_hours, forecast, trucks_phrase, last_update, timeline, truck_downtime, truck_scoreboard,
                          truck_timeline)

t = translator("en")

BLACK = (26, 26, 26)
ORANGE = (255, 107, 0)
GREY = (136, 136, 136)
LIGHT = (247, 247, 247)
LINE = (221, 221, 221)
WHITE = (255, 255, 255)
BAR_BASE = (226, 226, 226)
GRID = (236, 236, 236)
RED = (198, 40, 40)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


STATUS_RGB = {k: _rgb(v) for k, v in config.STATUS_COLORS.items()}

MARGIN = 12


def _fd(d: date | None) -> str:
    return d.strftime("%d-%b-%y") if isinstance(d, date) else "-"


def _txt(text: object) -> str:
    """Las fuentes estándar del PDF solo admiten latin-1."""
    return str(text).replace("→", "->").replace("·", "-").replace("–", "-").encode("latin-1", "replace").decode("latin-1")


def _ts(ts: str, tz: str) -> str:
    """Fecha-hora UTC guardada → hora local del proyecto."""
    if not ts:
        return "-"
    try:
        import pandas as pd
        return pd.Timestamp(ts).tz_convert(tz).strftime("%d-%b-%Y %H:%M")
    except Exception:
        return ts[:16].replace("T", " ")


class _Report(FPDF):
    def __init__(self, today: date, title: str = "HCM COUNTERMEASURE ACTION PLAN", subtitle: str = "",
                 report_id: str = "", printed_by: str = "") -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.today = today
        self.report_id = report_id
        self.printed_by = printed_by
        self.report_title = title
        self.report_subtitle = subtitle or f"{config.PROJECT_NAME.upper()} - {config.FLEET} - {_fd(today).upper()}"
        self.content_w = self.w - 2 * MARGIN
        self.set_margins(MARGIN, 36, MARGIN)
        self.set_auto_page_break(True, margin=16)
        self.set_title(f"{config.PROJECT_NAME} - Action plan {today.isoformat()}")
        self.set_author("LANDCROS")

    def header(self) -> None:
        self.set_fill_color(*BLACK)
        self.rect(0, 0, self.w, 26, "F")
        self.set_fill_color(*ORANGE)
        self.rect(0, 26, self.w, 1.6, "F")
        if config.LOGO_PATH.exists():
            try:
                self.image(str(config.LOGO_PATH), x=MARGIN, y=7, h=12)
            except Exception:  # formato de imagen no soportado: el membrete sigue sin logo
                pass
        self.set_xy(90, 6.5)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 15)
        self.cell(self.w - 90 - MARGIN, 7, _txt(self.report_title), align="R")
        self.set_xy(90, 14)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(170, 170, 170)
        self.cell(self.w - 90 - MARGIN, 5, _txt(self.report_subtitle), align="R")
        self.set_y(34)

    def footer(self) -> None:
        self.set_y(-11)
        self.set_draw_color(*LINE)
        self.line(MARGIN, self.get_y() - 1, self.w - MARGIN, self.get_y() - 1)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GREY)
        third = self.content_w / 3
        self.cell(third, 5, _txt(f"LANDCROS - {config.PROJECT_NAME}"))
        stamp = " - ".join(x for x in (f"Report ID {self.report_id}" if self.report_id else "",
                                       f"Printed by {self.printed_by}" if self.printed_by else "") if x)
        self.cell(third, 5, _txt(stamp), align="C")
        self.cell(third, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    def section(self, title: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*BLACK)
        self.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*ORANGE)
        self.rect(MARGIN, self.get_y(), self.content_w, 0.6, "F")
        self.ln(2.5)

    def kpis(self, items: list[tuple]) -> None:
        """items: (etiqueta, valor, subtítulo[, color de acento RGB])."""
        w = (self.content_w - 3 * (len(items) - 1)) / len(items)
        y = self.get_y()
        for i, item in enumerate(items):
            label, value, sub = item[:3]
            accent = item[3] if len(item) > 3 else ORANGE
            x = MARGIN + i * (w + 3)
            self.set_fill_color(*LIGHT)
            self.rect(x, y, w, 20, "F")
            self.set_fill_color(*accent)
            self.rect(x, y, 1.2, 20, "F")
            self.set_xy(x + 4, y + 2)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*GREY)
            self.cell(w - 6, 4, _txt(label.upper()))
            self.set_xy(x + 4, y + 6.5)
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(*BLACK)
            self.cell(w - 6, 8, _txt(value))
            self.set_xy(x + 4, y + 14.5)
            size = 7.0
            self.set_font("Helvetica", "", size)
            while self.get_string_width(_txt(sub)) > w - 6 and size > 5.2:
                size -= 0.2
                self.set_font("Helvetica", "", size)
            self.set_text_color(*GREY)
            self.cell(w - 6, 4, _txt(sub))
        self.set_y(y + 24)

    def grey_note(self, text: str) -> None:
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY)
        self.multi_cell(0, 3.6, _txt(text), new_x="LMARGIN", new_y="NEXT")


# ─── Diagrama de Gantt dibujado en el PDF ─────────────────────────────────
def _months(x0: date, x1: date) -> list[date]:
    """Inicios de mes para las marcas del eje (como máximo ~12)."""
    span = (x1.year - x0.year) * 12 + x1.month - x0.month
    step = next(s for s in (1, 2, 3, 6, 12) if span / s <= 12)
    d = date(x0.year, x0.month, 1)
    out = []
    while d <= x1:
        if d >= x0 and (d.month - 1) % step == 0:
            out.append(d)
        d = date(d.year + (d.month // 12), d.month % 12 + 1, 1)
    return out


def draw_gantt(pdf: _Report, rows: list[dict], today: date, bottom: float, label_w: float = 72,
               text_w: float = 48, legend: list[tuple] | None = None) -> None:
    """rows: label, start, end, fill_end, color (hex), end_text, text_rgb y markers [(fecha, 'circle'|'diamond')].

    Dibuja desde la posición actual hasta `bottom`: etiquetas, barras grises
    (inicio → meta) con la parte rellena en color, texto al final, marcas,
    cuadrícula mensual, línea de hoy y leyenda."""
    if not rows:
        return
    dates = [d for r in rows for d in (r["start"], r["end"], *[m for m, _ in r.get("markers", [])])]
    x0d = min(min(dates), today) - timedelta(days=15)
    x1d = max(max(dates), today) + timedelta(days=15)
    left = MARGIN + label_w
    width = pdf.content_w - label_w - text_w
    days = max((x1d - x0d).days, 1)

    def X(d: date) -> float:
        return left + width * (d - x0d).days / days

    top = pdf.get_y() + 5
    legend_h = 7 if legend else 0
    row_h = max(min((bottom - top - 6 - legend_h) / len(rows), 7.0), 3.4)
    chart_bottom = top + row_h * len(rows)
    bar_h = row_h * 0.58

    # cuadrícula y eje de meses
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*GREY)
    pdf.set_draw_color(*GRID)
    pdf.set_line_width(0.2)
    for m in _months(x0d, x1d):
        x = X(m)
        pdf.line(x, top, x, chart_bottom)
        pdf.set_xy(x - 8, top - 4.5)
        pdf.cell(16, 3.5, m.strftime("%b-%y"), align="C")

    for i, r in enumerate(rows):
        y = top + i * row_h
        if i % 2 == 0:
            pdf.set_fill_color(251, 251, 251)
            pdf.rect(MARGIN, y, pdf.content_w, row_h, "F")
        yb = y + (row_h - bar_h) / 2
        # etiqueta
        pdf.set_font("Helvetica", "", 6.8 if row_h < 5 else 7.5)
        pdf.set_text_color(*BLACK)
        pdf.set_xy(MARGIN, y)
        label = _txt(r["label"])
        while pdf.get_string_width(label) > label_w - 3 and len(label) > 4:
            label = label[:-2]
        pdf.cell(label_w - 2, row_h, label if label == _txt(r["label"]) else label.rstrip() + "...", align="R")
        # barras
        xs, xe, xf = X(r["start"]), X(r["end"]), X(r["fill_end"])
        pdf.set_fill_color(*BAR_BASE)
        pdf.rect(xs, yb, max(xe - xs, 0.4), bar_h, "F")
        if xf > xs:
            pdf.set_fill_color(*_rgb(r["color"]))
            pdf.rect(xs, yb, xf - xs, bar_h, "F")
        # marcas: ○ planificado, ◆ ejecutado
        for d, kind in r.get("markers", []):
            cx, cy, rad = X(d), y + row_h / 2, min(bar_h * 0.55, 1.6)
            pdf.set_draw_color(*BLACK)
            pdf.set_fill_color(*BLACK)
            if kind == "diamond":
                pdf.polygon([(cx, cy - rad), (cx + rad, cy), (cx, cy + rad), (cx - rad, cy)], style="F")
            else:
                pdf.set_line_width(0.35)
                pdf.set_fill_color(*WHITE)
                pdf.ellipse(cx - rad, cy - rad, 2 * rad, 2 * rad, style="DF")
                pdf.set_line_width(0.2)
        # texto al final de la barra
        pdf.set_xy(xe + 1.2, y)
        pdf.set_font("Helvetica", "B", 6.8 if row_h < 5 else 7.5)
        pdf.set_text_color(*r.get("text_rgb", BLACK))
        pdf.cell(text_w + width - (xe - left) - 1, row_h, _txt(r["end_text"]))

    # hoy (línea punteada)
    xt = X(today)
    pdf.set_draw_color(*BLACK)
    pdf.set_line_width(0.3)
    pdf.set_dash_pattern(dash=0.8, gap=0.8)
    pdf.line(xt, top - 1, xt, chart_bottom + 1)
    pdf.set_dash_pattern()
    pdf.set_line_width(0.2)
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(*BLACK)
    pdf.set_xy(xt - 15, chart_bottom + 1)
    pdf.cell(30, 3.5, f"Today {_fd(today)}", align="C")
    pdf.set_y(chart_bottom + 5)

    if legend:
        x = MARGIN
        y = pdf.get_y() + 0.5
        pdf.set_font("Helvetica", "", 7)
        for item, text in legend:
            if item == "circle":
                pdf.set_draw_color(*BLACK)
                pdf.set_fill_color(*WHITE)
                pdf.set_line_width(0.35)
                pdf.ellipse(x, y + 0.4, 2.6, 2.6, style="DF")
                pdf.set_line_width(0.2)
            elif item == "diamond":
                pdf.set_fill_color(*BLACK)
                pdf.polygon([(x + 1.3, y), (x + 2.6, y + 1.7), (x + 1.3, y + 3.4), (x, y + 1.7)], style="F")
            else:
                pdf.set_fill_color(*item)
                pdf.rect(x, y + 0.3, 5, 2.8, "F")
            pdf.set_xy(x + 6.5, y)
            pdf.set_text_color(*BLACK)
            pdf.cell(pdf.get_string_width(_txt(text)) + 2, 3.5, _txt(text))
            x = pdf.get_x() + 5
        pdf.set_y(y + 5)


def _fleet_gantt_page(pdf: _Report, p: Project) -> None:
    """Página 1 del plan de acción: pronóstico de horas y Gantt de la flota."""
    k, f = p.kpis(), forecast(p)
    pdf.section("Countermeasure timeline (Gantt)")
    missing = f" - {f['no_estimate_jobs']} truck-jobs without hours" if f["no_estimate_jobs"] else ""
    pdf.kpis([
        ("Fleet executed", f"{k['pct'] * 100:.0f}%", f"{k['executed']} of {k['n']} truck-jobs"),
        ("Remaining work", f"{fmt_hours(f['remaining_h'])} h",
         f"{f['pending_jobs']} truck-jobs on {f['trucks_pending']} trucks{missing}"),
        ("Time to 100%", f"{f['days']} days",
         f"At {fmt_hours(f['hours_per_day'])} h/day x {fmt_hours(f['parallel'])} truck(s) in parallel", _rgb("#1565C0")),
        ("Estimated completion", _fd(f["finish"]),
         f"Continuous work on {trucks_phrase(f['parallel'])} in parallel, without any delays", _rgb("#2E7D32")),
    ])
    tl = timeline(p)
    rows = [{"label": r.label, "start": r.start, "end": r.end, "fill_end": r.fill_end, "color": r.color,
             "end_text": f"{r.pct * 100:.0f}%" + ("" if r.has_target else " - No target")
                         + (f" - {fmt_hours(r.remaining_h)} h left" if r.remaining_h > 0 else "")}
            for r in tl.itertuples()]
    draw_gantt(pdf, rows, p.today, bottom=pdf.h - 24,
               legend=[(_rgb(config.STATUS_COLORS["done"]), "Done (fleet 100%)"),
                       (_rgb(config.STATUS_COLORS["overdue"]), "Overdue (target passed)"),
                       (_rgb(config.STATUS_COLORS["in_progress"]), "In progress"),
                       (BAR_BASE, "Remaining to the fleet target")])
    updated = last_update(p)
    pdf.grey_note(f"Last update: {_ts(updated, p.settings.get('timezone', 'UTC')) if updated else '-'}. "
                  "Each bar runs from the first planned or executed date to the fleet target; the filled part is "
                  "the % of the fleet executed. Hours left = estimated hours per truck x trucks not executed yet.")


def build_executive_pdf(p: Project, report_id: str = "", printed_by: str = "") -> bytes:
    k = p.kpis()
    pdf = _Report(p.today, report_id=report_id, printed_by=printed_by)
    pdf.alias_nb_pages()
    pdf.add_page()
    _fleet_gantt_page(pdf, p)
    pdf.add_page()
    pdf.kpis([
        ("Fleet executed", f"{k['pct'] * 100:.0f}%", f"{k['executed']} of {k['n']} truck-jobs"),
        ("Fully closed out", f"{k['close_pct'] * 100:.0f}%", "FIR uploaded and report filed"),
        ("Countermeasures done", f"{k['cms_done']} / {k['cms']}", "Every applicable truck executed"),
        ("Past target date", str(k["cms_overdue"]), "Target passed, fleet not finished"),
    ])

    pdf.section("Countermeasure task list")
    cols = [("No.", 9), ("Issue / task", 70), ("Responsible", 34), ("Duration", 20), ("Target", 20),
            ("Executed", 22), ("Fleet %", 48), ("Status", 28)]
    scale = pdf.content_w / sum(w for _, w in cols)
    cols = [(n, w * scale) for n, w in cols]
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(*BLACK)
    pdf.set_text_color(*WHITE)
    for name, w in cols:
        pdf.cell(w, 6, name.upper(), fill=True)
    pdf.ln()
    for _, c in p.cms.iterrows():
        if pdf.get_y() > pdf.h - 24:
            pdf.add_page()
        y = pdf.get_y()
        pdf.set_text_color(*BLACK)
        pdf.set_font("Helvetica", "", 8)
        vals = [str(c.order), c["name"], c.owner or "-", c.duration or "-", _fd(c.target), f"{c.executed}/{c.n}"]
        for (_, w), v in zip(cols[:6], vals):
            pdf.cell(w, 7, _txt(v)[:60])
        # barra de avance
        bw = cols[6][1] - 14
        x = pdf.get_x()
        pdf.set_fill_color(*BAR_BASE)
        pdf.rect(x, y + 2.2, bw, 2.6, "F")
        pdf.set_fill_color(*_rgb(config.progress_color(c.status)))
        pdf.rect(x, y + 2.2, bw * c.pct, 2.6, "F")
        pdf.set_x(x + bw + 1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(13, 7, f"{c.pct * 100:.0f}%")
        pdf.set_fill_color(*STATUS_RGB[c.status])
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.cell(cols[7][1] - 2, 5, t("cst_" + c.status).upper(), fill=True, align="C")
        pdf.set_y(y + 7)
        pdf.set_draw_color(*LINE)
        pdf.line(MARGIN, y + 7, MARGIN + pdf.content_w, y + 7)

    alerts = p.alerts()
    if alerts:
        pdf.section("Alerts")
        pdf.set_font("Helvetica", "", 8.5)
        names = dict(zip(p.cms.cm_id, p.cms["name"]))
        for a in alerts:
            pdf.set_text_color(*STATUS_RGB["overdue" if a["type"] in ("overdue", "planned_missed") else "in_progress"])
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.cell(60, 5, _txt(names.get(a["cm"], a["cm"]))[:40])
            pdf.set_text_color(*BLACK)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.multi_cell(0, 5, _txt(alert_text(t, a)), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def alert_text(t, a: dict) -> str:
    if a["type"] == "overdue":
        return t("alert_overdue", days=a["days"], left=a["left"])
    if a["type"] == "due_soon":
        return t("alert_due_soon", days=a["days"], left=a["left"])
    fleets = ", ".join(a["fleets"][:12]) + (f" +{len(a['fleets']) - 12}" if len(a["fleets"]) > 12 else "")
    if a["type"] == "planned_missed":
        return t("alert_planned_missed", n=len(a["fleets"]), fleets=fleets)
    return t("alert_docs_pending", n=len(a["fleets"]), fleets=fleets)


# ─── Reporte de un camión ────────────────────────────────────────────────
def build_truck_pdf(p: Project, fleet: str, users: dict | None = None, report_id: str = "",
                    printed_by: str = "") -> bytes:
    """Tablero, Gantt y detalle de las contramedidas de un camión."""
    s = truck_scoreboard(p, fleet)
    d = truck_downtime(p, fleet)
    pdf = _Report(p.today, title=f"TRUCK REPORT - {fleet}",
                  subtitle=f"{config.PROJECT_NAME.upper()} - {fleet} - {s['model'] or '-'} - SERIAL "
                           f"{s['serial'] or '-'} - {_fd(p.today).upper()}",
                  report_id=report_id, printed_by=printed_by)
    pdf.set_title(f"{config.PROJECT_NAME} - Truck {fleet} {p.today.isoformat()}")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.section(f"{fleet} - countermeasures applied")
    pdf.kpis([
        ("Executed", f"{s['executed']} / {s['n']}", f"of applicable - {s['na']} N/A"),
        ("Closed out", str(s["closed"]), f"FIR + report - {s['docs_open']} docs open", _rgb("#2E7D32")),
        ("Pending", str(s["pending"]) + (f"  ({s['late']} overdue)" if s["late"] else ""),
         f"{s['in_progress']} in progress - {s['not_started']} not started", RED if s["late"] else ORANGE),
        ("Step progress", f"{s['progress'] * 100:.0f}%", f"Fleet-executed: {s['pct'] * 100:.0f}%", _rgb("#1565C0")),
        ("Next planned", _fd(s["next_date"]) if s["next_date"] else "-", s["next_cm"][:34] or "Nothing planned ahead"),
        ("Est. downtime", f"{fmt_hours(d['hours'])} h",
         f"~{d['days']:.1f} days at {fmt_hours(d['hours_per_day'])} h/day", RED if d["hours"] else _rgb("#2E7D32")),
    ])
    tl = truck_timeline(p, fleet)
    if tl.empty:
        pdf.grey_note("No countermeasures apply to this truck.")
        return bytes(pdf.output())
    status_txt = {k2: t("st_" + k2) for k2 in config.RECORD_STATUSES}
    rows = []
    for r in tl.itertuples():
        markers = [(m, kind) for m, kind in ((r.planned_date, "circle"), (r.exec_date, "diamond")) if isinstance(m, date)]
        rows.append({"label": r.label, "start": r.start, "end": r.end, "fill_end": r.fill_end, "color": r.color,
                     "markers": markers,
                     "text_rgb": RED if r.bar_status == "overdue" else BLACK,
                     "end_text": f"{r.progress * 100:.0f}% - {status_txt[r.status]}"
                                 + (" - Overdue" if r.bar_status == "overdue" else "")
                                 + (f" - {fmt_hours(r.remaining_h)} h left" if r.remaining_h > 0 else "")})
    draw_gantt(pdf, rows, p.today, bottom=pdf.h - 24, text_w=58,
               legend=[(_rgb(config.STATUS_COLORS["done"]), "Executed"),
                       (_rgb(config.STATUS_COLORS["overdue"]), "Target passed, not executed"),
                       (_rgb(config.STATUS_COLORS["in_progress"]), "Pending"),
                       (BAR_BASE, "Countermeasure window (start -> fleet target)"),
                       ("circle", "Planned date"), ("diamond", "Execution date")])
    who = (users or {}).get(s["last_user"])
    who = who.name if who else (s["last_user"] or "-")
    when = (f"Last update for {fleet}: {_ts(s['last_ts'], p.settings.get('timezone', 'UTC'))} - {who}."
            if s["last_ts"] else f"No changes recorded in the app for {fleet} yet (status from the initial tracker).")
    pdf.grey_note(f"{when} "
                  "The filled part of each bar is this truck's progress (steps ticked / total steps).")

    # Detalle
    pdf.add_page()
    pdf.section(f"{fleet} - detail by countermeasure")
    cols = [("Countermeasure", 66), ("Status", 30), ("Steps", 13), ("Progress", 17), ("Planned", 19),
            ("Executed", 19), ("Work order", 22), ("FIR", 10), ("Report", 12), ("Target", 19), ("Hours/truck", 19),
            ("Remaining", 19)]
    scale = pdf.content_w / sum(w for _, w in cols)
    cols = [(n, w * scale) for n, w in cols]
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(*BLACK)
    pdf.set_text_color(*WHITE)
    for name, w in cols:
        pdf.cell(w, 6, name.upper(), fill=True)
    pdf.ln()
    for i, r in enumerate(tl.itertuples()):
        if pdf.get_y() > pdf.h - 24:
            pdf.add_page()
        y = pdf.get_y()
        if i % 2:
            pdf.set_fill_color(*LIGHT)
            pdf.rect(MARGIN, y, pdf.content_w, 6.5, "F")
        vals = [r.label, status_txt[r.status], f"{r.steps_done}/{r.steps_n}", f"{r.progress * 100:.0f}%",
                _fd(r.planned_date), _fd(r.exec_date), r.work_order or "-", "Yes" if r.fir else "-",
                "Yes" if r.report else "-", _fd(r.target) if r.has_target else "No target",
                f"{fmt_hours(r.hours)} h" if r.hours is not None else "-",
                f"{fmt_hours(r.remaining_h)} h" if r.remaining_h else "-"]
        for j, ((_, w), v) in enumerate(zip(cols, vals)):
            pdf.set_font("Helvetica", "B" if j == 0 else "", 7.5)
            pdf.set_text_color(*(RED if j == 1 and r.bar_status == "overdue" else BLACK))
            text = _txt(v)
            while pdf.get_string_width(text) > w - 1.5 and len(text) > 4:
                text = text[:-2]
            pdf.cell(w, 6.5, text)
        pdf.ln()
        pdf.set_draw_color(*LINE)
        pdf.line(MARGIN, y + 6.5, MARGIN + pdf.content_w, y + 6.5)
    notes = [(r.label, r.note) for r in tl.itertuples() if r.note]
    if notes:
        pdf.section("Notes")
        for label, note in notes:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*BLACK)
            pdf.cell(70, 5, _txt(label)[:45])
            pdf.set_font("Helvetica", "", 8)
            pdf.multi_cell(0, 5, _txt(note), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
