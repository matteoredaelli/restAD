"""Pydantic response models (wrappers) for the REST API.

LDAP entries are intentionally dynamic: the attributes returned depend on the
requested attribute list, so each entry is represented as an open mapping
(``dict[str, Any]``) rather than a rigid model. The wrappers below add a small,
predictable envelope (counts, the domain queried) around those entries.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

#: A single LDAP entry: attribute name -> value(s). Values are whatever ldap3
#: decoded them to (str, int, datetime, list, ...).
LdapEntry = dict[str, Any]


class HealthResponse(BaseModel):
    """Result of the LDAP connectivity health check."""

    ok: bool = Field(description="Whether the bind to the directory succeeded.")
    target: str = Field(description="The server URL, e.g. ldaps://dc:636.")
    auth: str = Field(description="Authentication method used (kerberos or user '<name>').")
    error: str | None = Field(default=None, description="Error message when ok is false.")


class WhoAmIResponse(BaseModel):
    """Result of the RFC 4532 "Who Am I?" extended operation."""

    authzid: str | None = Field(
        default=None,
        description=(
            "The identity the connection is bound as, as reported by the "
            "directory server (e.g. 'u:svc_reader' or a DN form)."
        ),
    )


class EntryResponse(BaseModel):
    """A single LDAP entry (or null when not found)."""

    entry: LdapEntry | None = None


class EntriesResponse(BaseModel):
    """A list of LDAP entries plus a count."""

    count: int = Field(description="Number of entries returned.")
    entries: list[LdapEntry] = Field(default_factory=list)


class BoolResponse(BaseModel):
    """A tri-state boolean result (null means 'not found')."""

    result: bool | None = None


class OsSummaryItem(BaseModel):
    """One row of the computer-OS summary."""

    operatingSystem: str
    count: int


class OsSummaryResponse(BaseModel):
    """Computer accounts grouped and counted by operating system."""

    count: int = Field(description="Number of distinct operating systems.")
    items: list[OsSummaryItem] = Field(default_factory=list)
