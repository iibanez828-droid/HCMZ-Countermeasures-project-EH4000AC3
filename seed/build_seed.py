"""Convierte el Excel de seguimiento y el plan de acción (PDF) en los CSV de origen.

    python seed/build_seed.py

Entradas (en esta carpeta):
- Countermeasures Progress Tracker V2-19-Oct-26.xlsx  → una hoja por contramedida
- HCM-Countermeasure Action & Roll out Plan.pdf       → responsable, fecha meta, duración y acción
  (los datos del PDF están transcritos abajo en PLAN porque el PDF no es editable)

Salidas:
- countermeasures_seed.csv  ← catálogo: una fila por contramedida
- records_seed.csv          ← estado inicial: una fila por camión × contramedida
"""

from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
TRACKER = HERE / "Countermeasures Progress Tracker V2-19-Oct-26.xlsx"

AM, TC, GM, BM = "Andrew Moobela", "Timothy Chilapala", "Gillen Mukuka", "Bright Musonda"
PM = "Scheduling the work to be carried out during PMs."
SHUT = ("Taking advantage during 15,000-hour shutdowns or during major component work like struts upgrade "
        "and front axle trunnion modifications.")

# id, nombre, hoja del Excel, modelo, responsable, fecha meta, duración por máquina, acción requerida
PLAN = [
    ("nose-front", "Front Nose Cone Additional Weld", "Front Nose Cone Additional Weld", "EH4000AC-3", AM, "2026-12-31", "12 h", PM),
    ("nose-rear", "Rear Nose Cone Additional Weld", "Rear Nose Cone Additional Weld", "EH4000AC-3", AM, "2027-10-30", "12 h",
     "CSL was shared to customer; scheduling will start."),
    ("strut", "Front Strut Mount Additional Weld", "Front Strut Mount", "EH4000AC-3", TC, "2026-12-31", "10 h", PM),
    ("top-plate", "Frame Top Plate Reinforcement", "Frame top plate countermeasure", "EH4000AC-3", GM, "2027-01-30", "12 h", PM),
    ("trailing-arm", "Trailing Arm R12 Radius", "Trailing Arm Holes R12", "EH4000AC-3", AM, "2026-06-30", "4 h",
     "Use machines after PM during backlog repairs. Target 7 trucks per week. KMP work orders opened 1 week before pre-planning meeting."),
    ("panto-a", "Panto A-Frame Reinforcement", "Panto A-Frame", "EH4000AC-3 (S3)", GM, "2026-08-30", "4 h",
     "Applies to the S3 machines (10 trucks) only. Target 2 trucks per month. Awaiting parts."),
    ("panto-rear", "Panto Support Frame Reinforcement (Rear)", "Panto Frame Reinforcement Rear", "EH4000AC-3", AM, "2026-12-31", "4 h", PM),
    ("panto-front", "Panto Support Frame Reinforcement (Front)", "Panto Frame Reinforcement FRONT", "EH4000AC-3", AM, "2026-12-31", "4 h", PM),
    ("cross-beam", "Front Cross Beam R5 Radius", "FRONT CROSS BEAM-R5 RADIUS", "EH4000AC-3", TC, "2026-07-30", "1 h",
     "R5 modification, targeting 7 trucks per week."),
    ("rhs-fender", "RHS Fender Repair", "RHS FENDER REPAIR", "EH4000AC-3", BM, "2026-12-31", "12 h", SHUT),
    ("mirror", "LHS Mirror Bracket Upgrade", "LHS Mirror Bracket Update", "EH4000AC-3", BM, "2026-12-31", "12 h",
     "Target is to complete 1 truck per week."),
    ("lhs-fender", "LHS Fender Countermeasure", "LHS FENDER COUNTERMEASURE", "EH4000AC-3", AM, "2027-03-31", "12 h",
     "Work orders created. Target 1 truck per week."),
    ("brake", "Single Brake Pedal S/B", "SINGLE BRAKE PEDAL SB", "EH4000 / EH3500", "Andre Du Plooy", "2026-08-30", "2 h",
     "Inspection & verification included as a PM task; 10 trucks per week across EH3500AC and EH4000AC. "
     "Pedal marked with red paint. Use machines on breakdown, at the fuel farm, in the workshop or on the go-line."),
    ("deck-nuts", "Centre Deck Nuts Countermeasure", "Centre Deck Nuts Countermeasure", "EH4000AC-3", AM, "2026-09-29", "2 h",
     "10 trucks per week scheduled. Use machines on breakdown or in the workshop."),
    ("handrail", "RHS Handrail Reinforcement", "RHS Hand Rail Reinforcement", "EH4000AC-3", "Tada", "", "",
     "Awaiting service parts."),
    ("upright-seat", "LHS Upright Seat Screw", "LHS Upright Seat Screw", "EH4000AC-3", AM, "2027-03-31", "12 h",
     SHUT + " CSL provided 19 March."),
    ("frame-seat-rhs", "Main Frame Bottom Plate Seat Screw (RHS)", "RHS Frame Re-location seatscrew", "EH4000AC-3", AM, "2027-03-31", "3 h",
     "Scheduling plan communicated to the customer. KMP work orders opened every week."),
    ("frame-seat-lhs", "Main Frame Bottom Plate Seat Screw (LHS)", "LHS Frame Re-location seats", "EH4000AC-3", AM, "2027-10-01", "8 h",
     "Scheduling plan communicated to the customer. CSL shared to customer on 7/11/2026."),
    ("ex-arm", "EX5600-7 Arm Additional Welds", "EX5600-7 LD ARM WELD", "EX5600-7", "Tada", "2026-10-01", "16 h",
     "Pro-active additional welding before crack development, arm top and bottom positions."),
    ("ex-boom", "EX5600-7 Boom Additional Welds", "EX5600-7 LD BOOM WELD", "EX5600-7", "Tada", "2026-10-01", "12 h",
     "Pro-active additional welding before crack development."),
]


def _date(v) -> str:
    return v.strftime("%Y-%m-%d") if isinstance(v, dt.datetime) else ""


def _step_label(h: str) -> str:
    return h.strip().replace("(RHS) ", "RHS ").replace("(LHS)", "LHS ").strip()


def read_tracker(path: Path) -> tuple[dict[str, str], dict[str, dict]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    models = {}
    for r in list(wb["Top Page"].iter_rows(values_only=True))[2:]:
        if r[1]:
            models[str(r[1]).strip()] = str(r[0]).strip()
    sheets = {}
    for ws in wb.worksheets[1:]:
        rows = list(ws.iter_rows(values_only=True))
        hdr = [(str(c).strip().lower() if c is not None else "") for c in rows[2]]

        def col(pred):
            return next((i for i, h in enumerate(hdr) if pred(h)), None)

        i_pd = col(lambda h: "planned date" in h or "panned date" in h)
        i_wo = col(lambda h: h.startswith("work order") and "closed" not in h)
        i_ed = col(lambda h: "execu" in h and "date" in h)
        i_pl = col(lambda h: h == "planned")
        i_fir = col(lambda h: h.startswith("fir"))
        i_rep = col(lambda h: h.startswith("report"))
        i_st = col(lambda h: h == "status")
        steps = [(i, _step_label(str(rows[2][i]))) for i in range(i_pl + 1, i_fir)]
        recs = []
        for r in rows[3:]:
            fleet = r[0]
            if not isinstance(fleet, str) or not fleet.strip() or len(fleet) > 8:
                continue
            g = lambda i: r[i] if i is not None and i < len(r) else None  # noqa: E731
            wo = g(i_wo)
            wo = str(wo) if isinstance(wo, (int, float)) and not isinstance(wo, bool) else (wo if isinstance(wo, str) else "")
            serial = g(1)
            recs.append({
                "fleet": fleet.strip(), "serial": str(serial) if isinstance(serial, (int, str)) else "",
                "model": models.get(fleet.strip(), "EX5600-7" if fleet.startswith("EX") else ""),
                "planned_date": _date(g(i_pd)), "work_order": wo, "exec_date": _date(g(i_ed)),
                "planned": int(bool(g(i_pl))), "steps": "|".join(str(int(bool(g(i)))) for i, _ in steps),
                "fir": int(bool(g(i_fir))), "report": int(bool(g(i_rep))),
                # Sin estado en el Excel = la contramedida no aplica a ese camión
                "na": int(not g(i_st)),
            })
        sheets[ws.title.strip()] = {"steps": [s for _, s in steps], "records": recs}
    return models, sheets


def main(tracker: Path = TRACKER) -> None:
    _, sheets = read_tracker(tracker)
    with open(HERE / "countermeasures_seed.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cm_id", "order", "name", "model", "owner", "target", "duration", "action", "steps"])
        for n, (cid, name, sheet, model, owner, target, dur, action) in enumerate(PLAN, 1):
            w.writerow([cid, n, name, model, owner, target, dur, action, "|".join(sheets[sheet]["steps"])])
    with open(HERE / "records_seed.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["cm_id", "fleet", "serial", "model", "planned_date", "work_order", "exec_date",
                "planned", "steps", "fir", "report", "na"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        total = 0
        for cid, _, sheet, *_ in PLAN:
            for rec in sheets[sheet]["records"]:
                w.writerow({"cm_id": cid, **rec})
                total += 1
    print(f"{len(PLAN)} countermeasures, {total} truck records")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else TRACKER)
