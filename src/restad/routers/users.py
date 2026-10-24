"""Read-only user endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import (
    find_inactive_users,
    find_users,
    get_user,
    user_groups,
)
from msad.user import (
    has_expired_password,
    has_never_expires_password,
    is_disabled,
    is_locked,
)

from ..deps import BaseDep, ConnDep
from ..models import BoolResponse, EntriesResponse, EntryResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=EntriesResponse, summary="Find users by field")
def list_users(
    conn: ConnDep,
    base: BaseDep,
    name: Annotated[str | None, Query(description="givenName (first name); * wildcards ok")] = None,
    surname: Annotated[str | None, Query(description="sn (last name); * wildcards ok")] = None,
    mail: Annotated[str | None, Query(description="mail; * wildcards ok")] = None,
    sam: Annotated[str | None, Query(description="sAMAccountName; * wildcards ok")] = None,
    department: Annotated[str | None, Query(description="department; * wildcards ok")] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Find users matching one or more fields (all ANDed together)."""
    entries = find_users(
        conn,
        base,
        name=name,
        surname=surname,
        mail=mail,
        sam=sam,
        department=department,
        limit=limit,
    )
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/inactive", response_model=EntriesResponse, summary="Find inactive users")
def inactive_users(
    conn: ConnDep,
    base: BaseDep,
    days: Annotated[int, Query(ge=0, description="Inactivity threshold in days")] = 90,
    include_never: Annotated[bool, Query(description="Also include never-logged-on users")] = False,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Enabled users whose last logon is older than ``days`` days."""
    entries = find_inactive_users(conn, base, days=days, include_never=include_never, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/{identifier}", response_model=EntryResponse, summary="Get a single user")
def read_user(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single user matched by sAMAccountName, UPN, mail or cn."""
    entry = get_user(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return EntryResponse(entry=entry)


@router.get("/{identifier}/groups", response_model=EntriesResponse, summary="User's groups")
def read_user_groups(
    conn: ConnDep,
    base: BaseDep,
    identifier: str,
    nested: Annotated[bool, Query(description="Expand nested group membership")] = True,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the groups a user belongs to (nested by default)."""
    entries = user_groups(conn, base, limit, identifier, nested=nested)
    if entries is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/{identifier}/status", summary="User status checks")
def read_user_status(conn: ConnDep, base: BaseDep, identifier: str) -> dict[str, bool | None]:
    """Return a bundle of boolean status checks for a user.

    Each value is ``null`` when the check could not determine the state (e.g.
    the user was not found for that specific check).
    """
    return {
        "is_disabled": is_disabled(conn, base, identifier),
        "is_locked": is_locked(conn, base, identifier),
        "has_never_expires_password": has_never_expires_password(conn, base, identifier),
        "has_expired_password": has_expired_password(conn, base, identifier),
    }


@router.get("/{identifier}/disabled", response_model=BoolResponse, summary="Is user disabled")
def read_user_disabled(conn: ConnDep, base: BaseDep, identifier: str) -> BoolResponse:
    """True if the account is disabled, null if not found."""
    return BoolResponse(result=is_disabled(conn, base, identifier))


@router.get("/{identifier}/locked", response_model=BoolResponse, summary="Is user locked")
def read_user_locked(conn: ConnDep, base: BaseDep, identifier: str) -> BoolResponse:
    """True if the account is locked, null if not found."""
    return BoolResponse(result=is_locked(conn, base, identifier))
