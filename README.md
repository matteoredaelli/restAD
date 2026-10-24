# restAD

A **read-only** REST interface over the [`msad`](https://github.com/matteoredaelli/msad)
Active Directory library, built with **FastAPI** + **Pydantic**, managed with
**uv** on **Python 3.14**.

Only LDAP *search* operations are exposed. No write operations (create / modify
/ delete / password reset / group membership changes) are reachable through the
API.

## How configuration is resolved

The effective connection config (an `msad.DomainConfig`) is built in two layers,
with the environment always winning:

1. **msad TOML file** (optional) — `~/.msad.toml` by default, or the path in
   `MSAD_CONFIG_FILE`. The `MSAD_DOMAIN` variable selects which
   `[domains.<name>]` section to use (otherwise the `[defaults] domain`).
2. **`MSAD_*` environment overrides** — applied on top of the TOML values.

This lets you keep non-secret settings in the TOML file (or omit it entirely)
and inject **credentials and any connection parameter at runtime** via the
environment, so secrets never need to live on disk.

### Environment variables

| Variable             | Overrides / effect                                             |
| -------------------- | -------------------------------------------------------------- |
| `MSAD_CONFIG_FILE`   | Path to the msad TOML file (default `~/.msad.toml`).           |
| `MSAD_DOMAIN`        | Which `[domains.<name>]` section to use.                       |
| `MSAD_HOST`          | Directory host (e.g. `dc.example.com`).                        |
| `MSAD_BASE`          | Search base DN (e.g. `dc=example,dc=com`).                     |
| `MSAD_PORT`          | Port (int, e.g. `636`).                                        |
| `MSAD_USE_SSL`       | LDAPS on/off (`true`/`false`/`1`/`0`/`yes`/`no`).              |
| `MSAD_USER`          | Bind user. Setting user **and** password enables simple bind. |
| `MSAD_PASSWORD`      | Bind password.                                                 |
| `MSAD_QUERY_TIMEOUT` | Per-operation receive timeout in seconds (int).               |

`host` and `base` are required (from either the TOML file or the environment).

Authentication:
- Omit `MSAD_USER`/`MSAD_PASSWORD` **and** leave them unset in the TOML →
  Kerberos/SASL bind (run `kinit` first).
- Set both `MSAD_USER` and `MSAD_PASSWORD` → simple user/password bind.

### Server variables

| Variable             | Effect                                                     |
| -------------------- | ---------------------------------------------------------- |
| `RESTAD_HOST`        | HTTP bind host for the `restad` command (default `127.0.0.1`). |
| `RESTAD_PORT`        | HTTP bind port (default `8000`).                           |
| `RESTAD_LAZY_CONNECT`| If true, start even if the directory is unreachable at boot. |

## Install

```bash
uv sync
```

The `msad` dependency is pulled from PyPI (`msad>=0.8`). Because `msad` depends
on `gssapi`, installing it builds a C extension against the system Kerberos
libraries, so you need the krb5 development headers available (e.g.
`libkrb5-dev` + `krb5-config` on Debian/Ubuntu, `krb5` via Homebrew on macOS).

Common developer tasks run through the `Makefile`:

```bash
make sync     # install/refresh the dev environment
make lint     # ruff check + format check
make test     # run the test suite
make build    # build wheel + sdist into dist/
make publish  # upload to PyPI (needs credentials)
```

## Run

Credentials are passed via the environment:

```bash
export MSAD_HOST=dc.example.com
export MSAD_BASE='dc=example,dc=com'
export MSAD_PORT=636
export MSAD_USE_SSL=true
export MSAD_USER='svc_reader'
export MSAD_PASSWORD='s3cr3t'

uv run restad
# or:
uv run uvicorn restad.app:app --host 0.0.0.0 --port 8000
```

Then open the interactive docs at <http://127.0.0.1:8000/docs>.

## Endpoints (all read-only)

- `GET /health` — connectivity probe (connect/bind test).
- **Users** — `GET /users` (by field), `/users/inactive`, `/users/{id}`,
  `/users/{id}/groups`, `/users/{id}/status`, `/users/{id}/disabled`,
  `/users/{id}/locked`.
- **Computers** — `GET /computers` (by field), `/computers/stale`,
  `/computers/domain-controllers`, `/computers/os-summary`, `/computers/{id}`.
- **Groups** — `GET /groups` (search), `/groups/empty`, `/groups/{id}`,
  `/groups/{id}/members`, `/groups/{id}/members/{user}` (membership check).
- **OUs** — `GET /ous` (find), `/ous/contents?ou_dn=...`, `/ous/{id}`.
- **Audit** — `GET /audit/domain`, `/audit/password-policy`,
  `/audit/password-policy/violations`, `/audit/privileged-groups`,
  `/audit/fsmo-roles`, `/audit/trusts`, `/audit/sites`, `/audit/gpos`,
  `/audit/gpos/{id}`, `/audit/fine-grained-password-policies`.

## Notes

- LDAP entries are dynamic (attributes depend on what the directory returns),
  so entries are serialized as open JSON objects inside typed envelopes
  (`count` + `entries`, or `entry`).
- A single LDAP connection is opened during the app lifespan and shared across
  requests; it is unbound at shutdown.
