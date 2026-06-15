import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

EXAMPLE_SCN = Path(__file__).parent.parent / "examples" / "scene.scn"


class _MockObserver:
    def stop(self): pass
    def join(self): pass


@pytest.fixture
def scene_dir(tmp_path):
    shutil.copy(EXAMPLE_SCN, tmp_path / "scene.scn")
    return tmp_path


@pytest.fixture
def client(tmp_path, scene_dir, monkeypatch):
    import server.main as main_module
    from server.config import Config

    monkeypatch.setattr(
        main_module, "start_watcher", lambda *a, **kw: _MockObserver()
    )

    config = Config(scene_dir=scene_dir, db_path=tmp_path / "test.db")
    app = main_module.create_app(config)
    with TestClient(app) as c:
        yield c


# ── /health ──────────────────────────────────────────────────────────────────

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["scene_count"] == 1
    assert data["scene_dir_exists"] is True


# ── GET /api/scenes ───────────────────────────────────────────────────────────

def test_list_scenes_returns_file(client):
    r = client.get("/api/scenes")
    assert r.status_code == 200
    scenes = r.json()["scenes"]
    assert len(scenes) == 1
    s = scenes[0]
    assert s["file_name"] == "scene.scn"
    assert s["file_type"] == "scene"
    assert s["has_note"] is False
    assert s["note_preview"] == ""


def test_list_scenes_no_orphans_initially(client):
    assert client.get("/api/scenes").json()["orphaned_notes"] == []


# ── GET /api/scenes/{file_path} ───────────────────────────────────────────────

def test_get_scene_structure(client):
    r = client.get("/api/scenes/scene.scn")
    assert r.status_code == 200
    data = r.json()
    assert data["file_name"] == "scene.scn"
    assert data["file_type"] == "scene"
    assert data["note"] == ""
    assert "channels" in data
    assert "1" in data["channels"]
    assert "32" in data["channels"]


def test_get_scene_channel_data(client):
    ch1 = client.get("/api/scenes/scene.scn").json()["channels"]["1"]
    assert ch1["name"] == "Diazno"
    assert ch1["color"] == "CY"
    assert ch1["eq"]["enabled"] is True
    assert ch1["eq"]["bands"][0]["type"] == "PEQ"
    assert ch1["eq"]["bands"][0]["freq"] == pytest.approx(164.4)


def test_get_scene_fader_neg_inf_is_null(client):
    # channel 4 has fader at -oo
    ch4 = client.get("/api/scenes/scene.scn").json()["channels"]["4"]
    assert ch4["fader_db"] is None


def test_get_scene_muted_channel(client):
    ch4 = client.get("/api/scenes/scene.scn").json()["channels"]["4"]
    assert ch4["on"] is False


def test_get_scene_not_found(client):
    assert client.get("/api/scenes/missing.scn").status_code == 404


def test_get_scene_returns_note_when_present(client):
    client.post("/api/notes/scene.scn", json={"note": "pre-loaded"})
    data = client.get("/api/scenes/scene.scn").json()
    assert data["note"] == "pre-loaded"


# ── GET /api/notes ────────────────────────────────────────────────────────────

def test_get_note_404_when_missing(client):
    assert client.get("/api/notes/scene.scn").status_code == 404


# ── POST /api/notes ───────────────────────────────────────────────────────────

def test_create_note(client):
    r = client.post("/api/notes/scene.scn", json={"note": "Sunday morning setup"})
    assert r.status_code == 200
    data = r.json()
    assert data["note"] == "Sunday morning setup"
    assert data["file_path"] == "scene.scn"
    assert data["file_name"] == "scene.scn"
    assert "created_at" in data
    assert "updated_at" in data


def test_get_note_after_create(client):
    client.post("/api/notes/scene.scn", json={"note": "hello"})
    r = client.get("/api/notes/scene.scn")
    assert r.status_code == 200
    assert r.json()["note"] == "hello"


def test_update_note_idempotent(client):
    client.post("/api/notes/scene.scn", json={"note": "first"})
    client.post("/api/notes/scene.scn", json={"note": "updated"})
    assert client.get("/api/notes/scene.scn").json()["note"] == "updated"


# ── DELETE /api/notes ─────────────────────────────────────────────────────────

def test_delete_note(client):
    client.post("/api/notes/scene.scn", json={"note": "to delete"})
    r = client.delete("/api/notes/scene.scn")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert client.get("/api/notes/scene.scn").status_code == 404


def test_delete_note_not_found(client):
    assert client.delete("/api/notes/scene.scn").status_code == 404


# ── note reflected in scene list ─────────────────────────────────────────────

def test_has_note_and_preview_in_list(client):
    client.post("/api/notes/scene.scn", json={"note": "first line\nsecond line"})
    r = client.get("/api/scenes")
    s = r.json()["scenes"][0]
    assert s["has_note"] is True
    assert s["note_preview"] == "first line"


# ── orphaned notes ────────────────────────────────────────────────────────────

def test_orphaned_note_appears_in_list(client):
    client.post("/api/notes/deleted.scn", json={"note": "orphaned"})
    orphaned = client.get("/api/scenes").json()["orphaned_notes"]
    assert any(o["file_path"] == "deleted.scn" for o in orphaned)


def test_empty_orphaned_note_not_surfaced(client):
    # An empty note for a missing file is not worth surfacing
    client.post("/api/notes/deleted.scn", json={"note": ""})
    orphaned = client.get("/api/scenes").json()["orphaned_notes"]
    assert not any(o["file_path"] == "deleted.scn" for o in orphaned)
