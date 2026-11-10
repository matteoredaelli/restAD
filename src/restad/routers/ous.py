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

"""Read-only organizational-unit (OU) endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import find_empty_ous, find_ous, get_ou, get_ou_contents

from ..deps import BaseDep, ConnDep
from ..models import EntriesResponse, EntryResponse

router = APIRouter(prefix="/ous", tags=["ous"])


@router.get("", response_model=EntriesResponse, summary="Find OUs")
def list_ous(
    conn: ConnDep,
    base: BaseDep,
    name: Annotated[str | None, Query(description="ou name; * wildcards ok")] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Find organizational units."""
    entries = find_ous(conn, base, name=name, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/contents", response_model=EntriesResponse, summary="List OU contents")
def ou_contents(
    conn: ConnDep,
    ou_dn: Annotated[str, Query(description="Distinguished name of the OU to list")],
    object_class: Annotated[
        str | None, Query(description="Restrict to one objectClass (user/group/computer/...)")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the objects contained directly under an OU (by its DN)."""
    entries = get_ou_contents(conn, ou_dn, object_class=object_class, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/empty", response_model=EntriesResponse, summary="List empty OUs")
def empty_ous(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List organizational units with no nested sub-OU."""
    entries = find_empty_ous(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/{identifier}", response_model=EntryResponse, summary="Get a single OU")
def read_ou(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single OU matched by its ou name or full DN."""
    entry = get_ou(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OU not found")
    return EntryResponse(entry=entry)
