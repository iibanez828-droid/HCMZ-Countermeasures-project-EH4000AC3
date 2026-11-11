"""Constantes del proyecto HCM Countermeasure Roll-out 2027.

Todo lo que define el proyecto (estados, colores, valores por defecto) vive
aquí para que cambiarlo sea editar un solo archivo. Las contramedidas en sí
son datos: vienen de seed/countermeasures_seed.csv y el administrador puede
agregar, editar o quitar contramedidas desde la app.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SEED = ROOT / "seed"
LOGO_PATH = ASSETS / "landcros_logo.webp"
TRUCK_IMAGE_PATH = ASSETS / "eh5000.webp"

PROJECT_NAME = "HCM Countermeasure Roll-out 2027"
FLEET = "EH4000AC-3 · EH3500AC-2 · EX5600-7"

# Archivos de origen (solo para seed/build_seed.py y la inicialización)
TRACKER_FILE = "Countermeasures Progress Tracker V2-19-Oct-26.xlsx"
PLAN_FILE = "HCM-Countermeasure Action & Roll out Plan.pdf"
CATALOG_SEED = SEED / "countermeasures_seed.csv"
RECORDS_SEED = SEED / "records_seed.csv"

# ─── Estados ──────────────────────────────────────────────────────────────
# Registro (camión × contramedida)
RECORD_STATUSES = ("closed", "executed", "in_progress", "not_started", "na")
# Contramedida (flota completa)
CM_STATUSES = ("done", "overdue", "due_soon", "on_track", "no_target")

# ─── Valores por defecto (editables por el administrador) ────────────────
DEFAULT_SETTINGS = {
    "timezone": "Africa/Lusaka",
    "due_soon_days": 45,   # días calendario antes de la fecha meta para avisar
}

ROLES = ("admin", "supervisor")
LANGUAGES = {"en": "English", "ja": "日本語"}

# ─── Colores (identidad LANDCROS) ─────────────────────────────────────────
ORANGE = "#FF6B00"
BLACK = "#1A1A1A"
GREY = "#888888"
LIGHT = "#F7F7F7"
STATUS_COLORS = {
    # registros
    "closed": "#2E7D32",
    "executed": "#1565C0",
    "in_progress": ORANGE,
    "not_started": "#9E9E9E",
    "na": "#D6D6D6",
    # contramedidas
    "done": "#2E7D32",
    "overdue": "#C62828",
    "due_soon": ORANGE,
    "on_track": "#1565C0",
    "no_target": "#6D4C41",
}
