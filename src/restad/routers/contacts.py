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
