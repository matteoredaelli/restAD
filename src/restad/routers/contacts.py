"""Read-only contact endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from msad import find_contacts

from ..deps import BaseDep, ConnDep
from ..models import EntriesResponse

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=EntriesResponse, summary="Find contacts")
def list_contacts(
    conn: ConnDep,
    base: BaseDep,
    q: Annotated[str | None, Query(description="cn/mail/displayName; * wildcards ok")] = None,
    limit: Annotated[int, Query(ge=0, description="Max entries (0 = no limit)")] = 0,
) -> EntriesResponse:
    """Find contact objects by cn, mail or displayName."""
    entries = find_contacts(conn, base, q, limit=limit)
    return EntriesResponse(count=len(entries), entries=entries)
