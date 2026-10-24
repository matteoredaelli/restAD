"""Read-only computer endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import (
    find_computers,
    find_stale_computers,
    get_computer,
    list_domain_controllers,
    summarize_computer_os,
)

from ..deps import BaseDep, ConnDep
from ..models import EntriesResponse, EntryResponse, OsSummaryResponse

router = APIRouter(prefix="/computers", tags=["computers"])


@router.get("", response_model=EntriesResponse, summary="Find computers by field")
def list_computers(
    conn: ConnDep,
    base: BaseDep,
    name: Annotated[str | None, Query(description="cn (computer name); * wildcards ok")] = None,
    dns: Annotated[str | None, Query(description="dNSHostName (FQDN); * wildcards ok")] = None,
    os: Annotated[str | None, Query(description="operatingSystem; * wildcards ok")] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Find computers matching one or more fields (all ANDed together)."""
    entries = find_computers(conn, base, name=name, dns=dns, os=os, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/stale", response_model=EntriesResponse, summary="Find stale computers")
def stale_computers(
    conn: ConnDep,
    base: BaseDep,
    days: Annotated[int, Query(ge=0, description="Staleness threshold in days")] = 90,
    include_never: Annotated[
        bool, Query(description="Also include never-logged-on computers")
    ] = False,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Computers whose last logon is older than ``days`` days."""
    entries = find_stale_computers(conn, base, days=days, include_never=include_never, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/domain-controllers",
    response_model=EntriesResponse,
    summary="List domain controllers",
)
def domain_controllers(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the domain controllers (DC computer accounts)."""
    entries = list_domain_controllers(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/os-summary", response_model=OsSummaryResponse, summary="Computer OS summary")
def os_summary(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max computers to scan (0 = no limit)")] = 0,
) -> OsSummaryResponse:
    """Summarize computer accounts grouped by operatingSystem."""
    items = summarize_computer_os(conn, base, limit=limit)
    return OsSummaryResponse(count=len(items), items=items)


@router.get("/{identifier}", response_model=EntryResponse, summary="Get a single computer")
def read_computer(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single computer matched by sAMAccountName, cn or dNSHostName."""
    entry = get_computer(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer not found")
    return EntryResponse(entry=entry)
