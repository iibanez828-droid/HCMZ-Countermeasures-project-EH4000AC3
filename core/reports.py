"""Reportes consolidados en Excel y CSV (para descargar o publicar en la rama
`data`, carpeta reports/)."""

from __future__ import annotations

import io

import pandas as pd

from core import config
from core.project import Project


def countermeasure_table(p: Project) -> pd.DataFrame:
    c = p.cms
    return pd.DataFrame({
        "No.": c.order, "Countermeasure": c["name"], "Model": c.model, "Responsible": c.owner,
        "Fleet target": c.target, "Duration per machine": c.duration, "Action required": c.action,
        "Applicable trucks": c.n, "Executed": c.executed, "Closed out": c.closed,
        "In progress": c.in_progress, "Not started": c.not_started, "N/A": c.na,
        "Fleet % executed": (c.pct * 100).round(1), "Fleet % closed": (c.close_pct * 100).round(1),
        "Status": c.status, "Days to target": c.days_left,
        "Hours per truck": c.hours, "Trucks pending": c.pending_n, "Remaining hours": c.remaining_h.round(1),
    })


def record_table(p: Project) -> pd.DataFrame:
    r = p.records.sort_values(["order", "fleet"])
    return pd.DataFrame({
        "Countermeasure": r.cm_name, "Fleet": r.fleet, "Serial": r.serial, "Model": r.model,
        "Planned date": r.planned_date, "Work order": r.work_order, "Execution date": r.exec_date,
        "Planned": r.planned, "Steps executed": r.steps.map(lambda s: f"{sum(s)}/{len(s)}"),
        "FIR uploaded": r.fir, "Report/Timesheets": r.report, "Progress %": (r.progress * 100).round(0),
        "Status": r.status, "Note": r.note, "Last update": r.last_ts.str[:16].str.replace("T", " "),
        "Updated by": r.last_user,
    })


def truck_table(p: Project) -> pd.DataFrame:
    t = p.trucks
    return pd.DataFrame({"Fleet": t.fleet, "Serial": t.serial, "Model": t.model, "Applicable": t.n,
                         "Executed": t.executed, "Closed out": t.closed, "% executed": (t.pct * 100).round(1),
                         "Pending countermeasures": t.pending, "Estimated downtime (h)": t.remaining_h.round(1)})


def matrix_table(p: Project) -> pd.DataFrame:
    """Hoja tipo «Top Page»: camión × contramedida con el estado."""
    m = p.records.pivot_table(index="fleet", columns="cm_name", values="status", aggfunc="first")
    m = m.reindex(index=p.fleets(), columns=p.cms["name"].tolist())
    return m.reset_index().rename(columns={"fleet": "Fleet"}).fillna("")


def build_excel(p: Project) -> bytes:
    k = p.kpis()
    sheets = {
        "Countermeasures": countermeasure_table(p),
        "Top Page": matrix_table(p),
        "Truck records": record_table(p),
        "Trucks": truck_table(p),
        "Change log": p.log,
    }
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        head = xw.book.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1A1A1A", "border": 1})
        info = pd.DataFrame({"": [config.PROJECT_NAME, f"Generated: {p.today.isoformat()}",
                                  f"Fleet executed: {k['pct'] * 100:.1f}% ({k['executed']}/{k['n']} truck-jobs)",
                                  f"Fully closed out: {k['close_pct'] * 100:.1f}%",
                                  f"Countermeasures done: {k['cms_done']}/{k['cms']}",
                                  f"Past target date: {k['cms_overdue']}"]})
        info.to_excel(xw, sheet_name="Summary", index=False, header=False)
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for c, col in enumerate(df.columns):
                ws.write(0, c, col, head)
                width = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) + 2
                ws.set_column(c, c, min(width, 50))
            ws.freeze_panes(1, 1 if name == "Top Page" else 0)
            if len(df.columns):
                ws.autofilter(0, 0, max(len(df), 1), len(df.columns) - 1)
    return buf.getvalue()


def status_csv(p: Project) -> bytes:
    return record_table(p).to_csv(index=False).encode("utf-8-sig")
