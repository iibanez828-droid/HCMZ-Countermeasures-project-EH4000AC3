"""Pruebas de las reglas de negocio (core/), en una carpeta local temporal."""

from datetime import date

import pytest

from core.events import initialize, write_event
from core.executive_report import build_executive_pdf
from core.project import build_project, cm_status, fleet_key, record_progress, record_status
from core.reports import build_excel, status_csv
from storage.local_store import LocalStore

TODAY = date(2026, 11, 9)


@pytest.fixture
def store(tmp_path):
    s = LocalStore(tmp_path / "data")
    initialize(s, "tester")
    return s


def project(store, today=TODAY):
    return build_project(store.snapshot(), today=today)


# ─── Reglas puras ─────────────────────────────────────────────────────────
def test_record_status_rules():
    assert record_status({"na": True, "steps": [True]}) == "na"
    assert record_status({"steps": [True, True], "fir": True, "report": True}) == "closed"
    assert record_status({"steps": [True, True], "fir": True}) == "executed"
    assert record_status({"steps": [True, False]}) == "in_progress"
    assert record_status({"planned": True, "steps": [False]}) == "in_progress"
    assert record_status({"steps": [False]}) == "not_started"


def test_record_progress_matches_excel():
    # Excel: Planned + RHS + LHS sin FIR ni reporte = 3/5 = 60 %
    assert record_progress({"planned": True, "steps": [True, True]}) == pytest.approx(0.6)
    # Un solo paso: Planned = 25 %
    assert record_progress({"planned": True, "steps": [False]}) == pytest.approx(0.25)


def test_cm_status():
    assert cm_status(10, 10, None, TODAY, 45) == "done"
    assert cm_status(5, 10, None, TODAY, 45) == "no_target"
    assert cm_status(5, 10, date(2026, 10, 1), TODAY, 45) == "overdue"
    assert cm_status(5, 10, date(2026, 12, 1), TODAY, 45) == "due_soon"
    assert cm_status(5, 10, date(2027, 6, 1), TODAY, 45) == "on_track"


def test_fleet_sort_is_natural():
    assert sorted(["RD100", "RD9", "RD20"], key=fleet_key) == ["RD9", "RD20", "RD100"]


# ─── Datos de origen ──────────────────────────────────────────────────────
def test_seed_loads_all_countermeasures(store):
    p = project(store)
    assert len(p.cms) == 20
    assert len(p.records) > 1000
    trailing = p.cm_row("trailing-arm")
    assert trailing.status == "done" and trailing.pct == 1.0
    # Las contramedidas de soldadura de nariz tienen dos pasos: RHS y LHS
    assert list(p.cm_row("nose-front").steps) == ["RHS Front", "LHS Front"]
    # RD220–RD227 sin estado en el Excel → N/A en el puntal delantero
    rec = p.records[(p.records.cm_id == "strut") & (p.records.fleet == "RD220")].iloc[0]
    assert rec.status == "na"


# ─── Eventos ──────────────────────────────────────────────────────────────
def test_record_event_updates_status_and_history(store):
    write_event(store, "record", {"cm": "handrail", "fleet": "RD168",
                                  "values": {"planned": True, "steps": [True], "exec_date": "2026-11-09"}}, "sam", "x")
    p = project(store)
    rec = p.records[(p.records.cm_id == "handrail") & (p.records.fleet == "RD168")].iloc[0]
    assert rec.status == "executed"
    assert rec.exec_date == date(2026, 11, 9)
    assert rec.last_user == "sam"
    assert p.log.iloc[0].fleet == "RD168"


def test_last_write_wins(store):
    write_event(store, "record", {"cm": "handrail", "fleet": "RD168", "values": {"note": "first"}}, "a", "x")
    write_event(store, "record", {"cm": "handrail", "fleet": "RD168", "values": {"note": "second"}}, "b", "x")
    rec = project(store).records.query("cm_id == 'handrail' and fleet == 'RD168'").iloc[0]
    assert rec.note == "second" and rec.last_user == "b"


def test_meta_event_changes_plan(store):
    write_event(store, "meta", {"cm": "handrail", "values": {"target": "2027-02-28", "owner": "Tada"}}, "ana", "x")
    c = project(store).cm_row("handrail")
    assert c.target == date(2027, 2, 28) and c.status == "on_track"


def test_scope_add_and_remove_truck(store):
    write_event(store, "scope", {"action": "add_truck", "fleet": "RD232", "serial": "50189", "model": "EH4000AC-3",
                                 "cms": ["handrail", "mirror"]}, "ana", "RD232")
    p = project(store)
    assert set(p.truck_records("RD232").cm_id) == {"handrail", "mirror"}
    write_event(store, "scope", {"action": "remove_truck", "fleet": "RD232", "cms": ["mirror"]}, "ana", "RD232")
    assert set(project(store).truck_records("RD232").cm_id) == {"handrail"}


def test_scope_add_and_remove_countermeasure(store):
    p = project(store)
    fleets = [{"fleet": r.fleet, "serial": r.serial, "model": r.model, "na": bool(r.na)}
              for _, r in p.cm_records("handrail").iterrows()]
    write_event(store, "scope", {"action": "add_cm", "cm": "rear-axle", "fleets": fleets,
                                 "values": {"name": "Rear Axle Weld", "target": "2027-05-01", "steps": ["RHS", "LHS"]}},
                "ana", "rear-axle")
    p = project(store)
    assert p.cm_row("rear-axle").n == p.cm_row("handrail").n
    assert list(p.cm_row("rear-axle").steps) == ["RHS", "LHS"]
    write_event(store, "scope", {"action": "remove_cm", "cm": "rear-axle"}, "ana", "rear-axle")
    p = project(store)
    assert "rear-axle" not in set(p.cms.cm_id) and "rear-axle" in p.removed_cms


def test_settings_event(store):
    write_event(store, "settings", {"values": {"due_soon_days": 90}}, "ana")
    p = project(store)
    assert p.settings["due_soon_days"] == 90
    assert p.cm_row("nose-front").status == "due_soon"  # meta 31-Dec-26 está a 52 días


def test_alerts_include_overdue(store):
    types = {a["type"] for a in project(store).alerts()}
    assert "overdue" in types and "docs_pending" in types


def test_corrupt_event_is_ignored(store):
    store.write("log/record/2026-11/bad.json", b"{not json", "test")
    assert len(project(store).cms) == 20


# ─── Usuarios ─────────────────────────────────────────────────────────────
def test_authenticate():
    from core.auth import User, authenticate, hash_password
    users = {"ana": User("ana", "Ana", "admin", hash_password("admin-pass")),
             "old": User("old", "Old", "supervisor", hash_password("old-pass1"), active=False)}
    assert authenticate(users, "ANA ", "admin-pass").username == "ana"
    assert authenticate(users, "ana", "wrong-pass") is None
    assert authenticate(users, "old", "old-pass1") is None


# ─── Reportes ─────────────────────────────────────────────────────────────
def test_reports_build(store):
    p = project(store)
    assert build_excel(p)[:2] == b"PK"
    assert build_executive_pdf(p)[:4] == b"%PDF"
    assert status_csv(p).decode("utf-8-sig").startswith("Countermeasure,Fleet")
