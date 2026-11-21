# AGENTS.md — Amoja Harbor working notes

Amoja Harbor is a multi-tenant issue tracker. This file is the contract for anyone (human or
agent) picking up the next phase.

The next five features — scope, schema changes, routes, and definition of done — live in
[`FEATURES.md`](FEATURES.md). Work from that file; the table below is only the long-range
view.

## Commands

| Task | Command |
| --- | --- |
| Install deps | `uv sync` |
| Apply migrations | `make db-upgrade` |
| Reset the local database | `make db-reset` |
| Open a SQLite shell | `make db-shell` |
| Run dev server (port 5001) | `make dev` |
| Rebuild Tailwind after template edits | `make css` |
| Tests | `make test` |
| Lint / format | `make lint`, `make fmt` |
| New migration | `make db-revision m="add issues"` |

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
5. **Deterministic tests.** Tests run against a throwaway SQLite file created under
   pytest's temporary directory and migrated with Alembic; no mocks, no shared state.

## UI shell

- `templates/base.html` is the authenticated workspace shell: fixed 268px sidebar on
  desktop, off-canvas drawer with overlay on mobile, workspace card, icon navigation,
  and a user footer.
- `templates/public_base.html` wraps the landing page; `templates/auth_base.html` wraps
  sign-in, sign-up, and the no-workspace screen.
- Sidebar links use HTMX (`hx-target="#page-content"`, `hx-select="#page-content"`) so
  future pages swap only the content area.
- Shared Jinja helpers live in `templates/_macros.html`; styles live in
  `app/static/css/src.css` and are compiled with `make css`.

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
- Tests create real rows (no mocks) and `tests/factories.py` deletes them in teardown.
  The suite is fast because SQLite is a local file and migrations run once per session.

## Schema (phase 1)

One initial migration: `20261026_e40a67f2c0e7_initial_schema`, plus sessions and index
cleanup. SQLite is the only supported database.

| Table | Notes |
| --- | --- |
| `organizations` | `slug` is the URL handle: `/app/<slug>/...` |
| `users` | global identity; email stored lowercase, enforced by CHECK |
| `memberships` | `(org_id, user_id)` unique; role `owner > admin > member > viewer` |
| `projects` | `(org_id, key)` unique; `issue_counter` allocates `KEY-<n>` atomically |
| `issues` | `org_id` denormalized; `(project_id, number)` unique |
| `comments` | `org_id` denormalized; ordered by `created_at` |
| `labels`, `issue_labels` | `(org_id, name)` unique; many-to-many with issues |
| `activity` | append-only, JSON payload, no `updated_at` |

Decisions that later phases depend on:

- Enums are VARCHAR + CHECK (`native_enum=False`), so adding a status is a constraint
  swap instead of `ALTER TYPE`. Python-side `StrEnum` is the source of truth.
- `org_id` is denormalized onto issues, comments, and labels so authorization is a
  single-column filter and never needs a join through `projects`.
- UUID PKs default to `uuid.uuid4` in Python. Raw SQL inserts must supply an id.
- `UTCDateTime` (`app/models/types.py`) normalizes values to UTC on write and re-attaches
  UTC on read, because SQLite does not store timezone offsets.
- `updated_at` is set by the ORM (`onupdate=now()`); scripts that write raw SQL must
  set it themselves.
- Foreign keys are enforced: `app/db.py` runs `PRAGMA foreign_keys=ON` on every SQLite
  connection, so `ON DELETE CASCADE` works without ORM cascades.

## Conventions

- Python 3.13, modern typing (`X | None`), `from __future__ import annotations`.
- Ruff for lint and format; line length 100.
- Blueprints are per-domain: `public`, `auth`, `orgs`, `issues`, `comments`, `admin`, `api`.
- Models live in `app/models/<domain>.py`, exported from `app/models/__init__.py`.
- Use `db.get_session()` inside requests, `db.session_scope()` in scripts and jobs.
- UUID primary keys (`uuid.uuid4`), `UTCDateTime` for all times, `created_at`/`updated_at`
  on every mutable table.
- Indexes are composite-first. SQLite uses an index on `(a, b)` for filters on `a` alone,
  so never put `index=True` on a column that is already the leading column of a
  composite index or unique constraint. This bit us once: seven redundant indexes came
  from doing exactly that.
- Soft-delete only where the roadmap calls for it (`deleted_at`), never by deleting rows
  that audit records reference.

## Environment

- **Development and production:** SQLite, at `instance/amoja_harbor.db` by default. Set
  `DATABASE_URL=sqlite:///path/to/file.db` to move it; relative paths resolve from the
  repository root.
- `app/db.py` enables foreign keys, WAL journaling, and a busy timeout on every
  connection. `instance/` and `*.db*` are gitignored.
- Tests read `TEST_DATABASE_URL` when set, otherwise they create a temporary database
  file per session and apply migrations to it, so a test run never touches local data.
- Alembic honours `ALEMBIC_DATABASE_URL` (or a programmatic `sqlalchemy.url`) before
  falling back to the app configuration.
- The old Neon/Postgres configuration is archived in `.env.neon.backup` and is not loaded.
