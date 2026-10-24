"""Console entry point: run the restAD API with uvicorn.

Usage:
    restad                 # listen on 127.0.0.1:8000
    RESTAD_HOST=0.0.0.0 RESTAD_PORT=9000 restad

Host/port are read from RESTAD_HOST / RESTAD_PORT (not the MSAD_* vars, which
configure the directory connection).
"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("RESTAD_HOST", "127.0.0.1")
    port = int(os.environ.get("RESTAD_PORT", "8000"))
    uvicorn.run("restad.app:app", host=host, port=port, factory=False)


if __name__ == "__main__":
    main()
