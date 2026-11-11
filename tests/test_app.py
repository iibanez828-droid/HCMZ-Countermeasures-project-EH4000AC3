"""Pruebas de la app completa con AppTest (modo local en una carpeta temporal)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def at(tmp_path, monkeypatch):
    monkeypatch.setenv("CM_LOCAL_DIR", str(tmp_path / "data"))
    import streamlit as st
    from core.auth import USERS_PATH, User, dump_users, hash_password
    from core.events import initialize
    from storage.local_store import LocalStore
    st.cache_resource.clear()
    st.cache_data.clear()
    store = LocalStore(tmp_path / "data")
    users = {"ana": User("ana", "Ana Admin", "admin", hash_password("admin-pass")),
             "sam": User("sam", "Sam Sup", "supervisor", hash_password("sup-pass1")),
             "old": User("old", "Old User", "supervisor", hash_password("old-pass1"), active=False)}
    store.write(USERS_PATH, dump_users(users), "test")
    initialize(store, "ana")
    app = AppTest.from_file(APP, default_timeout=90)
    app.secrets["master"] = {"username": "iibanez", "name": "Ivan", "password_hash": hash_password("master-pass-1")}
    return app


def _as(at, username):
    """Inicia sesión colocando el usuario en la sesión (una sola ejecución).
    El clic en el formulario se prueba en test_core.py (authenticate); el arnés de
    pruebas de Streamlit 1.51 falla al repetir ejecuciones con segmented_control."""
    from core.auth import User, load_users
    from storage.local_store import LocalStore
    import os
    users = load_users(LocalStore(Path(os.environ["CM_LOCAL_DIR"])).snapshot())
    at.session_state["user"] = users.get(username) or User(username, "Ivan", "master", "")
    at.run()
    return at


def _md(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_public_view_shows_plan_without_login(at):
    at.run()
    assert not at.exception
    assert "Fleet executed" in _md(at)
    assert len(at.dataframe) >= 2  # plan de acción + matriz
    assert [b.label for b in at.button] == ["Sign in"]
    assert not at.tabs


def test_admin_sees_all_tabs(at):
    _as(at, "ana")
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Summary", "Top page", "Progress", "Countermeasures", "Trucks", "Reports", "Settings"]
    assert "Past the fleet target" in _md(at)


def test_supervisor_sees_progress_editor_only(at):
    _as(at, "sam")
    assert not at.exception
    assert not at.tabs
    assert any(b.label == "Save changes" for b in at.button)


def test_inactive_user_is_signed_out(at):
    _as(at, "old")
    assert "user" not in at.session_state


def test_master_without_secret_is_signed_out(at):
    _as(at, "someone-else")
    assert "user" not in at.session_state


def test_japanese_interface(at):
    at.session_state["lang"] = "ja"
    _as(at, "ana")
    assert not at.exception
    assert [t.label for t in at.tabs][0] == "概要"
