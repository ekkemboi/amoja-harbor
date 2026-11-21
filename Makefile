.PHONY: install css watch dev test lint fmt db-upgrade db-revision db-current db-reset db-shell

PORT ?= 5001
DB_PATH ?= instance/amoja_harbor.db

install:
	uv sync

# --- SQLite ------------------------------------------------------------------

# Apply pending migrations to the local database file.
db-upgrade:
	uv run alembic upgrade head

# Drop the local database and rebuild it from migrations.
db-reset:
	rm -f $(DB_PATH) $(DB_PATH)-wal $(DB_PATH)-shm
	uv run alembic upgrade head

db-shell:
	sqlite3 $(DB_PATH)

# Compiled output is gitignored; run this after changing templates.
css:
	./bin/tailwindcss -i app/static/css/src.css -o app/static/css/app.css --minify

watch:
	./bin/tailwindcss -i app/static/css/src.css -o app/static/css/app.css --watch

dev:
	uv run flask --app app run --debug --port $(PORT)

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

db-revision:
	uv run alembic revision --autogenerate -m "$(m)"

db-current:
	uv run alembic current
