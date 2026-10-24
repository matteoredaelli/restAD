"""Read-only audit endpoints: domain info, policy, privileged groups, topology."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import (
    get_domain_info,
    get_gpo,
    get_password_policy,
    get_password_policy_violations,
    get_privileged_groups,
    list_fine_grained_password_policies,
    list_fsmo_roles,
    list_gpos,
    list_sites,
    list_trusts,
)

from ..deps import BaseDep, ConnDep
from ..models import EntriesResponse, EntryResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/domain", response_model=EntryResponse, summary="Domain object info")
def domain_info(conn: ConnDep, base: BaseDep) -> EntryResponse:
    """Read the domain object (security-relevant settings and metadata)."""
    return EntryResponse(entry=get_domain_info(conn, base))


@router.get("/password-policy", response_model=EntryResponse, summary="Default password policy")
def password_policy(conn: ConnDep, base: BaseDep) -> EntryResponse:
    """Read the default domain password policy."""
    return EntryResponse(entry=get_password_policy(conn, base))


@router.get(
    "/password-policy/violations",
    response_model=EntriesResponse,
    summary="Password policy violations",
)
def password_policy_violations(
    conn: ConnDep,
    base: BaseDep,
    include_never_set: Annotated[
        bool, Query(description="Also flag users with pwdLastSet=0")
    ] = True,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Enabled users whose password violates the domain policy."""
    entries = get_password_policy_violations(
        conn, base, include_never_set=include_never_set, limit=limit
    )
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/privileged-groups", response_model=EntriesResponse, summary="Privileged groups")
def privileged_groups(
    conn: ConnDep,
    base: BaseDep,
    with_members: Annotated[bool, Query(description="Include each group's members")] = False,
    nested: Annotated[bool, Query(description="Expand nested membership")] = False,
) -> EntriesResponse:
    """Report on well-known privileged groups with member counts."""
    entries = get_privileged_groups(conn, base, with_members=with_members, nested=nested)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/fsmo-roles", response_model=EntriesResponse, summary="FSMO role owners")
def fsmo_roles(conn: ConnDep, base: BaseDep) -> EntriesResponse:
    """Report the owner of each of the five FSMO roles."""
    entries = list_fsmo_roles(conn, base)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/trusts", response_model=EntriesResponse, summary="Domain trusts")
def trusts(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the domain's trust relationships."""
    entries = list_trusts(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/sites", response_model=EntriesResponse, summary="AD sites")
def sites(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the AD sites from the Configuration NC."""
    entries = list_sites(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/gpos", response_model=EntriesResponse, summary="Group Policy Objects")
def gpos(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List Group Policy Objects."""
    entries = list_gpos(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/gpos/{identifier}", response_model=EntryResponse, summary="Get a single GPO")
def gpo(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single GPO matched by its cn (GUID) or displayName."""
    entry = get_gpo(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GPO not found")
    return EntryResponse(entry=entry)


@router.get(
    "/fine-grained-password-policies",
    response_model=EntriesResponse,
    summary="Fine-grained password policies (PSOs)",
)
def fine_grained_password_policies(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List fine-grained password policies (PSOs)."""
    entries = list_fine_grained_password_policies(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)
