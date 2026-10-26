# AGENTS.md — Harbor working notes

Harbor is a multi-tenant issue tracker. This file is the contract for anyone (human or
agent) picking up the next phase.

## Commands

| Task | Command |
| --- | --- |
| Install deps | `uv sync` |
| Run dev server (port 5001) | `make dev` |
| Rebuild Tailwind after template edits | `make css` |
| Tests | `make test` |
| Lint / format | `make lint`, `make fmt` |
| New migration | `make db-revision m="add issues"` |
| Apply migrations | `make db-upgrade` |
| Pull DB creds | `neon env pull --file .env` |
| New Neon branch for a feature | `neon checkout <name> --create` |

## Phase roadmap

| # | Phase | Status |
| --- | --- | --- |
| 0 | Scaffold, database, health check | done |
| 1 | Schema + migrations (orgs, users, memberships, projects, issues, comments, labels, activity) | next |
| 2 | Auth, org scoping, RBAC enforcement + tests | queued |
| 3 | Projects & issues CRUD, board + list views | queued |
| 4 | Realtime comments, presence, notifications | queued |
| 5 | Attachments to object storage, quotas | queued |
| 6 | Search (FTS → hybrid) | queued |
| 7 | Audit log, admin dashboard, analytics | queued |
| 8 | API keys, webhooks, rate limits | queued |
| 9 | Billing and plan gates | queued |
| 10 | Import/export, seed data, E2E, deploy | queued |

## Non-negotiables

1. **Org scoping everywhere.** Helper: resolve the current org from the URL
   (`/app/<org_slug>/...`) and verify membership on every request.
2. **No authorization in templates.** Templates may hide controls, but the server must
   reject unauthorized actions independently.
3. **Migrations only.** Never call `Base.metadata.create_all()` outside tests.
4. **Fragments are separate templates.** HTMX responses use `templates/partials/`.
5. **Deterministic tests.** Tests run against a real Postgres (the Neon branch in `.env`)
   using a `harbor_test` schema or transaction rollback; no SQLite.

## Conventions

- Python 3.13, modern typing (`X | None`), `from __future__ import annotations`.
- Ruff for lint and format; line length 100.
- Blueprints are per-domain: `public`, `auth`, `orgs`, `issues`, `comments`, `admin`, `api`.
- Models live in `app/models/<domain>.py`, exported from `app/models/__init__.py`.
- Use `db.get_session()` inside requests, `db.session_scope()` in scripts and jobs.
- UUID primary keys (`uuid.uuid4`), `timestamptz` for all times, `created_at`/`updated_at`
  on every mutable table.
- Soft-delete only where the roadmap calls for it (`deleted_at`), never by deleting rows
  that audit records reference.

## Environment

- Neon project `harbor`, region `aws-us-east-2` (required for Functions/Storage/Realtime
  when those phases arrive).
- App connects with `DATABASE_URL_UNPOOLED` (direct endpoint) because gunicorn keeps its
  own pool. Pooled `DATABASE_URL` is reserved for serverless callers.
