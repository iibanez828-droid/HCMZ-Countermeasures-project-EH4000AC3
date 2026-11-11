"""Reporte ejecutivo en PDF con membrete LANDCROS: resumen de la flota,
alertas y avance de cada contramedida (equivalente al plan de acción
«HCM Counter Measure Tasklist – Action Plan»)."""

from __future__ import annotations

from datetime import date

from fpdf import FPDF

from core import config
from core.i18n import translator
from core.project import Project

t = translator("en")

BLACK = (26, 26, 26)
ORANGE = (255, 107, 0)
GREY = (136, 136, 136)
LIGHT = (247, 247, 247)
LINE = (221, 221, 221)
WHITE = (255, 255, 255)
BAR_BASE = (226, 226, 226)
STATUS_RGB = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in config.STATUS_COLORS.items()}

MARGIN = 12


def _fd(d: date | None) -> str:
    return d.strftime("%d-%b-%y") if isinstance(d, date) else "-"


def _txt(text: object) -> str:
    """Las fuentes estándar del PDF solo admiten latin-1."""
    return str(text).replace("→", "->").replace("·", "-").replace("–", "-").encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def __init__(self, today: date) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.today = today
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
        self.cell(self.w - 90 - MARGIN, 7, "HCM COUNTERMEASURE ACTION PLAN", align="R")
        self.set_xy(90, 14)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(170, 170, 170)
        self.cell(self.w - 90 - MARGIN, 5, _txt(f"{config.PROJECT_NAME.upper()} - {config.FLEET} - {_fd(self.today).upper()}"),
                  align="R")
        self.set_y(34)

    def footer(self) -> None:
        self.set_y(-11)
        self.set_draw_color(*LINE)
        self.line(MARGIN, self.get_y() - 1, self.w - MARGIN, self.get_y() - 1)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GREY)
        self.cell(self.content_w / 2, 5, _txt(f"LANDCROS - {config.PROJECT_NAME}"))
        self.cell(self.content_w / 2, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    def section(self, title: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*BLACK)
        self.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*ORANGE)
        self.rect(MARGIN, self.get_y(), self.content_w, 0.6, "F")
        self.ln(2.5)

    def kpis(self, items: list[tuple[str, str, str]]) -> None:
        w = (self.content_w - 3 * (len(items) - 1)) / len(items)
        y = self.get_y()
        for i, (label, value, sub) in enumerate(items):
            x = MARGIN + i * (w + 3)
            self.set_fill_color(*LIGHT)
            self.rect(x, y, w, 20, "F")
            self.set_fill_color(*ORANGE)
            self.rect(x, y, 1.2, 20, "F")
            self.set_xy(x + 4, y + 2)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*GREY)
            self.cell(w - 6, 4, label.upper())
            self.set_xy(x + 4, y + 6.5)
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(*BLACK)
            self.cell(w - 6, 8, _txt(value))
            self.set_xy(x + 4, y + 14.5)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GREY)
            self.cell(w - 6, 4, _txt(sub))
        self.set_y(y + 24)


def build_executive_pdf(p: Project) -> bytes:
    k = p.kpis()
    pdf = _Report(p.today)
    pdf.alias_nb_pages()
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
        pdf.set_fill_color(*STATUS_RGB["done" if c.status == "done" else "overdue" if c.status == "overdue" else "in_progress"])
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
