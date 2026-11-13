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


# ─── Gantt ────────────────────────────────────────────────────────────────
def test_timeline_matches_pdf_colors_and_bounds(store):
    from core import config
    from core.project import timeline
    p = project(store)
    tl = timeline(p).set_index("cm_id")
    assert len(tl) == 20
    assert tl.loc["trailing-arm", "color"] == config.STATUS_COLORS["done"]      # 100 % → verde
    assert tl.loc["panto-a", "color"] == config.STATUS_COLORS["overdue"]        # vencida → rojo
    assert tl.loc["nose-front", "color"] == config.STATUS_COLORS["in_progress"]  # en curso → naranja
    assert (tl.start < tl.end).all() and (tl.fill_end >= tl.start).all() and (tl.fill_end <= tl.end).all()
    assert not tl.loc["handrail", "has_target"]


def test_truck_timeline_and_scoreboard(store):
    from core import config
    from core.project import record_bar_status, truck_scoreboard, truck_timeline
    assert record_bar_status("closed", None, TODAY) == "done"
    assert record_bar_status("in_progress", date(2026, 1, 1), TODAY) == "overdue"
    assert record_bar_status("not_started", date(2027, 1, 1), TODAY) == "in_progress"
    write_event(store, "record", {"cm": "handrail", "fleet": "RD168", "values": {"planned_date": "2026-12-01"}}, "sam", "x")
    p = project(store)
    tl = truck_timeline(p, "RD168")
    recs = p.truck_records("RD168")
    assert len(tl) == int((recs.status != "na").sum())                       # sin N/A
    row = tl.set_index("cm_id").loc["trailing-arm"]
    assert row.color == config.STATUS_COLORS["done"] and row.fill_end <= row.end
    s = truck_scoreboard(p, "RD168")
    assert s["executed"] + s["pending"] == s["n"]
    assert s["next_date"] == date(2026, 12, 1) and s["last_user"] == "sam"


# ─── Horas de trabajo ─────────────────────────────────────────────────────
def test_parse_and_remaining_hours():
    from core.project import parse_hours, remaining_hours
    assert parse_hours("12 h") == 12 and parse_hours("2,5 hrs") == 2.5 and parse_hours("") is None
    assert remaining_hours({"steps": [False, False]}, 12) == 12
    assert remaining_hours({"steps": [True, False]}, 12) == 6          # RHS hecho, LHS pendiente
    assert remaining_hours({"steps": [True, True]}, 12) == 0           # ejecutado
    assert remaining_hours({"steps": [False], "na": True}, 12) == 0    # N/A
    assert remaining_hours({"steps": [False]}, None) == 0              # sin estimación


def test_hours_update_with_meta_and_status(store):
    from core.project import forecast, truck_downtime
    p = project(store)
    c = p.cm_row("mirror")
    assert c.hours == 12 and c.remaining_h == pytest.approx(12 * c.pending_n)
    total = forecast(p)["remaining_h"]
    assert total == pytest.approx(p.cms.remaining_h.sum())
    # El administrador cambia las horas → todo se recalcula
    write_event(store, "meta", {"cm": "mirror", "values": {"duration": "20 h"}}, "ana", "mirror")
    p2 = project(store)
    assert p2.cm_row("mirror").remaining_h == pytest.approx(20 * c.pending_n)
    assert forecast(p2)["remaining_h"] == pytest.approx(total + 8 * c.pending_n)
    # Un camión ejecuta la contramedida → sus horas salen del pendiente
    fleet = p2.cm_records("mirror").query("status not in ['executed', 'closed', 'na']").fleet.iloc[0]
    before = truck_downtime(p2, fleet)["hours"]
    write_event(store, "record", {"cm": "mirror", "fleet": fleet, "values": {"steps": [True]}}, "sam", "x")
    p3 = project(store)
    assert truck_downtime(p3, fleet)["hours"] == pytest.approx(before - 20)
    assert p3.cm_row("mirror").remaining_h == pytest.approx(20 * (c.pending_n - 1))


def test_forecast_uses_capacity(store):
    from core.project import forecast
    write_event(store, "settings", {"values": {"hours_per_day": 10, "parallel_trucks": 2}}, "ana")
    p = project(store)
    f = forecast(p)
    import math
    assert f["days"] == math.ceil(f["remaining_h"] / 20) and f["finish"] > p.today
    assert "RHS Handrail Reinforcement" in f["no_estimate"]          # sin duración en el plan


def test_pdf_reports_with_gantt(store):
    import re
    from core.executive_report import build_truck_pdf
    p = project(store)
    plan = build_executive_pdf(p)
    assert plan[:4] == b"%PDF" and len(re.findall(rb"/Type\s*/Page[^s]", plan)) >= 2   # Gantt + lista
    truck = build_truck_pdf(p, "RD200")
    assert truck[:4] == b"%PDF" and len(re.findall(rb"/Type\s*/Page[^s]", truck)) >= 2  # Gantt + detalle


def test_completion_assumes_two_trucks_by_default(store):
    from core.i18n import translator
    from core.project import forecast, trucks_phrase
    f = forecast(project(store))
    assert f["parallel"] == 2                                   # valor por defecto
    assert trucks_phrase(1) == "one truck" and trucks_phrase(2) == "two trucks"
    text = translator("en")("fc_finish_sub", trucks=trucks_phrase(2), n="2")
    assert text == "Based on continuous work on two trucks in parallel, without any delays"


# ─── Registro de impresión y nombres de usuario ───────────────────────────
def test_username_ignores_spaces_and_case():
    from core.auth import User, authenticate, hash_password, normalize_username
    users = {"peter1": User("peter1", "Peter", "admin", hash_password("Dummy-pass-9"))}
    assert normalize_username(" Peter 1 ") == "peter1"
    assert authenticate(users, "Peter 1", "Dummy-pass-9").username == "peter1"
    assert authenticate(users, "PETER1", "dummy-pass-9") is None             # la contraseña sí distingue mayúsculas


def test_print_register_and_report_id(store):
    import io
    from pypdf import PdfReader
    from core.executive_report import build_truck_pdf
    write_event(store, "report", {"report": "truck report", "report_id": "RPT-TEST-0001", "fleet": "RD200",
                                  "values": {"report": "truck report", "report_id": "RPT-TEST-0001"}}, "marcos1", "x")
    p = project(store)
    row = p.log.iloc[0]
    assert row.kind == "report" and row.user == "marcos1" and row.fleet == "RD200"
    assert "RPT-TEST-0001" in row.change and "truck report" in row.change
    pdf = build_truck_pdf(p, "RD200", None, "RPT-TEST-0002", "Marcos (marcos1)")
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "Report ID RPT-TEST-0002" in text and "Printed by Marcos (marcos1)" in text
