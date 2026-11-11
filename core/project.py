"""Estado actual del proyecto, calculado a partir del catálogo, el estado inicial y los eventos.

Reglas de negocio (todas en este archivo):
- Un registro es un camión × una contramedida. Sus pasos son: Planificado,
  los pasos de ejecución de la contramedida (p. ej. RHS / LHS), FIR subido y
  Reporte / hojas de tiempo.
- Avance de un registro = pasos marcados ÷ pasos totales (igual que el Excel).
- Estado de un registro:
    N/A          la contramedida no aplica al camión (no cuenta en ningún %)
    closed       todos los pasos de ejecución + FIR + reporte
    executed     todos los pasos de ejecución, falta documentación (FIR o reporte)
    in_progress  algún paso marcado
    not_started  ningún paso marcado
- % ejecutado de una contramedida = camiones ejecutados (executed + closed)
  ÷ camiones aplicables. Es el "Fleet % complete" del plan de acción.
- Estado de una contramedida: done (100 % ejecutado), overdue (pasó la fecha
  meta), due_soon (faltan `due_soon_days` días o menos), on_track, no_target.
- El estado inicial viene del Excel (plan/baseline.csv). Los eventos se
  aplican encima en orden de fecha: el último valor guardado gana.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from core import config
from core.events import read_baseline, read_catalog, read_events, read_settings

RECORD_FIELDS = ("planned", "steps", "fir", "report", "planned_date", "work_order", "exec_date", "note", "na")


def _d(value) -> date | None:
    if isinstance(value, date):
        return value
    if not value or (isinstance(value, float) and value != value):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _b(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def fleet_key(fleet: str) -> tuple[str, int]:
    """RD9 < RD10 < RD100 (orden natural por prefijo y número)."""
    head = fleet.rstrip("0123456789")
    num = fleet[len(head):]
    return head, int(num) if num.isdigit() else 0


def record_status(rec: Mapping) -> str:
    if rec.get("na"):
        return "na"
    steps = list(rec.get("steps") or [])
    executed = bool(steps) and all(steps)
    if executed and rec.get("fir") and rec.get("report"):
        return "closed"
    if executed:
        return "executed"
    if rec.get("planned") or any(steps) or rec.get("fir") or rec.get("report"):
        return "in_progress"
    return "not_started"


def record_progress(rec: Mapping) -> float:
    if rec.get("na"):
        return 0.0
    items = [bool(rec.get("planned")), *map(bool, rec.get("steps") or []), bool(rec.get("fir")), bool(rec.get("report"))]
    return sum(items) / len(items) if items else 0.0


def cm_status(executed: int, n: int, target: date | None, today: date, due_soon_days: int) -> str:
    if n and executed >= n:
        return "done"
    if target is None:
        return "no_target"
    if today > target:
        return "overdue"
    if (target - today).days <= due_soon_days:
        return "due_soon"
    return "on_track"


def today_in(settings: dict) -> date:
    try:
        tz = ZoneInfo(settings.get("timezone") or "UTC")
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).date()


@dataclass
class Project:
    settings: dict
    today: date
    cms: pd.DataFrame        # una fila por contramedida
    records: pd.DataFrame    # una fila por camión × contramedida
    trucks: pd.DataFrame     # una fila por camión
    log: pd.DataFrame        # todos los eventos, del más reciente al más antiguo
    removed_cms: list[str] = field(default_factory=list)

    # ── Consultas frecuentes ────────────────────────────────────────────
    def cm_row(self, cm_id: str) -> pd.Series:
        return self.cms.set_index("cm_id").loc[cm_id]

    def cm_records(self, cm_id: str) -> pd.DataFrame:
        r = self.records[self.records.cm_id == cm_id]
        return r.iloc[sorted(range(len(r)), key=lambda i: fleet_key(r.fleet.iloc[i]))]

    def truck_records(self, fleet: str) -> pd.DataFrame:
        return self.records[self.records.fleet == fleet].sort_values("order")

    def fleets(self) -> list[str]:
        return sorted(self.records.fleet.unique().tolist(), key=fleet_key)

    def kpis(self) -> dict:
        app = self.records[self.records.status != "na"]
        n = len(app)
        executed = int(app.status.isin(["executed", "closed"]).sum())
        closed = int((app.status == "closed").sum())
        return {"n": n, "executed": executed, "closed": closed,
                "pct": executed / n if n else 0.0, "close_pct": closed / n if n else 0.0,
                "cms": len(self.cms), "cms_done": int((self.cms.status == "done").sum()),
                "cms_overdue": int((self.cms.status == "overdue").sum())}

    def alerts(self) -> list[dict]:
        """Alertas para el administrador, de la más a la menos urgente."""
        out: list[dict] = []
        for _, c in self.cms.iterrows():
            if c.status == "overdue":
                out.append({"type": "overdue", "cm": c.cm_id, "days": (self.today - c.target).days,
                            "left": c.n - c.executed})
            elif c.status == "due_soon":
                out.append({"type": "due_soon", "cm": c.cm_id, "days": (c.target - self.today).days,
                            "left": c.n - c.executed})
        recs = self.records
        late = recs[(recs.status.isin(["not_started", "in_progress"])) & recs.planned_date.notna()
                    & (recs.planned_date.map(lambda d: d is not None and d < self.today))]
        for cm_id, grp in late.groupby("cm_id"):
            out.append({"type": "planned_missed", "cm": cm_id, "fleets": sorted(grp.fleet, key=fleet_key)})
        docs = recs[recs.status == "executed"]
        for cm_id, grp in docs.groupby("cm_id"):
            out.append({"type": "docs_pending", "cm": cm_id, "fleets": sorted(grp.fleet, key=fleet_key)})
        order = {"overdue": 0, "planned_missed": 1, "due_soon": 2, "docs_pending": 3}
        return sorted(out, key=lambda a: order[a["type"]])


# ─── Construcción ─────────────────────────────────────────────────────────
def _catalog(df: pd.DataFrame) -> dict[str, dict]:
    out = {}
    for _, r in df.iterrows():
        out[r.cm_id] = {"cm_id": r.cm_id, "order": int(r.order or 0), "name": r["name"], "model": r.model,
                        "owner": r.owner, "target": r.target, "duration": r.duration, "action": r.action,
                        "steps": [s for s in str(r.steps).split("|") if s] or ["Executed"]}
    return out


def _baseline(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    out = {}
    for _, r in df.iterrows():
        out[(r.cm_id, r.fleet)] = {
            "cm_id": r.cm_id, "fleet": r.fleet, "serial": r.serial, "model": r.model,
            "planned_date": r.planned_date, "work_order": r.work_order, "exec_date": r.exec_date,
            "planned": _b(r.planned), "steps": [_b(s) for s in str(r.steps).split("|") if s != ""],
            "fir": _b(r.fir), "report": _b(r.report), "na": _b(r.na), "note": "",
            "last_user": "", "last_ts": "",
        }
    return out


def _blank(cm_id: str, fleet: str, n_steps: int, serial: str = "", model: str = "") -> dict:
    return {"cm_id": cm_id, "fleet": fleet, "serial": serial, "model": model, "planned_date": "", "work_order": "",
            "exec_date": "", "planned": False, "steps": [False] * n_steps, "fir": False, "report": False,
            "na": False, "note": "", "last_user": "", "last_ts": ""}


def _summary(ev: dict) -> str:
    """Descripción corta de un evento para el historial."""
    v = ev.get("values", {})
    if ev["kind"] == "record":
        parts = [f"{k}={v[k]}" for k in RECORD_FIELDS if k in v]
        return ", ".join(parts)
    if ev["kind"] == "scope":
        return ev.get("action", "")
    return ", ".join(f"{k}={val}" for k, val in v.items())


def build_project(snapshot: Mapping[str, bytes], today: date | None = None) -> Project:
    events = read_events(snapshot)
    settings = read_settings(snapshot, events["settings"])
    today = today or today_in(settings)
    cms = _catalog(read_catalog(snapshot))
    recs = _baseline(read_baseline(snapshot))
    removed: list[str] = []

    # Todos los eventos en orden de fecha, sin importar el tipo
    ordered = sorted((e for k in ("record", "meta", "scope") for e in events[k]), key=lambda e: e["ts"])
    for ev in ordered:
        kind = ev["kind"]
        if kind == "scope":
            action = ev.get("action")
            if action == "add_cm" and ev.get("cm"):
                vals = dict(ev.get("values", {}))
                steps = [s for s in vals.pop("steps", []) if s] or ["Executed"]
                cms[ev["cm"]] = {"cm_id": ev["cm"], "order": max([c["order"] for c in cms.values()] + [0]) + 1,
                                 "name": "", "model": "", "owner": "", "target": "", "duration": "", "action": "",
                                 **vals, "steps": steps}
                for f in ev.get("fleets", []):
                    recs[(ev["cm"], f["fleet"])] = _blank(ev["cm"], f["fleet"], len(steps), f.get("serial", ""), f.get("model", ""))
                    recs[(ev["cm"], f["fleet"])]["na"] = bool(f.get("na"))
                if ev["cm"] in removed:
                    removed.remove(ev["cm"])
            elif action == "remove_cm" and ev.get("cm") in cms:
                cms.pop(ev["cm"])
                removed.append(ev["cm"])
                for key in [k for k in recs if k[0] == ev["cm"]]:
                    recs.pop(key)
            elif action == "add_truck" and ev.get("fleet"):
                for cm_id in ev.get("cms") or list(cms):
                    if cm_id in cms and (cm_id, ev["fleet"]) not in recs:
                        recs[(cm_id, ev["fleet"])] = _blank(cm_id, ev["fleet"], len(cms[cm_id]["steps"]),
                                                            ev.get("serial", ""), ev.get("model", ""))
            elif action == "remove_truck" and ev.get("fleet"):
                for cm_id in ev.get("cms") or list(cms):
                    recs.pop((cm_id, ev["fleet"]), None)
        elif kind == "meta" and ev.get("cm") in cms:
            vals = {k: v for k, v in ev.get("values", {}).items() if k in ("name", "model", "owner", "target", "duration", "action")}
            cms[ev["cm"]].update(vals)
        elif kind == "record":
            rec = recs.get((ev.get("cm"), ev.get("fleet")))
            if rec is None:
                continue
            for k, v in ev.get("values", {}).items():
                if k == "steps":
                    steps = [bool(s) for s in v][: len(rec["steps"])]
                    rec["steps"] = steps + rec["steps"][len(steps):]
                elif k in RECORD_FIELDS:
                    rec[k] = v
            rec["last_user"], rec["last_ts"] = ev.get("user", ""), ev["ts"]

    # ── Registros ──
    rows = []
    for (cm_id, _), r in recs.items():
        if cm_id not in cms:
            continue
        c = cms[cm_id]
        rows.append({**r, "order": c["order"], "cm_name": c["name"],
                     "planned_date": _d(r["planned_date"]), "exec_date": _d(r["exec_date"]),
                     "status": record_status(r), "progress": record_progress(r)})
    cols = ["cm_id", "fleet", "serial", "model", "planned_date", "work_order", "exec_date", "planned", "steps", "fir",
            "report", "na", "note", "last_user", "last_ts", "order", "cm_name", "status", "progress"]
    records = pd.DataFrame(rows, columns=cols)

    # Modelo y serie de cada camión: el primer valor no vacío entre sus registros
    ident = {}
    for _, r in records.iterrows():
        cur = ident.setdefault(r.fleet, {"serial": "", "model": ""})
        cur["serial"] = cur["serial"] or r.serial
        cur["model"] = cur["model"] or r.model

    # ── Contramedidas ──
    due_soon = int(settings.get("due_soon_days", 45))
    cm_rows = []
    for c in sorted(cms.values(), key=lambda c: c["order"]):
        sub = records[(records.cm_id == c["cm_id"]) & (records.status != "na")]
        n = len(sub)
        counts = sub.status.value_counts()
        executed = int(counts.get("executed", 0) + counts.get("closed", 0))
        target = _d(c["target"])
        cm_rows.append({**c, "target": target, "n": n, "executed": executed,
                        "closed": int(counts.get("closed", 0)), "in_progress": int(counts.get("in_progress", 0)),
                        "not_started": int(counts.get("not_started", 0)),
                        "na": int((records[records.cm_id == c["cm_id"]].status == "na").sum()),
                        "pct": executed / n if n else 0.0, "close_pct": counts.get("closed", 0) / n if n else 0.0,
                        "status": cm_status(executed, n, target, today, due_soon),
                        "days_left": (target - today).days if target else None})
    cm_cols = ["cm_id", "order", "name", "model", "owner", "target", "duration", "action", "steps", "n", "executed",
               "closed", "in_progress", "not_started", "na", "pct", "close_pct", "status", "days_left"]
    cms_df = pd.DataFrame(cm_rows, columns=cm_cols)

    # ── Camiones ──
    t_rows = []
    for fleet in sorted(records.fleet.unique(), key=fleet_key):
        sub = records[(records.fleet == fleet) & (records.status != "na")]
        n = len(sub)
        executed = int(sub.status.isin(["executed", "closed"]).sum())
        t_rows.append({"fleet": fleet, **ident.get(fleet, {}), "n": n, "executed": executed,
                       "closed": int((sub.status == "closed").sum()), "pct": executed / n if n else 0.0})
    trucks = pd.DataFrame(t_rows, columns=["fleet", "serial", "model", "n", "executed", "closed", "pct"])

    # ── Historial ──
    names = {c: cms[c]["name"] for c in cms}
    log_rows = [{"ts": e["ts"], "user": e.get("user", ""), "kind": e["kind"], "cm_id": e.get("cm", ""),
                 "countermeasure": names.get(e.get("cm", ""), e.get("cm", "")), "fleet": e.get("fleet", ""),
                 "change": _summary(e), "note": e.get("values", {}).get("note", "") if e["kind"] == "record" else ""}
                for k in ("record", "meta", "scope", "settings") for e in events[k]]
    log = pd.DataFrame(log_rows, columns=["ts", "user", "kind", "cm_id", "countermeasure", "fleet", "change", "note"])
    log = log.sort_values("ts", ascending=False, ignore_index=True)

    return Project(settings=settings, today=today, cms=cms_df, records=records, trucks=trucks, log=log,
                   removed_cms=removed)
