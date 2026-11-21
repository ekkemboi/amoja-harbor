# Amoja Harbor

Multi-tenant issue tracking and project workspaces. Flask + SQLite, server-rendered
with Jinja and HTMX.

## Stack

| Concern | Choice |
| --- | --- |
| Runtime | Python 3.13, Flask 3 |
| Database | SQLite, file-backed (`instance/amoja_harbor.db`) |
| ORM / migrations | SQLAlchemy 2.1 + Alembic |
| UI | Jinja templates, Tailwind CSS 4, HTMX 2 |
| Tooling | uv, ruff, pytest |

## Quickstart

```bash
uv sync                # create .venv from uv.lock
cp .env.example .env    # set SECRET_KEY; SQLite needs no server
make db-upgrade         # apply migrations
make dev                # http://localhost:5001
```

`make dev` runs the Flask dev server on port 5001 (macOS reserves 5000 for AirPlay).
The compiled `app/static/css/app.css` is committed, so no CSS build is needed to run
the app. After editing templates or `src.css`, install the Tailwind CLI once with
`bin/install-tailwind`, then run `make css`.

Tests need no running database. The suite creates a throwaway SQLite file under
pytest's temporary directory, applies migrations to it, and removes it afterwards:

```bash
make test
```

To reset local data, `make db-reset` deletes the database file and re-runs migrations.
`make db-shell` opens it with the `sqlite3` CLI.

## What works today

| Area | Status |
| --- | --- |
| Sign up / sign in / sign out | Argon2id passwords, server-side sessions, CSRF on every form |
| Workspaces | Create on signup or later at `/app/new`; `owner` membership |
| Roles | `owner > admin > member > viewer`, enforced server-side |
| Members | List, change role, remove — guarded by rank and last-owner rules |
| Tenancy | `/app/<org_slug>/…`; non-members get 404, not 403 |

## Next five features

See [`FEATURES.md`](FEATURES.md) for the turn-by-turn scope, schema changes, routes, and
definition of done.

## Routes

| Route | Method | Notes |
| --- | --- | --- |
| `/` | GET | Landing page |
| `/healthz` | GET | Liveness + database check |
| `/signup` | GET, POST | Creates user, workspace, owner membership |
| `/signin` | GET, POST | Honours `?next=` for same-site paths only |
| `/signout` | POST | Deletes the server-side session row |
| `/app` | GET | Redirects to the first workspace |
| `/app/new` | POST | Creates another workspace |
| `/app/<org_slug>/` | GET | Workspace home and member list |
| `/app/<org_slug>/members/<id>/role` | POST | Admin or owner |
| `/app/<org_slug>/members/<id>/remove` | POST | Admin or owner |

## Layout

```
app/
  __init__.py          app factory
  config.py            env loading, SQLite URL resolution
  db.py                engine, pragmas, Base, request-scoped session
  blueprints/          route modules (public, auth, orgs, ...)
  models/              SQLAlchemy models and the UTC datetime type
  templates/           Jinja templates; partials/ for HTMX fragments
  static/              css/src.css (source), css/app.css (compiled), js/
migrations/            Alembic
tests/                 pytest
instance/              local SQLite database (gitignored)
```
instance/              local SQLite database (gitignored)
```

## Conventions

- **Every query is org-scoped.** Models are never fetched by bare primary key in a
  request; always filter by the caller's organization.
- **Authorization lives in the data layer**, not in templates. A missing permission
  returns 403 before the model is loaded.
- **HTMX over SPA.** Endpoints return full pages on `GET` and fragments on
  `HX-Request`; fragments live in `templates/partials/`.
- **Migrations only, no `create_all`.** `make db-revision m="..."` then
  `make db-upgrade`.
- **Secrets stay in `.env`** (gitignored). `.env.example` documents keys only.

See `AGENTS.md` for the phase roadmap and working notes.
