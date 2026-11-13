"""Genera el manual de usuario en PDF con el mismo membrete LANDCROS del reporte
del plan de acción (core/executive_report.py).

    python docs/manual/build_manual.py

Salida: docs/HCM_Countermeasure_App_User_Manual.pdf
Las capturas están en docs/manual/img/ (tomadas de una copia de prueba de la app).
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from core import config  # noqa: E402

IMG = HERE / "img"
OUT = ROOT / "docs" / "HCM_Countermeasure_App_User_Manual.pdf"
VERSION = "1.1"
ISSUED = date(2026, 11, 13)

BLACK = (26, 26, 26)
ORANGE = (255, 107, 0)
GREY = (136, 136, 136)
DARK = (68, 68, 68)
LIGHT = (247, 247, 247)
LINE = (221, 221, 221)
WHITE = (255, 255, 255)
TIP_BG = (255, 244, 236)
WARN_BG = (253, 236, 234)
RED = (198, 40, 40)
GREEN = (46, 125, 50)
BLUE = (21, 101, 192)
NA = (214, 214, 214)
MID = (158, 158, 158)

MARGIN = 15

_REPL = {"→": "->", "—": " - ", "–": "-", "…": "...", "≈": "~", "“": '"', "”": '"', "‘": "'", "’": "'",
         "✓": "(tick)", "◐": "(half circle)", "○": "(circle)", "◆": "(diamond)", "⋮": "(three dots)", "≥": ">="}


_ITALIC = re.compile(r"(?<![*\w])\*(?!\*)([^*\n]+?)(?<!\*)\*(?![*\w])")


def md(text: str) -> str:
    """*cursiva* → __cursiva__ (sintaxis markdown de fpdf2); «--» literal (no subrayado)."""
    return _ITALIC.sub(r"__\1__", text.replace("--", "\\--"))


def plain(text: str) -> str:
    """Sin marcas de formato (celdas de tabla)."""
    return str(text).replace("**", "").replace("*", "")


def tx(text: object) -> str:
    """Las fuentes estándar del PDF solo admiten latin-1."""
    s = str(text)
    for k, v in _REPL.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class Manual(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.content_w = self.w - 2 * MARGIN
        self.set_margins(MARGIN, 36, MARGIN)
        self.set_auto_page_break(True, margin=18)
        self.set_title(f"{config.PROJECT_NAME} - User manual")
        self.set_author("LANDCROS")
        self.cover = True
        self.fig_n = 0

    # ── Membrete (igual que el reporte del plan de acción) ──
    def header(self) -> None:
        if self.page_no() == 1:  # portada
            return
        self.set_fill_color(*BLACK)
        self.rect(0, 0, self.w, 26, "F")
        self.set_fill_color(*ORANGE)
        self.rect(0, 26, self.w, 1.6, "F")
        try:
            self.image(str(config.LOGO_PATH), x=MARGIN, y=7, h=12)
        except Exception:
            pass
        self.set_xy(70, 6.5)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 15)
        self.cell(self.w - 70 - MARGIN, 7, "APP USER MANUAL", align="R")
        self.set_xy(70, 14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(170, 170, 170)
        self.cell(self.w - 70 - MARGIN, 5, tx(f"{config.PROJECT_NAME.upper()} - VERSION {VERSION} - "
                                              f"{ISSUED:%d-%b-%Y}".upper()), align="R")
        self.set_y(34)

    def footer(self) -> None:
        if self.page_no() == 1:  # portada
            return
        self.set_y(-12)
        self.set_draw_color(*LINE)
        self.line(MARGIN, self.get_y() - 1, self.w - MARGIN, self.get_y() - 1)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GREY)
        self.cell(self.content_w / 2, 5, tx(f"LANDCROS - {config.PROJECT_NAME} - User manual"))
        self.cell(self.content_w / 2, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    # ── Bloques ──
    def need(self, h: float) -> None:
        if self.get_y() + h > self.h - 20:
            self.add_page()

    def chapter(self, title: str) -> None:
        self._flush(0)
        if self.get_y() > self.t_margin + 1:  # no dejar páginas en blanco (p. ej. justo después del índice)
            self.add_page()
        self.start_section(title, level=0)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*BLACK)
        self.cell(0, 9, tx(title.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*ORANGE)
        self.rect(MARGIN, self.get_y() + 0.5, self.content_w, 1, "F")
        self.ln(5)

    def section(self, title: str, keep: float = 22) -> None:
        """El título se imprime junto con el bloque que lo sigue (nunca queda solo al pie de la página)."""
        self._flush(0)
        self._pending = title

    def _flush(self, block_h: float) -> None:
        title = getattr(self, "_pending", None)
        if not title:
            return
        self._pending = None
        self.need(14 + max(block_h, 12))
        self.ln(2)
        self.start_section(title, level=1)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(*BLACK)
        self.cell(0, 7, tx(title.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*ORANGE)
        self.rect(MARGIN, self.get_y(), self.content_w, 0.6, "F")
        self.ln(3)

    def sub(self, title: str) -> None:
        self._flush(16)
        self.need(16)
        self.ln(1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ORANGE)
        self.cell(0, 6, tx(title), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*BLACK)

    def p(self, text: str, size: float = 9.5) -> None:
        self._flush(15)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5, tx(md(text)), markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullets(self, items: list[str], numbered: bool = False) -> None:
        self._flush(15)
        self.set_font("Helvetica", "", 9.5)
        for i, it in enumerate(items, 1):
            self.need(8)
            y = self.get_y()
            self.set_text_color(*ORANGE)
            self.set_font("Helvetica", "B", 9.5)
            self.cell(7, 5, f"{i}." if numbered else "-", align="R" if numbered else "C")
            self.set_text_color(*DARK)
            self.set_font("Helvetica", "", 9.5)
            self.set_xy(MARGIN + 9, y)
            self.multi_cell(self.content_w - 9, 5, tx(md(it)), markdown=True, new_x="LMARGIN", new_y="NEXT")
            self.ln(0.8)
        self.ln(1)

    def box(self, kind: str, text: str) -> None:
        """kind: tip | warning | example | note."""
        bg, bar, label = {"tip": (TIP_BG, ORANGE, "TIP"), "warning": (WARN_BG, RED, "IMPORTANT"),
                          "example": (LIGHT, BLUE, "EXAMPLE"), "note": (LIGHT, GREY, "NOTE")}[kind]
        self.set_font("Helvetica", "", 9)
        lines = self.multi_cell(self.content_w - 10, 4.8, tx(md(text)), markdown=True, dry_run=True, output="LINES")
        h = 4.8 * len(lines) + 10
        self._flush(h + 2)
        self.need(h + 2)
        x, y = MARGIN, self.get_y()
        self.set_fill_color(*bg)
        self.rect(x, y, self.content_w, h, "F")
        self.set_fill_color(*bar)
        self.rect(x, y, 1.4, h, "F")
        self.set_xy(x + 5, y + 2)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*bar)
        self.cell(0, 4, label, new_x="LMARGIN", new_y="NEXT")
        self.set_xy(x + 5, y + 6.5)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        self.multi_cell(self.content_w - 10, 4.8, tx(md(text)), markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.set_y(y + h + 3)

    def figure(self, name: str, caption: str, width: float | None = None, max_h: float = 200) -> None:
        path = IMG / f"{name}.jpg"
        if not path.exists():
            return
        from PIL import Image
        with Image.open(path) as im:
            ratio = im.height / im.width
        w = width or self.content_w
        h = w * ratio
        if h > max_h:
            h, w = max_h, max_h / ratio
        self._flush(h + 10)
        self.need(h + 10)
        x = MARGIN + (self.content_w - w) / 2
        y = self.get_y()
        self.set_draw_color(*LINE)
        self.image(str(path), x=x, y=y, w=w, h=h)
        self.rect(x, y, w, h)
        self.fig_n += 1
        self.set_y(y + h + 1.5)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.multi_cell(0, 4, tx(f"Figure {self.fig_n}. {caption}"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def table(self, header: list[str], rows: list[list[str]], widths: list[float],
              colors: list[tuple | None] | None = None) -> None:
        widths = [w * self.content_w / sum(widths) for w in widths]
        self._flush(20)
        self.need(14)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*BLACK)
        self.set_text_color(*WHITE)
        for h, w in zip(header, widths):
            self.cell(w, 6.5, tx(h.upper()), fill=True)
        self.ln()
        self.set_font("Helvetica", "", 8.2)
        for k, row in enumerate(rows):
            row = [plain(c) for c in row]
            heights = [len(self.multi_cell(w - 2, 4.2, tx(c), dry_run=True, output="LINES")) for c, w in zip(row, widths)]
            h = max(heights) * 4.2 + 2.2
            if self.get_y() + h > self.h - 20:
                self.add_page()
            y = self.get_y()
            if k % 2:
                self.set_fill_color(*LIGHT)
                self.rect(MARGIN, y, self.content_w, h, "F")
            x = MARGIN
            for i, (c, w) in enumerate(zip(row, widths)):
                color = colors[k] if colors and i == 0 else None
                if color:
                    self.set_fill_color(*color)
                    self.rect(x + 1, y + 1.2, w - 2, h - 2.4, "F")
                    self.set_text_color(*(BLACK if color in (NA, LIGHT) else WHITE))
                    self.set_font("Helvetica", "B", 8)
                else:
                    self.set_text_color(*DARK)
                    self.set_font("Helvetica", "B" if i == 0 else "", 8.2)
                self.set_xy(x + 1, y + 1.1)
                self.multi_cell(w - 2, 4.2, tx(c))
                x += w
            self.set_draw_color(*LINE)
            self.line(MARGIN, y + h, MARGIN + self.content_w, y + h)
            self.set_y(y + h)
        self.ln(3)


def toc(pdf: Manual, outline) -> None:
    pdf.set_xy(MARGIN, max(pdf.get_y(), 34))
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(*BLACK)
    pdf.cell(0, 9, "CONTENTS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*ORANGE)
    pdf.rect(MARGIN, pdf.get_y() + 0.5, pdf.content_w, 1, "F")
    pdf.ln(5)
    for s in outline:
        if s.level > 1:
            continue
        top = s.level == 0
        pdf.set_font("Helvetica", "B" if top else "", 10 if top else 9)
        pdf.set_text_color(*(BLACK if top else DARK))
        if top:
            pdf.ln(1.5)
        indent = 0 if top else 7
        pdf.set_x(MARGIN + indent)
        link = pdf.add_link(page=s.page_number)
        name = tx(s.name)
        pdf.cell(pdf.content_w - indent - 12, 5.6 if top else 5, name, link=link)
        pdf.cell(12, 5.6 if top else 5, str(s.page_number), align="R", link=link, new_x="LMARGIN", new_y="NEXT")


def cover(pdf: Manual) -> None:
    pdf.add_page()
    pdf.set_fill_color(*BLACK)
    pdf.rect(0, 0, pdf.w, pdf.h, "F")
    pdf.set_fill_color(*ORANGE)
    pdf.rect(0, 118, pdf.w, 2.2, "F")
    try:
        pdf.image(str(config.LOGO_PATH), x=MARGIN, y=22, h=16)
        pdf.image(str(config.TRUCK_IMAGE_PATH), x=pdf.w - MARGIN - 95, y=48, w=95)
    except Exception:
        pass
    pdf.set_xy(MARGIN, 132)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 30)
    pdf.multi_cell(0, 13, tx(config.PROJECT_NAME.upper()), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 10, "APP USER MANUAL", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(200, 200, 200)
    pdf.multi_cell(150, 6, align="L", text=tx(f"A step-by-step guide for supervisors, admins and viewers of the countermeasure "
                              f"tracker for the FQM fleet ({config.FLEET}). Written for first-time users, with "
                              "worked examples and troubleshooting tips."), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(pdf.h - 48)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GREY)
    for k, v in (("VERSION", VERSION), ("ISSUED", f"{ISSUED:%d %B %Y}"), ("LANGUAGE OF THE APP", "English / Japanese")):
        pdf.set_x(MARGIN)
        pdf.cell(45, 6, k)
        pdf.set_text_color(*WHITE)
        pdf.cell(0, 6, tx(v), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*GREY)
    pdf.cover = False


# ─────────────────────────────────────────────────────────────────────────
def build() -> Path:
    pdf = Manual()
    pdf.alias_nb_pages()
    cover(pdf)
    pdf.add_page()
    pdf.insert_toc_placeholder(toc, pages=1)

    # 1 ─────────────────────────────────────────────────────────────────
    pdf.chapter("1. Welcome")
    pdf.section("What the app does")
    pdf.p("The **HCM Countermeasure Roll-out 2027** app tracks how each of the HCM countermeasures (weld "
          "reinforcements, brackets, seat screws, pedals...) is being applied across the FQM fleet: about 100 "
          "machines of the models EH4000AC-3, EH3500AC-2 and EX5600-7.")
    pdf.p("It replaces the Excel *Countermeasures Progress Tracker* and the *Action & Roll-out Plan*. Everybody "
          "works on the same live data, every change is recorded with who did it and when, and the dashboards, "
          "Gantt charts, alerts and reports update automatically.")
    pdf.section("Who uses it")
    pdf.table(["Role", "What they do", "How they get in"], [
        ["Viewer", "Sees the read-only landing page: KPIs, timelines, truck view, action plan, Top page. "
                   "Can download the action plan PDF.", "Just opens the app link. No account needed."],
        ["Supervisor", "Records the field progress of every truck: planned, execution steps (e.g. RHS / LHS), "
                       "FIR uploaded, report / timesheets, dates, work order, notes.", "Signs in with a username "
                                                                                      "and password."],
        ["Admin", "Everything a supervisor does, plus: summary and alerts, edits the action plan, adds or removes "
                  "countermeasures and trucks, marks N/A, sets working hours, publishes reports, settings.",
         "Signs in with an admin account."],
        ["Master (app owner)", "Can switch between the Admin and Supervisor views. Creates the user accounts.",
         "Account defined in the app secrets."],
    ], [22, 55, 33])
    pdf.box("tip", "If this is your first time, read chapters 2 and 3 first. Supervisors then go to chapter 5, "
                   "admins to chapters 5 and 6. Chapter 9 explains what to do when something does not update.")

    pdf.section("Key words used in this manual")
    pdf.table(["Word", "Meaning"], [
        ["Countermeasure", "A modification that must be applied to the trucks, e.g. *Front Nose Cone Additional "
                           "Weld*. Each has a responsible person, a fleet target date and a duration per machine."],
        ["Truck record (truck-job)", "One truck x one countermeasure. RD169 + Front Nose Cone is one record."],
        ["Execution steps", "The parts of the work that are ticked when done. Most countermeasures have one step "
                            "(*Executed*); welds often have two (e.g. *RHS Front* and *LHS Front*)."],
        ["Planned", "Tick that shows the job is scheduled. It is ticked automatically when you enter a planned "
                    "date or tick all execution steps."],
        ["FIR uploaded / Report", "The two documentation steps. A job is only *Closed out* when both are ticked."],
        ["N/A", "The countermeasure does not apply to that truck. It is excluded from every %. Only admins set it."],
        ["Fleet target", "Date by which every applicable truck should have the countermeasure executed."],
        ["Working hours", "Estimated hours of work per truck for a countermeasure (same as *Duration per "
                          "machine*). Used for remaining work, downtime and completion estimates."],
    ], [30, 80])

    # 2 ─────────────────────────────────────────────────────────────────
    pdf.chapter("2. Getting started")
    pdf.section("Opening the app")
    pdf.bullets([
        "Open the link shared by the app owner in any modern browser (Chrome, Edge, Safari) on a PC, tablet or "
        "phone. The online app runs on Streamlit Community Cloud.",
        "The first page you see is the **public landing page** (chapter 4). It is read-only: you can look at "
        "everything without signing in.",
        "If the app has not been used for a while it may show *\"This app has gone to sleep\"*. Click "
        "**Yes, get this app back up!** and wait about 30-60 seconds (see chapter 9).",
    ], numbered=True)
    pdf.figure("01_public_top", "Top of the landing page: LANDCROS header, fleet KPI cards and the sign-in "
                                "panel on the right.")
    pdf.section("Signing in", keep=95)
    pdf.figure("02_login", "Sign-in panel. Choose the language, type your username and password, press Sign in.",
               width=55)
    pdf.bullets([
        "On the right side of the landing page, choose **English** or **日本語**.".replace("日本語", "Japanese"),
        "Type your **Username** (e.g. *marcos1*; capital letters and spaces are ignored, so *Marcos1* or "
        "*Peter 1* also work) and your **Password** (capital letters matter).",
        "Press **Sign in** (or press Enter). You land on your own view: supervisors on the progress editor, "
        "admins on the Summary tab.",
    ], numbered=True)
    pdf.box("note", "After a wrong password the app waits a few seconds before you can try again (1 s, 2 s, up "
                    "to 5 s). This protects the accounts. If you forgot your password, ask the app owner to reset "
                    "it - nobody, not even the owner, can see your current password.")
    pdf.section("The sidebar", keep=95)
    pdf.figure("11_sidebar", "Sidebar after signing in: your name and role, language, Refresh data, Change my "
                             "password, Sign out, where the data is stored and today's date.", width=55)
    pdf.table(["Item", "What it does"], [
        ["Name and role", "Shows who is signed in (Supervisor, Admin or Master)."],
        ["Language", "Switches every screen between English and Japanese. Your data does not change."],
        ["View (master only)", "Switches between the Admin and Supervisor views."],
        ["Refresh data", "Reloads the latest data saved by **all** users. Use it whenever you expect to see "
                         "somebody else's change."],
        ["Change my password", "Supervisors change their password here. Admins do it in the Settings tab."],
        ["Sign out", "Ends your session. Always sign out on shared computers."],
        ["Data / Today", "Where the data is stored (GitHub for the live app) and today's date in the project "
                         "time zone (Africa/Lusaka by default)."],
    ], [30, 80])
    pdf.box("tip", "If the sidebar is hidden (small screens), click the orange **>>** button at the top-left "
                   "corner to open it again.")

    # 3 ─────────────────────────────────────────────────────────────────
    pdf.chapter("3. How progress is measured")
    pdf.section("Status of a truck record")
    pdf.p("Every truck record gets a status from the boxes ticked. The same colours are used in the Top page "
          "matrix, the tables and the reports.")
    pdf.table(["Status", "When", "Symbol in Top page"], [
        ["Closed out", "All execution steps + FIR uploaded + Report / timesheets ticked.", "tick"],
        ["Executed - docs open", "All execution steps ticked, but FIR or report still missing.", "E"],
        ["In progress", "Something ticked (Planned, a step, FIR or report) but not all execution steps.",
         "half circle"],
        ["Not started", "Nothing ticked.", "dot"],
        ["N/A", "Countermeasure does not apply to this truck. Not counted anywhere.", "N/A"],
    ], [28, 62, 20], colors=[GREEN, BLUE, ORANGE, MID, NA])
    pdf.section("Progress, fleet % and countermeasure status")
    pdf.bullets([
        "**Progress of a record** = boxes ticked / total boxes, exactly like the *Progress* column of the Excel. "
        "Example: Planned + RHS + LHS ticked, no FIR, no report = 3 of 5 = **60 %**.",
        "**Fleet % executed** of a countermeasure = trucks executed (Executed or Closed out) / applicable trucks. "
        "This is the *Fleet % complete* of the action plan.",
        "**Countermeasure status**: *Done* (100 % executed), *Overdue* (target date passed), *Due soon* (target "
        "within 45 days - configurable), *On track*, *No target* (no date set).",
    ])
    pdf.table(["Bar colour (Gantt and PDF)", "Meaning"], [
        ["Green", "Done / executed."],
        ["Red", "Overdue: the fleet target date has passed and the work is not finished."],
        ["Orange", "In progress / pending, still within the target."],
    ], [35, 75], colors=[GREEN, RED, ORANGE])
    pdf.section("Working hours, downtime and completion")
    pdf.p("Each countermeasure has an estimate of **hours per truck** (the *Duration per machine*, e.g. 12 h). "
          "The app uses it like this:")
    pdf.bullets([
        "Hours only count on trucks where the countermeasure is **not executed yet**. Executed, closed-out and "
        "N/A trucks count 0 h.",
        "If some execution steps are already done, only the open part counts. Example: Front Nose Cone = 12 h "
        "with steps RHS and LHS; RD186 has RHS done -> **6 h** remain.",
        "**Remaining work** of the project = sum of the remaining hours of every truck.",
        "**Estimated downtime of a truck** = sum of its remaining hours; shown also in days using *work hours "
        "per day* (default 12).",
        "**Time to 100 %** = remaining hours / (work hours per day x trucks worked in parallel). The "
        "**estimated completion** date is today + that number of days (calendar days).",
        "The estimated completion date is **based on continuous work on two trucks in parallel, without any "
        "delays** (default: 12 h per day, 2 trucks). Breakdowns, missing parts, holidays or trucks not released "
        "by operations will push the real date later. Admins can change the capacity (6.5).",
    ])
    pdf.box("example", "Remaining work 3,999 h, 12 h per day, 2 trucks in parallel: 3,999 / (12 x 2) = 167 days "
                       "-> estimated completion 29-Apr-2027, assuming continuous work without any delays. With "
                       "only 1 truck at a time it would be 3,999 / 12 = 334 days (13-Oct-2027).")

    # 4 ─────────────────────────────────────────────────────────────────
    pdf.chapter("4. The landing page (everyone)")
    pdf.p("The landing page is what everybody sees before signing in. From top to bottom:")
    pdf.section("4.1 Fleet KPI cards")
    pdf.table(["Card", "Meaning"], [
        ["Fleet executed", "% of all applicable truck-jobs that are executed. E.g. 55 % = 561 of 1027."],
        ["Fully closed out", "% of truck-jobs with execution + FIR + report."],
        ["Countermeasures done", "Countermeasures executed on every applicable truck, e.g. 1 / 20."],
        ["Past target date", "Countermeasures whose fleet target has passed without finishing."],
    ], [35, 75])
    pdf.section("4.2 Countermeasure timeline (fleet Gantt)", keep=95)
    pdf.figure("03_fleet_gantt", "Countermeasure timeline with the forecast cards on top. Each bar = one "
                                 "countermeasure; the coloured part is the % of the fleet executed.")
    pdf.bullets([
        "Three cards on top: **Remaining work** (hours, truck-jobs, trucks), **Time to 100 %** (days at the "
        "configured capacity) and **Estimated completion** (date). The note under the date reminds that it is "
        "*based on continuous work on two trucks in parallel, without any delays*.",
        "Each grey bar runs from the first planned or executed date of the countermeasure to its **fleet "
        "target**. The coloured part shows the **% of the fleet executed** (green / red / orange as in chapter 3).",
        "At the end of the bar: the % and the hours still left, e.g. *71 % - 17 h left*.",
        "The dotted vertical line is **today**. Bars ending left of the line with orange or red still to go are "
        "late.",
        "Move the mouse over a bar (or tap it) to see start, target, trucks executed, status and hours.",
        "In light grey under the chart: **Last update** - the date and time of the last change saved by anybody.",
    ])
    pdf.box("example", "Row *9. Front Cross Beam R5 Radius*: the bar is **red**, the label says **71 % - 17 h "
                       "left**. Meaning: the fleet target (30-Jul-2026) has passed, 71 % of the trucks are "
                       "executed and the 17 remaining trucks need about 17 h of work in total (1 h each).")
    pdf.section("4.3 Truck view", keep=95)
    pdf.figure("04_truck_view", "Truck view for RD200: scoreboard, estimated downtime, truck Gantt and detail "
                                "table.", max_h=215)
    pdf.p("Pick a truck in the **Truck** box (you can type to search, e.g. *RD200*). The view shows:")
    pdf.table(["Card", "Example (RD200)", "Meaning"], [
        ["Countermeasures executed", "6 / 17", "Executed out of applicable; N/A count below."],
        ["Closed out", "5", "Jobs with FIR and report; how many still have documents open."],
        ["Pending", "11", "In progress + not started; the card turns red if any is overdue."],
        ["Overall step progress", "41 %", "Average progress of its records (Excel method)."],
        ["Next planned", "25-Nov-2026", "Next future planned date and its countermeasure."],
        ["Estimated downtime", "106 h", "Remaining hours of its pending work; ~8.8 days at 12 h/day."],
    ], [38, 25, 47])
    pdf.bullets([
        "**Truck Gantt**: one bar per countermeasure that applies to this truck. The grey bar is the "
        "countermeasure window; the coloured part is **this truck's** progress. Green = executed, orange = "
        "pending, a **red label** = target passed and not executed.",
        "Markers: **circle** = planned date, **diamond** = execution date.",
        "Labels show progress, status and the hours left on that truck, e.g. *25 % - In progress - 12 h left*.",
        "In light grey: last update for this truck (when and who).",
        "**Detail table**: status, steps, progress, planned and execution dates, work order, FIR, report, "
        "target, hours per truck, remaining hours and note.",
        "**Truck report (PDF)** (button next to the truck selector): downloads a LANDCROS report of the selected "
        "truck - scoreboard, truck Gantt with planned / execution markers, and the detail table with notes. "
        "Useful for PM planning meetings and for the customer. Every copy gets a **Report ID** and is recorded in "
        "the Print register (6.7).",
    ])
    pdf.section("4.4 Action plan and Top page", keep=95)
    pdf.figure("05_action_plan", "Countermeasure task list (action plan) with the Action plan (PDF) download "
                                 "button.")
    pdf.bullets([
        "**Countermeasure task list - action plan**: responsible, fleet target, executed / applicable, fleet % "
        "executed, % closed out and status. Click a column title to sort.",
        "**Action plan (PDF)**: downloads the LANDCROS action plan report. Page 1 is the **countermeasure "
        "Gantt** with remaining work, time to 100 % and estimated completion; then the KPIs, the countermeasure "
        "task list with fleet % bars, and the alerts. Each copy carries a **Report ID** in its footer and is "
        "recorded in the Print register (6.7).",
        "**Top page**: the truck x countermeasure matrix, coloured by status, like the *Top Page* sheet of the "
        "Excel. Scroll right to see all countermeasures.",
    ])
    pdf.box("tip", "In the Top page the EX5600-7 excavators appear first and have empty cells for the truck "
                   "countermeasures - that is normal: those countermeasures do not apply to them. Admins can "
                   "filter the matrix by model (chapter 6).")

    # 5 ─────────────────────────────────────────────────────────────────
    pdf.chapter("5. Recording progress (supervisors)")
    pdf.p("After signing in, supervisors see the progress editor. You can work in two ways - choose with "
          "**Work by**:")
    pdf.table(["Work by", "Use it when"], [
        ["Countermeasure", "You do the same job on many trucks (e.g. a welding campaign). One table = all the "
                           "trucks of one countermeasure, with each execution step (RHS / LHS) as its own column."],
        ["Truck", "A truck is in the workshop and you work on several countermeasures. One table = all the "
                  "countermeasures of that truck, with a single *Executed* box per countermeasure."],
    ], [28, 82])
    pdf.section("5.1 Working by countermeasure", keep=95)
    pdf.figure("10_sup_cm", "Supervisor view, working by countermeasure: selector, filters, countermeasure "
                            "badge and the editable table.", max_h=170)
    pdf.bullets([
        "Choose the **Countermeasure** (the list shows its fleet %).",
        "Optional: **Show** filters by status (e.g. only *Not started*); **Find fleet # or WO** searches by truck "
        "number or work order.",
        "The black badge shows the status, trucks executed, closed out, responsible, fleet target (days left), "
        "duration per machine and the action required.",
        "Click the boxes and cells in the table to change them. Changed rows are counted under the table: "
        "*\"2 rows changed - not saved yet\"*.",
        "Press **Save changes**. A green message confirms *Saved N rows* and the table, KPIs and charts update.",
    ], numbered=True)
    pdf.table(["Column", "How to fill it"], [
        ["Planned", "Tick when the job is scheduled."],
        ["Step columns (e.g. RHS Front, LHS Front)", "Tick each part when it is physically done."],
        ["FIR uploaded", "Tick when the Field Investigation Report is uploaded."],
        ["Report / timesheets", "Tick when the report and timesheets are filed."],
        ["Planned date", "Double-click, pick the date. Ticks *Planned* automatically."],
        ["Work order", "Type the KMP work order number."],
        ["Execution date", "Filled with today automatically when all steps are ticked (if empty). You can "
                           "change it to the real date."],
        ["Note", "Free text, e.g. *Waiting for parts*."],
        ["N/A", "Greyed out for supervisors - only admins can change it."],
    ], [42, 68])
    pdf.box("example", "**Example 1 - one side welded.** On 12-Nov the night shift welded the RHS of the front "
                       "nose cone on RD173 (WO 15625683).\n"
                       "1) Work by Countermeasure -> *1. Front Nose Cone Additional Weld*. 2) Type *RD173* in "
                       "Find fleet. 3) Tick **RHS Front**, type the WO, note *LHS next PM*. 4) Save changes.\n"
                       "Result: status *In progress*, remaining hours for RD173 drop from 12 h to 6 h.")
    pdf.box("example", "**Example 2 - finishing the job.** Two days later LHS is welded. Tick **LHS Front** and "
                       "Save. Because all steps are now ticked, *Execution date* is filled with today and the "
                       "status becomes *Executed - docs open*. An alert *Executed, documents missing* appears for "
                       "the admins. When the FIR and the report are filed, tick **FIR uploaded** and **Report / "
                       "timesheets** and Save -> *Closed out*.")
    pdf.box("example", "**Example 3 - scheduling.** RD188 is booked for the rear nose cone on 25-Nov with WO "
                       "15712345. Choose *2. Rear Nose Cone*, find RD188, set **Planned date** = 25-Nov-2026 and "
                       "the work order, Save. *Planned* is ticked automatically and the date appears as a circle "
                       "in the truck Gantt and as *Next planned* in the truck scoreboard. If 25-Nov passes "
                       "without execution, an alert *Planned date passed, not executed* is raised.")
    pdf.box("warning", "Changing the countermeasure, the **Show** filter or the **Find** text **discards the "
                       "changes you have not saved**. Always press **Save changes** before switching.")
    pdf.section("5.2 Working by truck", keep=95)
    pdf.figure("12_sup_truck", "Supervisor view, working by truck: truck badge and one row per countermeasure.",
               max_h=150)
    pdf.bullets([
        "Choose **Work by -> Truck** and pick the truck (e.g. *RD200 - EH4000AC-3 - 35 %*).",
        "Each row is one countermeasure. **Executed** ticks **every** execution step of that countermeasure at "
        "once (e.g. both RHS and LHS).",
        "Fill planned date, work order, FIR, report and notes as above, then **Save changes**.",
    ], numbered=True)
    pdf.box("tip", "To tick only one side (RHS or LHS) of a two-step countermeasure, use *Work by -> "
                   "Countermeasure*: the truck view only has one Executed box.")
    pdf.box("example", "**Example 4 - truck in for PM.** RD200 is in the workshop for its PM and the team does "
                       "the rear and front panto support frame reinforcements. Work by Truck -> RD200, tick "
                       "**Executed** on rows 7 and 8, Save. RD200's estimated downtime drops by 8 h (4 h each).")
    pdf.section("5.3 Change history", keep=95)
    pdf.figure("13_history", "Change history under the table: when, who, truck, countermeasure, what changed and "
                             "the note.")
    pdf.p("Open **Change history** under the table to see every saved change for that countermeasure or truck: "
          "date and time, who, and exactly what changed (e.g. *planned=True, planned_date=2026-11-25, "
          "work_order=15712345*). Nothing is ever deleted - if a value was wrong, simply save the correct value; "
          "the latest one wins.")

    # 6 ─────────────────────────────────────────────────────────────────
    pdf.chapter("6. Managing the project (admins)")
    pdf.p("Admins see eight tabs. The master user sees the same tabs when *View* is set to *Admin* in the "
          "sidebar.")
    pdf.table(["Tab", "Use it to"], [
        ["Summary", "See the KPIs, all open alerts, the action plan and the latest changes."],
        ["Top page", "See the truck x countermeasure matrix, filtered by model."],
        ["Progress", "Record progress like a supervisor, and set N/A."],
        ["Countermeasures", "Edit the action plan; add or remove countermeasures."],
        ["Working hours", "Set the hours per truck of each countermeasure and the workshop capacity; see "
                          "downtime per truck."],
        ["Trucks", "See the fleet; add or remove trucks."],
        ["Reports", "Download Excel / PDF / CSV and publish them."],
        ["Settings", "Time zone, due-soon warning, your password."],
    ], [30, 80])
    pdf.section("6.1 Summary and alerts", keep=95)
    pdf.figure("20_admin_summary", "Summary tab: KPI cards and the alert list (most urgent first).", max_h=160)
    pdf.table(["Alert", "Raised when", "Typical action"], [
        ["Past the fleet target", "Target date passed and trucks still to execute.",
         "Re-plan the work or agree a new target (Countermeasures tab)."],
        ["Planned date passed, not executed", "A truck's planned date is in the past and it is not executed.",
         "Ask the supervisor to execute it or set a new planned date."],
        ["Fleet target approaching", "Target within the due-soon window (45 days by default).",
         "Check that the remaining trucks are scheduled."],
        ["Executed, documents missing", "Executed trucks without FIR or report.",
         "Chase the FIR / report and tick them."],
    ], [32, 40, 38])
    pdf.section("6.2 Top page by model", keep=95)
    pdf.figure("21_admin_matrix", "Top page filtered to EH4000AC-3. Use the Model buttons to switch.", max_h=120)
    pdf.section("6.3 Progress and N/A", keep=95)
    pdf.figure("22_admin_progress", "Progress tab - the same editor as supervisors, with the N/A column enabled.",
               max_h=120)
    pdf.box("example", "**Example 5 - N/A.** In the Excel, RD220 had no status for the front strut mount, so it "
                       "was loaded as **N/A** (not applicable). Now the truck does need the weld. Progress -> "
                       "Countermeasure *3. Front Strut Mount Additional Weld*, Show *N/A*, find RD220, **untick "
                       "N/A**, Save. RD220 now counts in the strut's %, hours and alerts as *Not started*. To "
                       "exclude a truck, do the opposite: tick N/A and Save.")
    pdf.section("6.4 Countermeasures: edit, add, remove", keep=95)
    pdf.figure("23_admin_cms", "Countermeasures tab: Edit a countermeasure, Add countermeasure and Remove "
                               "countermeasure.", max_h=200)
    pdf.sub("Edit a countermeasure")
    pdf.p("Pick the countermeasure, change name, model, responsible, fleet target, duration per machine or action "
          "required, and press **Save**. Only the fields you changed are recorded.")
    pdf.box("example", "**Example 6 - new target date.** The customer agreed to move *12. LHS Fender "
                       "Countermeasure* to 30-Apr-2027. Select it, change **Fleet target** to 30/04/2027, Save. "
                       "Its status, the alerts, the Gantt bar and the PDF update at once.")
    pdf.sub("Add a countermeasure")
    pdf.bullets([
        "Fill **Name** (required), model, responsible, fleet target, duration (e.g. *10 h*) and action required.",
        "**Execution steps**: leave *Executed* for a single step, or type the steps separated by commas, e.g. "
        "*RHS, LHS*.",
        "**Trucks it applies to (copy list from)**: copy the truck list (including N/A trucks) of a similar "
        "countermeasure, or choose *No trucks yet* and add them later in the Trucks tab.",
        "Press **Add countermeasure**.",
    ], numbered=True)
    pdf.box("example", "**Example 7 - new weld.** Name *Rear Axle Housing Additional Weld*, model *EH4000AC-3*, "
                       "responsible *Andrew Moobela*, target 30/06/2027, duration *10 h*, steps *RHS, LHS*, copy "
                       "trucks from *1. Front Nose Cone*. It appears at the end of the action plan with 0 %, and "
                       "adds 10 h x the number of applicable trucks to the remaining work.")
    pdf.box("warning", "The **execution steps cannot be changed** after the countermeasure is created. Check them "
                       "before pressing Add.")
    pdf.sub("Remove a countermeasure")
    pdf.p("Choose it, tick the confirmation box and press **Remove countermeasure**. It disappears from the "
          "tracker and reports; its change history is kept.")
    pdf.section("6.5 Working hours", keep=95)
    pdf.figure("24_admin_hours", "Working hours tab: forecast cards, hours per truck table, capacity and "
                                 "estimated downtime per truck.", max_h=215)
    pdf.bullets([
        "**Countermeasure working hours** table: type the **Hours per truck** of each countermeasure (e.g. "
        "12.0) and press **Save**. *Trucks pending* and *Remaining hours* are calculated for you.",
        "These hours are the same value as *Duration per machine*: changing one changes the other.",
        "**Capacity used for the completion estimate**: *Work hours per day on a truck* (e.g. 12 for one "
        "12-hour shift; default 12) and *Trucks worked in parallel* (default 2). Press **Save settings**. The "
        "note under *Estimated completion* always shows the number of trucks used.",
        "**Estimated downtime per truck**: trucks with the most outstanding work first, in hours and days.",
        "A yellow warning lists countermeasures without hours - their trucks are not counted until you set them.",
    ])
    pdf.box("example", "**Example 8 - longer job than planned.** The mirror bracket upgrade really takes 20 h, "
                       "not 12 h. Change *11. LHS Mirror Bracket Upgrade* from 12.0 to 20.0 and Save. With 7 "
                       "trucks pending, its remaining hours go from 84 h to 140 h, and the project's remaining "
                       "work, time to 100 % and completion date move accordingly.")
    pdf.box("example", "**Example 9 - third bay.** From December three trucks can be worked at the same time. Set "
                       "*Trucks worked in parallel* = 3 and Save settings: *Time to 100 %* drops from 167 to 112 "
                       "days, the estimated completion moves from 29-Apr-2027 to 05-Mar-2027, and the note reads "
                       "*based on continuous work on three trucks in parallel, without any delays*.")
    pdf.section("6.6 Trucks", keep=95)
    pdf.figure("25_admin_trucks", "Trucks tab: fleet table (with pending countermeasures and estimated "
                                  "downtime), Add truck and Remove truck.", max_h=175)
    pdf.box("example", "**Example 10 - new truck.** RD232 (serial 50189, EH4000AC-3) joins the fleet. Trucks -> "
                       "Add truck: Truck *RD232*, Serial *50189*, Model *EH4000AC-3*, keep the countermeasures "
                       "that apply (remove the ones that do not), press **Add truck**. It appears in every table "
                       "as *Not started*.")
    pdf.p("To remove a truck from some or all countermeasures, choose it in **Remove truck**, keep the "
          "countermeasures to remove it from, tick the confirmation box and press **Remove truck**. To exclude a "
          "truck from one countermeasure without deleting it, use **N/A** instead (6.3).")
    pdf.section("6.7 Reports and Settings", keep=95)
    pdf.figure("26_admin_reports", "Reports tab: downloads, Publish reports and the Print register.", max_h=110)
    pdf.table(["Button", "You get"], [
        ["Excel workbook", "Summary, Countermeasures (incl. hours), Top Page, Truck records, Trucks (incl. "
                           "downtime) and Change log sheets."],
        ["Action plan (PDF)", "The LANDCROS action plan report: page 1 countermeasure Gantt with the hours "
                              "forecast, then KPIs, task list with fleet % bars and alerts."],
        ["Truck records (CSV)", "Every truck record in one file, for other tools."],
        ["Publish reports", "Saves today's Excel and PDF in the *reports/* folder of the data repository, so "
                            "everybody keeps the same version."],
    ], [32, 78])
    pdf.sub("Print register and Report ID")
    pdf.p("Every PDF report printed from the app - the **Action plan (PDF)** (landing page or Reports tab) and the "
          "**Truck report (PDF)** (truck view) - gets a unique **Report ID**, for example "
          "*RPT-20261113-090627-613C* (date, time and a random code). The ID and the name of who printed it are "
          "shown at the bottom of every page of the PDF.")
    pdf.figure("28_pdf_footer", "Footer of a printed action plan: Report ID and Printed by.", max_h=14)
    pdf.bullets([
        "Each download is recorded with its Report ID, report type, truck (for truck reports), date and time, and "
        "the user. Downloads from the public landing page are recorded as *Public view (not signed in)*.",
        "Admins see the list in **Reports -> Print register**; it also appears in *Recent changes*, in the "
        "truck's *Change history* and in the *Change log* sheet of the Excel workbook.",
        "To check a paper copy, look up its Report ID in the Print register: you will see who printed it and when.",
    ])
    pdf.box("example", "**Example 11 - which copy is this?** At the weekly meeting a printed truck report for RD200 "
                       "shows *Report ID RPT-20261113-090618-8750*. In Reports -> Print register that ID reads "
                       "*13-Nov-2026 11:06 - Public view (not signed in) - truck report - RD200*, so everyone knows "
                       "it shows the status at 11:06 on 13 November.")
    pdf.figure("27_admin_settings", "Settings tab: time zone, due-soon warning and Change my password.", max_h=95)
    pdf.bullets([
        "**Project time zone** defines *today* for every date calculation (default *Africa/Lusaka*).",
        "**Warn ... days before the fleet target** sets the *Due soon* window (default 45 days).",
        "**Change my password** (admins): current password, new password (8+ characters) twice, Save.",
    ])

    # 7 ─────────────────────────────────────────────────────────────────
    pdf.chapter("7. User accounts (app owner)")
    pdf.p("Accounts are created only by the app owner, from a terminal on the owner's computer, in the project "
          "folder. Passwords are typed without being shown and are stored encrypted (bcrypt).")
    pdf.table(["Command", "What it does"], [
        ["python scripts/users.py add", "Create a user: username, full name, role (admin / supervisor), password."],
        ["python scripts/users.py list", "List users, roles and whether they are active."],
        ["python scripts/users.py password <user>", "Reset a forgotten password."],
        ["python scripts/users.py role <user> admin", "Change a role (admin or supervisor)."],
        ["python scripts/users.py rename <user> \"Name\"", "Change the full name shown in the app."],
        ["python scripts/users.py deactivate <user>", "Remove access but keep the user's history."],
        ["python scripts/users.py activate <user>", "Give access back."],
        ["python scripts/users.py master-hash", "Create the [master] block for the secrets (owner login)."],
    ], [55, 55])
    pdf.box("warning", "After running **master-hash**, paste the new [master] block into *.streamlit/secrets.toml* "
                       "**and** into Streamlit Cloud -> App settings -> Secrets, then **Reboot** the online app "
                       "(chapter 9). Otherwise the new password does not work online.")
    pdf.box("tip", "A user who leaves the project should be **deactivated**, not deleted, so their name stays "
                   "next to the changes they made. Deactivation takes effect within about 30 seconds.")
    pdf.section("Accounts in use")
    pdf.table(["Username", "Name", "Role", "Notes"], [
        ["iibanez", "Ivan Ibanez", "Master (app owner)", "Defined in the app secrets. Admin and Supervisor views."],
        ["marcos1", "Marcos", "Admin", "Created 13-Nov-2026. Can sign in as Marcos1 or marcos1."],
        ["peter1", "Peter", "Admin", "Created 13-Nov-2026. Can sign in as Peter 1, Peter1 or peter1."],
    ], [22, 22, 26, 50])
    pdf.box("warning", "Passwords are never written in this manual. They are given to each person privately by "
                       "the app owner. Each admin should change the initial password the first day: Settings -> "
                       "Change my password.")
    pdf.bullets([
        "**Usernames** ignore capital letters and spaces: *Peter 1*, *PETER1* and *peter1* are the same account.",
        "**Passwords** are case-sensitive: *Example123* is not the same as *example123*.",
    ])

    # 8 ─────────────────────────────────────────────────────────────────
    pdf.chapter("8. Where the data is saved")
    pdf.bullets([
        "The Excel tracker was only used **once**, to load the initial status. The app never writes to it.",
        "Every save creates a small, permanent file in the **data** branch of the GitHub repository "
        "(*iibanez828-droid/HCMZ-Countermeasures-project-EH4000AC3*). Nothing is overwritten, so the full history "
        "of who changed what and when is kept.",
        "The program code lives in the **main** branch. Saving data never restarts the app.",
        "The online app and any local copy that uses the same secrets work on the **same data**.",
        "Need an up-to-date Excel? Admin -> Reports -> **Excel workbook**.",
    ])
    pdf.box("warning", "Never edit or push files to the **data** branch by hand. Use the app.")

    # 9 ─────────────────────────────────────────────────────────────────
    pdf.chapter("9. Refresh, reboot and troubleshooting")
    pdf.section("9.1 The three levels of \"refresh\"")
    pdf.table(["Level", "When to use it", "How"], [
        ["1. Refresh data (sidebar)", "You do not see a change another person saved; numbers look old.",
         "Click **Refresh data** in the sidebar. The app also refreshes by itself every 30 seconds."],
        ["2. Reload the browser page", "The page looks frozen, half-drawn or shows a red error box.",
         "Press F5 (Windows) or Cmd+R (Mac). **You will be signed out** - sign in again. Unsaved table edits are "
         "lost."],
        ["3. Reboot the app (owner / admin with Streamlit access)",
         "A new version was pushed but does not show; secrets were changed; the app is stuck or errors for "
         "everybody.",
         "share.streamlit.io -> your app -> (three dots) -> **Reboot app**. Or, on the app page, **Manage app** "
         "(bottom right) -> (three dots) -> **Reboot app**. Wait 1-2 minutes."],
    ], [32, 38, 40])
    pdf.box("tip", "Try the levels in order: Refresh data first, then reload the page, and reboot only if the "
                   "first two do not help. Rebooting is safe - no data is lost, because the data is in GitHub - "
                   "but everybody connected is disconnected for a minute.")
    pdf.section("9.2 After the owner changes the app")
    pdf.bullets([
        "**Code changes** pushed to the *main* branch are picked up automatically by Streamlit Cloud within about "
        "1-2 minutes. If after 5 minutes the change is still not visible: reload the page; if still not, "
        "**Reboot app**.",
        "**Secrets changes** (token, master password) are only read when the app starts: always **Reboot app** "
        "after saving the secrets.",
        "**Local copy** (owner's computer): stop it with **Ctrl+C** in the terminal and start it again with "
        "*streamlit run app.py*. Tip: start it with *streamlit run app.py --server.runOnSave true* so the page "
        "reloads by itself every time a file is saved.",
    ])
    pdf.section("9.3 Common problems")
    pdf.table(["What you see", "Why", "What to do"], [
        ["\"This app has gone to sleep due to inactivity\"", "Free Streamlit apps sleep after some hours "
                                                             "without visitors.",
         "Click **Yes, get this app back up!** and wait 30-60 s."],
        ["\"The project has not been loaded yet\" and sign-in fails", "The online app has no secrets, so it "
                                                                      "cannot reach the data.",
         "Owner: paste the secrets in Streamlit Cloud -> Settings -> Secrets, Save, **Reboot app**. Sidebar "
         "*Data* must say *GitHub ...@data*."],
        ["\"Incorrect username or password\"", "Typo, caps, wrong account, account deactivated, or the master "
                                               "block in the secrets is outdated.",
         "Check spelling (usernames are lower case). Ask the owner to reset the password or reboot after "
         "updating the secrets."],
        ["Somebody else's change is not visible", "Your screen keeps data for up to 30 seconds.",
         "Click **Refresh data**."],
        ["My edits disappeared", "The countermeasure, filter or search was changed before saving, or the page "
                                 "was reloaded.", "Enter them again and press **Save changes** first."],
        ["\"Could not save. GitHub ... 401\"", "The GitHub token expired or is wrong.",
         "Owner: create a new token, update the secrets, Reboot app."],
        ["\"Could not save. GitHub ... 403 / 404\"", "Token without write permission, repository renamed, or "
                                                     "GitHub limit reached.",
         "Wait a minute and retry; if it persists, owner checks the token and repository."],
        ["Saving many rows is slow", "Each row is saved separately to GitHub.",
         "Wait for the confirmation; save in smaller batches (20-30 rows)."],
        ["A pushed change does not appear online", "Streamlit has not redeployed yet.",
         "Wait 2 minutes, reload the page, then **Reboot app**."],
        ["Red error box after an update", "Usually a temporary problem during a redeploy.",
         "Reload the page. If it stays, owner opens **Manage app** to read the log and reboots."],
    ], [36, 36, 38])
    pdf.box("note", "When you report a problem to the app owner, include: what you clicked, the exact message "
                    "(a screenshot is best), the truck and countermeasure, and the time.")

    # 10 ────────────────────────────────────────────────────────────────
    pdf.chapter("10. Quick reference")
    pdf.section("Supervisor - daily routine")
    pdf.bullets([
        "Open the app link -> Sign in.",
        "Work by **Countermeasure** (campaigns) or **Truck** (truck in the workshop).",
        "Tick what was done today; enter planned dates, work orders and notes.",
        "Press **Save changes** and wait for *Saved N rows*.",
        "When FIR and report are filed, tick them and Save -> *Closed out*.",
        "Click **Refresh data** if you expect to see a colleague's change. **Sign out** when done.",
    ], numbered=True)
    pdf.section("Admin - weekly routine")
    pdf.bullets([
        "Summary: review alerts (overdue, planned date passed, due soon, documents missing).",
        "Countermeasures: update responsible, target dates and action required after the planning meeting.",
        "Working hours: check hours per truck and capacity; read the estimated completion date.",
        "Trucks / Progress: add new trucks; set N/A where a countermeasure does not apply.",
        "Reports: download or **Publish reports** for the weekly meeting.",
    ], numbered=True)
    pdf.section("Remember")
    pdf.bullets([
        "Nothing is deleted: correct a mistake by saving the right value.",
        "Ticking all execution steps fills the execution date with today (if empty) and ticks Planned.",
        "Only admins can set N/A. Execution steps are fixed once a countermeasure is created.",
        "Refresh data -> reload page -> Reboot app, in that order.",
    ])

    pdf._flush(0)
    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    print(build())
