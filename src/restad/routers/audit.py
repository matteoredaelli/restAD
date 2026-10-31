"""Read-only audit endpoints: domain info, policy, privileged groups, topology."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from msad import (
    decode_entries,
    find_recently_created,
    find_recently_modified,
    get_domain_info,
    get_gpo,
    get_password_policy,
    get_password_policy_violations,
    get_privileged_groups,
    get_site,
    get_subnet,
    list_authorized_dhcp_servers,
    list_dfs_namespaces,
    list_dns_records,
    list_dns_zones,
    list_fine_grained_password_policies,
    list_fsmo_roles,
    list_gpos,
    list_servers,
    list_site_links,
    list_sites,
    list_subnets,
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


@router.get("/subnets", response_model=EntriesResponse, summary="AD subnets")
def subnets(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the AD subnets (CIDR -> site) from the Configuration NC."""
    entries = list_subnets(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/sites/{identifier}", response_model=EntryResponse, summary="Get a single site")
def site(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single AD site matched by its cn (name)."""
    entry = get_site(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return EntryResponse(entry=entry)


@router.get(
    "/subnets/{identifier:path}", response_model=EntryResponse, summary="Get a single subnet"
)
def subnet(conn: ConnDep, base: BaseDep, identifier: str) -> EntryResponse:
    """Return a single AD subnet matched by its cn (CIDR, e.g. 10.20.0.0/16).

    The identifier is a `:path` parameter so the ``/`` in the CIDR prefix is
    accepted as part of the value.
    """
    entry = get_subnet(conn, base, identifier)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subnet not found")
    return EntryResponse(entry=entry)


@router.get("/site-links", response_model=EntriesResponse, summary="AD site links")
def site_links(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List AD site links (inter-site replication topology)."""
    entries = list_site_links(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/servers", response_model=EntriesResponse, summary="Directory servers (DCs)")
def servers(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List directory servers (DCs) from the Configuration NC, site-centric."""
    entries = list_servers(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get("/dns-zones", response_model=EntriesResponse, summary="AD-integrated DNS zones")
def dns_zones(
    conn: ConnDep,
    base: BaseDep,
    zone_base: Annotated[
        str | None, Query(description="Override the zone partition DN (e.g. ForestDnsZones)")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List AD-integrated DNS zones."""
    entries = list_dns_zones(conn, base, zone_base=zone_base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/dns-zones/{zone}/records",
    response_model=EntriesResponse,
    summary="DNS records of a zone (decoded)",
)
def dns_records(
    conn: ConnDep,
    base: BaseDep,
    zone: str,
    zone_base: Annotated[
        str | None, Query(description="Override the zone partition DN (e.g. ForestDnsZones)")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List the DNS records of an AD-integrated zone (dnsRecord decoded)."""
    entries = list_dns_records(conn, base, zone, zone_base=zone_base, limit=limit)
    return EntriesResponse(count=len(entries), entries=decode_entries(entries))


@router.get(
    "/dhcp-servers",
    response_model=EntriesResponse,
    summary="Authorized DHCP servers",
)
def authorized_dhcp_servers(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List DHCP servers authorized in AD (authorization only, no scopes)."""
    entries = list_authorized_dhcp_servers(conn, base, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/dfs-namespaces",
    response_model=EntriesResponse,
    summary="Domain-based DFS namespaces",
)
def dfs_namespaces(
    conn: ConnDep,
    base: BaseDep,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """List domain-based DFS namespace roots."""
    entries = list_dfs_namespaces(conn, base, limit=limit)
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


@router.get(
    "/recently-modified",
    response_model=EntriesResponse,
    summary="Objects recently modified",
)
def recently_modified(
    conn: ConnDep,
    base: BaseDep,
    days: Annotated[int, Query(ge=0, description="Modified within the last N days")] = 7,
    object_class: Annotated[
        str | None, Query(description="Restrict to one objectClass (user/group/computer/...)")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Objects whose whenChanged is within the last ``days`` days."""
    entries = find_recently_modified(conn, base, days=days, object_class=object_class, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)


@router.get(
    "/recently-created",
    response_model=EntriesResponse,
    summary="Objects recently created",
)
def recently_created(
    conn: ConnDep,
    base: BaseDep,
    days: Annotated[int, Query(ge=0, description="Created within the last N days")] = 7,
    object_class: Annotated[
        str | None, Query(description="Restrict to one objectClass (user/group/computer/...)")
    ] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Objects whose whenCreated is within the last ``days`` days."""
    entries = find_recently_created(conn, base, days=days, object_class=object_class, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)
