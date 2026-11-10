# restAD - Read-only REST interface over the msad Active Directory library
# Copyright (C) 2026 - matteo.redaelli@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Shared FastAPI dependencies.

The LDAP connection and resolved configuration are created once during the
application lifespan (see :mod:`restad.app`) and stored on ``app.state``. These
dependencies expose them to the route handlers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from msad import DomainConfig
from msad.types import LdapConnection


def get_config(request: Request) -> DomainConfig:
    """Return the resolved domain configuration from app state."""
    config: DomainConfig | None = getattr(request.app.state, "config", None)
    if config is None:  # pragma: no cover - should not happen after lifespan
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration not initialized.",
        )
    return config


def get_base(config: Annotated[DomainConfig, Depends(get_config)]) -> str:
    """Return the configured search base DN."""
    return config.base


def get_connection(request: Request) -> LdapConnection:
    """Return the shared bound LDAP connection from app state.

    Raises 503 if the connection was never established (e.g. the directory was
    unreachable at startup and lazy connection is disabled).
    """
    conn: LdapConnection | None = getattr(request.app.state, "conn", None)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP connection is not available.",
        )
    return conn


ConfigDep = Annotated[DomainConfig, Depends(get_config)]
BaseDep = Annotated[str, Depends(get_base)]
ConnDep = Annotated[LdapConnection, Depends(get_connection)]
