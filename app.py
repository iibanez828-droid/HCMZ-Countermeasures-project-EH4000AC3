"""HCM Countermeasure Roll-out 2027 — seguimiento de las contramedidas HCM en la flota FQM
(EH4000AC-3, EH3500AC-2 y EX5600-7).

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import time

import streamlit as st

from core import config
from core.auth import User, authenticate, load_users, master_account
from core.events import initialize, is_initialized
from core.executive_report import build_executive_pdf
from core.i18n import translator
from core.project import build_project
from storage import StorageError, local_dir, make_store
from ui import admin, supervisor
from ui.common import Ctx, fleet_kpis, note, password_form, pdf_download, section, show_flash
from ui.gantt import gantt_view, truck_view
from ui.matrix import action_plan_table, matrix_view
from ui.theme import footer, header, inject_css, sidebar_logo

st.set_page_config(page_title=config.PROJECT_NAME, page_icon=str(config.LOGO_PATH), layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
ss = st.session_state
ss.setdefault("lang", "en")
t = translator(ss.lang)


# ─── Datos ────────────────────────────────────────────────────────────────
def _secrets() -> dict:
    try:
        return {k: dict(v) if hasattr(v, "keys") else v for k, v in st.secrets.items()}
    except Exception:  # sin archivo de secretos → modo local
        return {}


@st.cache_resource(show_spinner=False)
def get_store(_secrets_dict: dict, local_path: str):
    # local_path forma parte de la clave del caché: si cambia la carpeta local, se crea otro almacenamiento
    return make_store(_secrets_dict)


@st.cache_data(show_spinner=False, max_entries=4)
def load_state(_store, version: int, bucket: int):
    """Lee los datos (una descarga) y calcula el estado del proyecto.
    Se renueva al guardar (version) o cada 30 s (bucket) para ver lo que
    guardan los demás usuarios."""
    snapshot = _store.snapshot()
    project = build_project(snapshot) if is_initialized(snapshot) else None
    return snapshot, project


store = get_store(_secrets(), str(local_dir()))
try:
    with st.spinner(t("loading")):
        snapshot, project = load_state(store, store.version, int(time.time() // 30))
except StorageError as exc:
    header(config.PROJECT_NAME, config.FLEET)
    st.error(f"{t('load_failed')} {exc}", icon=":material/cloud_off:")
    if st.button(t("retry"), icon=":material/refresh:"):
        load_state.clear()
        st.rerun()
    st.stop()

users = load_users(snapshot)
master = master_account(_secrets())


def language_picker(where) -> None:
    choice = where.segmented_control(t("language"), list(config.LANGUAGES), default=ss.lang,
                                     format_func=lambda k: config.LANGUAGES[k], key="lang_pick")
    if choice and choice != ss.lang:
        ss.lang = choice
        st.rerun()


# ─── Vista pública (sin usuario) e inicio de sesión ───────────────────────
def login_form() -> None:
    with st.container(border=True):
        st.subheader(t("login"), anchor=False)
        language_picker(st)
        with st.form("login"):
            username = st.text_input(t("username"))
            pw = st.text_input(t("password"), type="password")
            if st.form_submit_button(t("login"), type="primary", width="stretch", icon=":material/login:"):
                user = authenticate(users, username, pw, master)
                if user:
                    ss.user = user
                    ss.pop("login_fail", None)
                    st.rerun()
                ss.login_fail = ss.get("login_fail", 0) + 1
                time.sleep(min(ss.login_fail, 5))  # frena intentos repetidos
                st.error(t("login_failed"))
        st.caption(t("login_help"))


def public_page() -> None:
    """View: cualquiera con el link ve el plan de acción y la matriz (solo lectura); el inicio de sesión va a la derecha."""
    header(config.PROJECT_NAME, f"{config.FLEET} · {t('public_subtitle')}")
    view_col, login_col = st.columns([3.3, 1], gap="large")
    with login_col:
        login_form()
    with view_col:
        if project is None:
            note(t("not_initialized"))
            return
        note(t("public_help"))
        fleet_kpis(t, project)
        section(t("gantt"))
        gantt_view(project, t, "pub_gantt")
        section(t("truck_view"))
        truck_view(project, t, "pub_truck", users, store=store)
        c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
        with c1:
            section(t("action_plan"))
        pdf_download(c2, t("dl_pdf"), lambda rid, by: build_executive_pdf(project, rid, by),
                     f"HCM_Countermeasure_Action_Plan_{project.today:%Y%m%d}.pdf", "pub_plan_pdf",
                     store=store, user=None, kind="action plan", icon=":material/print:",
                     printed_by_public=t("public_user"))
        action_plan_table(project, t, "pub_plan")
        section(t("tab_matrix"))
        matrix_view(project, t, "pub_matrix")
    footer(f"LANDCROS · {config.PROJECT_NAME}", t("public_footer"))


if "user" not in ss:
    public_page()
    st.stop()

# La sesión se valida contra el archivo de usuarios en cada carga: si el dueño
# desactiva a alguien o le cambia el rol, el cambio aplica en el siguiente clic.
user: User = ss.user
if user.is_master:
    if not master or master.username != user.username:
        ss.clear()
        st.rerun()
    user = ss.user = master
elif user.username in users and users[user.username].active and not (master and user.username == master.username):
    user = ss.user = users[user.username]
else:
    ss.clear()
    st.rerun()
ctx = Ctx(store=store, project=project, user=user, users=users, lang=ss.lang, t=t)

# ─── Barra lateral ────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_logo()
    st.markdown(f'<div class="side-user">{user.name}</div><span class="side-role">{t("role_" + user.role)}</span>',
                unsafe_allow_html=True)
    st.write("")
    language_picker(st)
    # Cada rol ve solo su vista; únicamente el maestro puede alternar entre ambas
    view = "admin" if user.is_admin else "supervisor"
    if user.is_master:
        view = st.segmented_control(t("view"), ["admin", "supervisor"], default="admin", key="view_pick",
                                    format_func=lambda v: t("view_" + v)) or "admin"
    st.divider()
    if st.button(t("refresh"), icon=":material/refresh:", width="stretch", help=t("refresh_help")):
        load_state.clear()
        st.rerun()
    # Los administradores cambian su contraseña en la pestaña de configuración;
    # la del maestro está en los secretos
    if user.role == "supervisor":
        with st.expander(t("change_password"), icon=":material/key:"):
            password_form(ctx, "chg_pw")
    if st.button(t("logout"), icon=":material/logout:", width="stretch"):
        lang = ss.lang
        ss.clear()
        ss.lang = lang
        st.rerun()
    st.caption(f"{t('data_source')}: {store.label}")
    if project is not None:
        st.caption(f"{t('today')}: {project.today:%d-%b-%Y} ({project.settings.get('timezone')})")

# ─── Contenido ────────────────────────────────────────────────────────────
show_flash()
subtitle = t("subtitle_admin") if view == "admin" else t("subtitle_supervisor")
header(config.PROJECT_NAME, f"{config.FLEET} · {subtitle}")
if project is None:
    if user.is_admin or user.is_master:
        note(t("init_help"))
        if st.button(t("init_button"), type="primary", icon=":material/rocket_launch:"):
            try:
                with st.spinner(t("saving")):
                    initialize(store, user.username)
            except StorageError as exc:
                st.error(f"{t('save_failed')} {exc}")
            else:
                load_state.clear()
                st.rerun()
    else:
        note(t("not_initialized"))
    st.stop()

if view == "admin":
    admin.render(ctx)
else:
    supervisor.render(ctx)

footer(f"LANDCROS · {config.PROJECT_NAME}", f"{len(project.cms)} countermeasures · {len(project.trucks)} machines")
