import pytest


def test_to_bool_variants() -> None:
    from md2docx.web import _to_bool

    assert _to_bool("true")
    assert _to_bool("1")
    assert _to_bool("yes")
    assert not _to_bool("false")
    assert not _to_bool("0")


def test_health_endpoint() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from md2docx.web import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

