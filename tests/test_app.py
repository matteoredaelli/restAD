"""Smoke tests for restAD that do not require a live Active Directory.

They exercise configuration resolution, the OpenAPI surface (read-only: every
operation must be a GET) and the lazy-connect startup path where the directory
is unreachable.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from restad.app import create_app
from restad.config import ConfigError, resolve_domain_config

# A config that is valid to *build* but points at an unresolvable host, so the
# connection fails fast without contacting a real directory.
_FAKE_ENV = {
    "MSAD_HOST": "dc.invalid.example",
    "MSAD_BASE": "dc=example,dc=com",
    "MSAD_PORT": "636",
    "MSAD_USE_SSL": "true",
    "MSAD_USER": "svc_reader",
    "MSAD_PASSWORD": "dummy",
    "RESTAD_LAZY_CONNECT": "true",
}


def test_env_overrides_win() -> None:
    cfg = resolve_domain_config(env=_FAKE_ENV)
    assert cfg.host == "dc.invalid.example"
    assert cfg.base == "dc=example,dc=com"
    assert cfg.port == 636
    assert cfg.use_ssl is True
    assert cfg.user == "svc_reader"
    assert cfg.uses_kerberos is False


def test_missing_required_fields_raise() -> None:
    with pytest.raises(ConfigError):
        resolve_domain_config(env={"MSAD_CONFIG_FILE": "/nonexistent/none.toml"})


def test_kerberos_when_no_credentials() -> None:
    cfg = resolve_domain_config(env={"MSAD_HOST": "dc.x", "MSAD_BASE": "dc=x"})
    assert cfg.uses_kerberos is True


def test_openapi_is_read_only() -> None:
    app = create_app()
    schema = app.openapi()
    methods = {m.upper() for ops in schema["paths"].values() for m in ops}
    assert methods == {"GET"}, f"Non-GET operations exposed: {methods}"


def test_docs_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESTAD_DOCS", raising=False)
    for key, value in _FAKE_ENV.items():
        monkeypatch.setenv(key, value)
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/").json()["docs"] == "/docs"


def test_docs_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _FAKE_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("RESTAD_DOCS", "false")
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        # The API itself still works.
        assert client.get("/").json()["docs"] == "disabled"
        assert client.get("/users?limit=1").status_code == 503


def test_lazy_startup_and_health(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _FAKE_ENV.items():
        monkeypatch.setenv(key, value)

    app = create_app()
    with TestClient(app) as client:
        # Root is always available.
        assert client.get("/").status_code == 200

        # Data endpoints are unavailable without a bound connection.
        assert client.get("/users?limit=1").status_code == 503

        # Health never 500s: it reports the failure as ok=false.
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["ok"] is False
        assert body["error"]
