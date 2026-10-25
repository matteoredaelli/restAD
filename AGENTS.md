# AGENTS.md — notes for coding agents working on restAD

This file is for AI coding agents. It covers things that aren't in the
README (install/usage/endpoint list) but matter when *changing code* here.

## What this repo is

A thin, read-only FastAPI wrapper around the `msad` library. One router per
`msad` domain object in `src/restad/routers/` (`users.py`, `groups.py`,
`computers.py`, `contacts.py`, `ous.py`, `audit.py`, `health.py`), wired up
in `app.py`. There is **no business logic here** — every endpoint should be
a near-1:1 call into an `msad` function, wrapped in the `EntryResponse` /
`EntriesResponse` / `BoolResponse` envelopes from `models.py`.

This is a sibling project to `graphqlAD` and `mcpAD`: all three wrap the same
`msad` functions through a different protocol (REST / GraphQL / MCP tools).
When `msad` gains a new function, it is expected to show up here too (a new
router function), and in the other two repos.

## Route ordering matters

FastAPI/Starlette matches routes in declaration order. Static sub-paths
(e.g. `/users/inactive`, `/groups/empty`, `/groups/security`) **must** be
declared before the catch-all `/{identifier}` route in the same router, or
they get swallowed by it. Follow the existing pattern in each router file.

## Read-only invariant

Every operation must be a GET. This is enforced by
`tests/test_app.py::test_openapi_is_read_only`, which inspects the generated
OpenAPI schema. If you add a write-capable msad function, it does not belong
here (restAD intentionally only exposes msad's read-only surface).

## Kerberos is an optional extra

`[project.optional-dependencies] kerberos = ["msad[kerberos]>=..."]` mirrors
msad's own extra. Don't add `gssapi` to the base `dependencies`.

## Versioning — do not hand-edit

Version comes from the Git tag via `hatch-vcs`, same setup as `msad` (see
`msad`'s AGENTS.md for the mechanics and the `fetch-depth: 0` CI gotcha).
`__version__` lives in `src/restad/__init__.py` and is referenced by
`app.py` (FastAPI `version=` and the `GET /` metadata) — never hardcode a
version string anywhere else.

## Keeping `msad` in sync

When bumping the `msad>=` pin in `pyproject.toml`, run:

```bash
uv lock --upgrade-package msad --refresh-package msad
```

Plain `--upgrade-package` without `--refresh-package` can silently resolve
against a stale cached version of msad's metadata right after a new release.

## Testing conventions

`tests/test_app.py` is a smoke-test suite — it does not hit a real
directory. It exercises config resolution, the OpenAPI surface (including
the read-only check above), and the lazy-connect startup path
(`RESTAD_LAZY_CONNECT=true`, which lets the app boot even when the
directory is unreachable, returning 503 from data endpoints until a
connection exists). There's no per-endpoint functional test against a fake
directory; a new router mainly needs to keep the OpenAPI/read-only checks
passing and get a line in the README's endpoint list.

Run `make lint` and `make test` before considering a change done.
