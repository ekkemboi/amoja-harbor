# Harbor

Multi-tenant issue tracking and project workspaces. Flask + Postgres, server-rendered
with Jinja and HTMX.

## Stack

| Concern | Choice |
| --- | --- |
| Runtime | Python 3.13, Flask 3 |
| Database | Postgres 18 on Neon (`aws-us-east-2`) |
| ORM / migrations | SQLAlchemy 2.1 + Alembic |
| UI | Jinja templates, Tailwind CSS 4, HTMX 2 |
| Tooling | uv, ruff, pytest |

## Quickstart

```bash
uv sync                 # create .venv from uv.lock
neon env pull --file .env   # or cp .env.example .env and fill in
make css                # compile Tailwind (gitignored output)
make dev                # http://localhost:5001
```

`make dev` runs the Flask dev server on port 5001 (macOS reserves 5000 for AirPlay).

## What works today

| Area | Status |
| --- | --- |
| Sign up / sign in / sign out | Argon2id passwords, server-side sessions, CSRF on every form |
| Workspaces | Create on signup or later at `/app/new`; `owner` membership |
| Roles | `owner > admin > member > viewer`, enforced server-side |
| Members | List, change role, remove — guarded by rank and last-owner rules |
| Tenancy | `/app/<org_slug>/…`; non-members get 404, not 403 |

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
  config.py            env loading, database URL normalization
  db.py                engine, Base, request-scoped session
  blueprints/          route modules (public, auth, orgs, issues, ...)
  models/              SQLAlchemy models
  templates/           Jinja templates; partials/ for HTMX fragments
  static/              css/src.css (source), js/htmx.min.js
migrations/            Alembic
tests/                 pytest
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
