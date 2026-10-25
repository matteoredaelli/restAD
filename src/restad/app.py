"""FastAPI application factory and lifespan.

At startup the lifespan resolves the effective :class:`msad.DomainConfig`
(TOML + ``MSAD_*`` env overrides), opens a single bound LDAP connection and
stores both on ``app.state``. At shutdown it unbinds the connection.

By default a failure to connect at startup is fatal. Set
``RESTAD_LAZY_CONNECT=true`` to start anyway (the ``/health`` endpoint still
works and reports the error; data endpoints return 503 until a connection is
available).
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from msad import connect

from .config import ConfigError, resolve_domain_config
from .routers import audit, computers, contacts, groups, health, ous, users

logger = logging.getLogger("restad")

_TRUE = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Resolve config, open the LDAP connection, and tear it down on exit."""
    lazy = _env_flag("RESTAD_LAZY_CONNECT")

    config = resolve_domain_config()
    app.state.config = config
    app.state.conn = None

    try:
        app.state.conn = connect(config)
        auth = "kerberos" if config.uses_kerberos else config.user
        logger.info("Connected to the directory as %s", auth)
    except Exception as exc:
        # MsadConnectionError on bind/connect failure, but also e.g. environment
        # issues raised deeper in ldap3. In lazy mode we start anyway; otherwise
        # startup fails loudly.
        if not lazy:
            raise
        logger.warning("Startup connection failed (lazy mode, continuing): %s", exc)

    try:
        yield
    finally:
        conn = app.state.conn
        if conn is not None:
            try:
                conn.unbind()
            except Exception:  # best-effort teardown
                logger.debug("unbind on shutdown failed", exc_info=True)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    The interactive docs and schema routes (``/docs``, ``/redoc`` and
    ``/openapi.json``) are enabled by default. Set ``RESTAD_DOCS=false`` to
    disable all three (e.g. to hide the API surface in production).
    """
    docs_enabled = _env_flag("RESTAD_DOCS", default=True)

    app = FastAPI(
        title="restAD",
        version="0.1.0",
        summary="Read-only REST interface over Active Directory (msad).",
        description=(
            "A read-only HTTP API in front of the msad library. All endpoints "
            "perform LDAP searches only; no write operations are exposed."
        ),
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(computers.router)
    app.include_router(groups.router)
    app.include_router(contacts.router)
    app.include_router(ous.router)
    app.include_router(audit.router)

    @app.get("/", tags=["health"], summary="Service metadata")
    def root() -> dict[str, str]:
        return {
            "service": "restAD",
            "version": "0.1.0",
            "docs": "/docs" if docs_enabled else "disabled",
        }

    return app


# Module-level app for `uvicorn restad.app:app` and ASGI servers.
app = create_app()


__all__ = ["app", "create_app", "lifespan", "ConfigError"]
