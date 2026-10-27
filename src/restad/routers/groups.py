"""Read-only group endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import (
    find_distribution_groups,
    find_groups,
    find_security_groups,
    get_group,
    is_member,
    list_empty_groups,
)
from msad.exceptions import MsadNotFoundError
from msad.group import group_members

from ..deps import BaseDep, ConnDep
from ..models import BoolResponse, EntriesResponse, EntryResponse

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=EntriesResponse, summary="Search groups")
def list_groups(
    conn: ConnDep,
    base: BaseDep,
    q: Annotated[
        str, Query(description="cn/name/sAMAccountName/displayName; * wildcards ok")
    ] = "*",
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Search groups by cn, name, sAMAccountName or displayName."""
    entries = find_groups(conn, base, q, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/empty", response_model=EntriesResponse, summary="List empty groups")
def empty_groups(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List groups that have no direct members."""
    entries = list_empty_groups(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/security", response_model=EntriesResponse, summary="List security groups")
def security_groups(
    conn: ConnDep,
    base: BaseDep,
    scope: Annotated[
        str | None, Query(description="Restrict to global/domain_local/universal")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List security-enabled groups (as opposed to distribution groups)."""
    try:
        entries = find_security_groups(conn, base, scope=scope, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/distribution", response_model=EntriesResponse, summary="List distribution groups")
def distribution_groups(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List distribution groups (complement of security-enabled groups)."""
    entries = find_distribution_groups(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/{identifier}", response_model=EntryResponse, summary="Get a single group")
def read_group(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single group matched by sAMAccountName or cn."""
    entry = get_group(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return EntryResponse(entry=entry)


@router.get("/{identifier}/members", response_model=EntriesResponse, summary="Group members")
def read_group_members(
    conn: ConnDep,
    base: BaseDep,
    identifier: str,
    nested: Annotated[bool, Query(description="Expand nested membership")] = False,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Return the members of a group as person objects."""
    try:
        entries = group_members(conn, base, identifier, nested=nested, limit=limit)
    except MsadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/{identifier}/members/{user}", response_model=BoolResponse, summary="Membership check")
def read_is_member(conn: ConnDep, base: BaseDep, identifier: str, user: str) -> BoolResponse:
    """Check whether ``user`` is a (possibly nested) member of the group."""
    try:
        result = is_member(conn, base, group=identifier, user=user)
    except MsadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BoolResponse(result=result)
