"""Health and connectivity endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from msad import check_connection, whoami

from ..deps import ConfigDep, ConnDep
from ..models import HealthResponse, WhoAmIResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness/connectivity check")
def health(config: ConfigDep) -> HealthResponse:
    """Test connectivity and bind to the directory without raising.

    Performs a fresh connect/bind probe (independent of the shared connection)
    and reports the outcome, so it is safe to call as a readiness probe. Any
    error (including low-level failures raised inside msad/ldap3) is captured
    and reported as ``ok: false`` rather than surfacing as a 500.
    """
    scheme = "ldaps" if config.use_ssl else "ldap"
    target = f"{scheme}://{config.host}:{config.port}"
    auth = "kerberos" if config.uses_kerberos else f"user {config.user!r}"
    try:
        status = check_connection(config)
    except Exception as exc:  # defensive: check_connection should not raise
        return HealthResponse(ok=False, target=target, auth=auth, error=str(exc))
    return HealthResponse(**status)


@router.get("/whoami", response_model=WhoAmIResponse, summary="Identity bound as")
def who_am_i(conn: ConnDep) -> WhoAmIResponse:
    """Report the identity the shared connection is bound as.

    Uses the RFC 4532 "Who Am I?" extended operation: the directory server
    reports the identity it actually authenticated (works with Kerberos/
    SASL-GSSAPI as well as simple user/password bind).
    """
    return WhoAmIResponse(authzid=whoami(conn))
