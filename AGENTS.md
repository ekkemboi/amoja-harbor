# AGENTS.md — Harbor working notes

Harbor is a multi-tenant issue tracker. This file is the contract for anyone (human or
agent) picking up the next phase.

The next five features — scope, schema changes, routes, and definition of done — live in
[`FEATURES.md`](FEATURES.md). Work from that file; the table below is only the long-range
view.

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
| 1 | Schema + migrations (orgs, users, memberships, projects, issues, comments, labels, activity) | done |
| 2 | Auth, org scoping, RBAC enforcement + tests | done |
| 3 | Projects & issues CRUD, board + list views | next |
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

## Auth and tenancy (phase 2)

- **Sessions are rows in `sessions`**, not signed cookies. The cookie holds only an opaque
  token, so `POST /signout` deletes server state and a stolen cookie can be revoked.
  Anonymous sessions (CSRF tokens, flash messages) exist too and expire after 14 days;
  `flask prune-sessions` clears them — wire it to cron when we deploy (phase 10).
- **Passwords are Argon2id** (`app/security.py`). `accounts.authenticate` still runs a
  verify against a dummy hash when the email is unknown, so timing does not reveal
  whether an account exists.
- **CSRF is global** via Flask-WTF. Every POST form needs
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Org routes live under `/app/<org_slug>/`.** `orgs._pull_org` resolves the org in a
  `url_value_preprocessor`; `orgs._require_membership` then rejects non-members with
  **404, never 403** — a 403 would confirm that someone else's workspace exists.
- **Role checks use `@requires_role(Role.X)`** against `g.membership`. Rank:
  `owner 4 > admin 3 > member 2 > viewer 1`.
- Role edits refuse all three of: changing your own role, touching a member ranked above
  you, and granting a role above your own rank.
- Signed-out `/app` hits redirect to `/signin?next=…`; `_safe_next` only follows
  same-site relative paths.
- Tests create real rows (no SQLite, no mocks) and `tests/factories.py` deletes them in
  teardown. The suite takes ~90s because each write is a round trip to Neon; if that
  becomes painful, run the suite against a dedicated Neon branch (`neon checkout test`).

## Schema (phase 1)

One migration: `20261026_e40a67f2c0e7_initial_schema`. Applied to the `main` branch.

| Table | Notes |
| --- | --- |
| `organizations` | `slug` is the URL handle: `/app/<slug>/...` |
| `users` | global identity; email stored lowercase, enforced by CHECK |
| `memberships` | `(org_id, user_id)` unique; role `owner > admin > member > viewer` |
| `projects` | `(org_id, key)` unique; `issue_counter` allocates `KEY-<n>` atomically |
| `issues` | `org_id` denormalized; `(project_id, number)` unique |
| `comments` | `org_id` denormalized; ordered by `created_at` |
| `labels`, `issue_labels` | `(org_id, name)` unique; many-to-many with issues |
| `activity` | append-only, JSONB payload, no `updated_at` |

Decisions that later phases depend on:

- Enums are VARCHAR + CHECK (`native_enum=False`), so adding a status is a constraint
  swap instead of `ALTER TYPE`. Python-side `StrEnum` is the source of truth.
- `org_id` is denormalized onto issues, comments, and labels so authorization is a
  single-column filter and never needs a join through `projects`.
- UUID PKs use `gen_random_uuid()` server defaults, so raw SQL inserts work too.
- `updated_at` is set by the ORM (`onupdate=now()`); scripts that write raw SQL must
  set it themselves.

## Conventions

- Python 3.13, modern typing (`X | None`), `from __future__ import annotations`.
- Ruff for lint and format; line length 100.
- Blueprints are per-domain: `public`, `auth`, `orgs`, `issues`, `comments`, `admin`, `api`.
- Models live in `app/models/<domain>.py`, exported from `app/models/__init__.py`.
- Use `db.get_session()` inside requests, `db.session_scope()` in scripts and jobs.
- UUID primary keys (`uuid.uuid4`), `timestamptz` for all times, `created_at`/`updated_at`
  on every mutable table.
- Indexes are composite-first. Postgres uses an index on `(a, b)` for filters on `a`
  alone, so never put `index=True` on a column that is already the leading column of a
  composite index or unique constraint. This bit us once: seven redundant indexes came
  from doing exactly that.
- Soft-delete only where the roadmap calls for it (`deleted_at`), never by deleting rows
  that audit records reference.

## Environment

- Neon project `harbor`, region `aws-us-east-2` (required for Functions/Storage/Realtime
  when those phases arrive).
- App connects with `DATABASE_URL_UNPOOLED` (direct endpoint) because gunicorn keeps its
  own pool. Pooled `DATABASE_URL` is reserved for serverless callers.
