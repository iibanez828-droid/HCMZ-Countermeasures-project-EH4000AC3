"""Piezas de interfaz compartidas por las vistas de supervisor y administrador."""

from __future__ import annotations

import html
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from core import config
from core.auth import USERS_PATH, User, check_password, dump_users, hash_password, stamp
from core.project import Project
from storage.base import StorageError, Store

T = Callable[..., str]


@dataclass
class Ctx:
    store: Store
    project: Project
    user: User
    users: dict[str, User]
    lang: str
    t: T

    @property
    def can_admin(self) -> bool:
        return self.user.is_admin or self.user.is_master


# ─── Formatos ─────────────────────────────────────────────────────────────
def fmt_date(d: date | None) -> str:
    return d.strftime("%d-%b-%Y") if isinstance(d, date) else "—"


def fmt_pct(p: float) -> str:
    return f"{p * 100:.0f}%"


def fmt_ts(ts: str, tz: str) -> str:
    """Fecha-hora UTC guardada → hora local del proyecto."""
    if not ts:
        return "—"
    try:
        return pd.Timestamp(ts).tz_convert(tz).strftime("%d-%b-%Y %H:%M")
    except Exception:
        return ts[:16].replace("T", " ")


def esc(text: object) -> str:
    return html.escape(str(text))


def user_name_plain(users: dict[str, User], username: str) -> str:
    """Nombre completo de un usuario sin sesión (vista pública)."""
    u = users.get(username)
    return u.name if u else (username or "—")


def user_name(ctx: Ctx, username: str) -> str:
    u = ctx.users.get(username)
    if u:
        return u.name
    if ctx.user.username == username:
        return ctx.user.name
    return username or "—"


# ─── Bloques visuales ─────────────────────────────────────────────────────
def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{esc(title)}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="lc-note">{text}</div>', unsafe_allow_html=True)


def pill_html(t: T, status: str, prefix: str = "st_") -> str:
    color = config.STATUS_COLORS.get(status, "#888")
    fg = "#1A1A1A" if status == "na" else "#fff"
    return f'<span class="pill" style="background:{color};color:{fg}!important">{esc(t(prefix + status))}</span>'


def kpi_cards(items: list[tuple[str, str, str, str]]) -> None:
    """items: (etiqueta, valor, subtítulo, color: ''|'red'|'green'|'blue')."""
    cards = "".join(
        f'<div class="kpi-card {c}"><div class="kpi-label">{esc(l)}</div>'
        f'<div class="kpi-value">{esc(v)}</div><div class="kpi-sub">{esc(s)}</div></div>'
        for l, v, s, c in items
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def fleet_kpis(t: T, p: Project) -> None:
    k = p.kpis()
    kpi_cards([
        (t("kpi_executed"), fmt_pct(k["pct"]), t("kpi_executed_sub", e=k["executed"], n=k["n"]), ""),
        (t("kpi_closed"), fmt_pct(k["close_pct"]), t("kpi_closed_sub"), "green"),
        (t("kpi_cms_done"), f"{k['cms_done']} / {k['cms']}", t("kpi_cms_done_sub"), "blue"),
        (t("kpi_overdue"), str(k["cms_overdue"]), t("kpi_overdue_sub"), "red"),
    ])


def cm_badge(ctx: Ctx, cm_id: str) -> None:
    t, c = ctx.t, ctx.project.cm_row(cm_id)
    target = fmt_date(c.target)
    if c.days_left is not None and c.status != "done":
        target += f" ({t('days_left', d=int(c.days_left))})" if c.days_left >= 0 else f" ({t('days_late', d=-int(c.days_left))})"
    parts = [
        f'<div class="truck-badge-dt" style="font-size:1.5rem">{esc(c["name"])}</div>',
        f'<div><div class="truck-badge-label">{esc(t("status"))}</div><div>{pill_html(t, c.status, "cst_")}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("executed"))}</div><div class="truck-badge-val">{c.executed} / {c.n} · {fmt_pct(c.pct)}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("closed_out"))}</div><div class="truck-badge-val">{c.closed}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("responsible"))}</div><div class="truck-badge-val">{esc(c.owner or "—")}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("target"))}</div><div class="truck-badge-val">{esc(target)}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("duration"))}</div><div class="truck-badge-val">{esc(c.duration or "—")}</div></div>',
    ]
    sep = '<div class="truck-badge-sep"></div>'
    st.markdown(f'<div class="truck-badge">{sep.join(parts)}</div>', unsafe_allow_html=True)
    if c.action:
        note(f"<b>{esc(t('action_required'))}:</b> {esc(c.action)}")


def truck_badge(ctx: Ctx, fleet: str) -> None:
    t, p = ctx.t, ctx.project
    tr = p.trucks.set_index("fleet").loc[fleet]
    parts = [
        f'<div class="truck-badge-dt">{esc(fleet)}</div>',
        f'<div><div class="truck-badge-label">{esc(t("model"))}</div><div class="truck-badge-val">{esc(tr.model or "—")}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("serial"))}</div><div class="truck-badge-val">{esc(tr.serial or "—")}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("executed"))}</div><div class="truck-badge-val">{tr.executed} / {tr.n} · {fmt_pct(tr.pct)}</div></div>',
        f'<div><div class="truck-badge-label">{esc(t("closed_out"))}</div><div class="truck-badge-val">{tr.closed}</div></div>',
    ]
    sep = '<div class="truck-badge-sep"></div>'
    st.markdown(f'<div class="truck-badge">{sep.join(parts)}</div>', unsafe_allow_html=True)


def cm_label(ctx: Ctx, cm_id: str) -> str:
    c = ctx.project.cm_row(cm_id)
    return f"{c.order}. {c['name']} · {fmt_pct(c.pct)}"


def truck_label(ctx: Ctx, fleet: str) -> str:
    tr = ctx.project.trucks.set_index("fleet").loc[fleet]
    return f"{fleet} · {tr.model or '—'} · {fmt_pct(tr.pct)}"


# ─── Guardado con manejo de errores ───────────────────────────────────────
def safe_write(ctx: Ctx, fn: Callable[[], object], success: str) -> bool:
    try:
        with st.spinner(ctx.t("saving")):
            fn()
    except StorageError as exc:
        st.error(f"{ctx.t('save_failed')} {exc}", icon=":material/error:")
        return False
    st.session_state["flash"] = success
    return True


def show_flash() -> None:
    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg, icon=":material/check_circle:")


# ─── PDF con registro de impresión ────────────────────────────────────────
PUBLIC_USER = "public"


def new_report_id() -> str:
    """ID único del reporte impreso, p. ej. RPT-20261113-101530-4F2A."""
    import secrets
    from datetime import datetime, timezone
    return f"RPT-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{secrets.token_hex(2).upper()}"


def _log_print(store: Store, username: str, report_id: str, kind: str, fleet: str, key: str) -> None:
    """Callback del botón: guarda el registro de impresión y prepara un ID nuevo para la próxima."""
    from core.events import write_event
    try:
        write_event(store, "report", {"report": kind, "report_id": report_id, "fleet": fleet,
                                      "values": {"report": kind, "report_id": report_id}},
                    username or PUBLIC_USER, report_id)
    except StorageError:
        pass  # la descarga no debe fallar si no se pudo registrar
    st.session_state[f"rid_{key}"] = new_report_id()


def pdf_download(where, label: str, build: Callable[[str, str], bytes], file_name: str, key: str, *,
                 store: Store, user: User | None, kind: str, fleet: str = "", icon: str = ":material/picture_as_pdf:",
                 printed_by_public: str = "Public view") -> None:
    """Botón de descarga de un PDF con ID de reporte. Cada descarga queda en el historial
    (tipo «report»): ID, tipo de reporte, camión y usuario («public» si no inició sesión)."""
    rid = st.session_state.setdefault(f"rid_{key}", new_report_id())
    printed_by = f"{user.name} ({user.username})" if user else printed_by_public
    where.download_button(label, build(rid, printed_by), file_name=file_name, mime="application/pdf", icon=icon,
                          width="stretch", key=key, on_click=_log_print,
                          args=(store, user.username if user else PUBLIC_USER, rid, kind, fleet, key))


# ─── Cambio de contraseña propia ──────────────────────────────────────────
def password_form(ctx: Ctx, key: str) -> None:
    """Cada usuario solo puede cambiar su propia contraseña."""
    t, user = ctx.t, ctx.user
    with st.form(key, clear_on_submit=True):
        old = st.text_input(t("current_password"), type="password")
        new = st.text_input(t("new_password"), type="password", help=t("password_help"))
        new2 = st.text_input(t("confirm_password"), type="password")
        if st.form_submit_button(t("save"), icon=":material/key:"):
            if not check_password(old, user.hash):
                st.error(t("err_current_password"))
            elif len(new) < 8:
                st.error(t("err_password_short"))
            elif new != new2:
                st.error(t("err_password_match"))
            else:
                updated = dict(ctx.users)
                updated[user.username] = stamp(User(**{**vars(user), "hash": hash_password(new)}))
                try:
                    ctx.store.write(USERS_PATH, dump_users(updated), f"[app] cambio de contraseña · {user.username}")
                    st.success(t("password_changed"))
                except StorageError as exc:
                    st.error(f"{t('save_failed')} {exc}")
