.PHONY: install css watch dev test lint fmt db-upgrade db-revision db-current

PORT ?= 5001

install:
	uv sync

# --- Local Postgres (Docker) -------------------------------------------------

db-up:
	docker compose up -d --wait

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d --wait

db-psql:
	docker compose exec db psql -U harbor -d harbor_dev

db-logs:
	docker compose logs -f db

# Compiled output is gitignored; run this after changing templates.
css:
	./bin/tailwindcss -i app/static/css/src.css -o app/static/css/app.css --minify

watch:
	./bin/tailwindcss -i app/static/css/src.css -o app/static/css/app.css --watch

dev: css
	uv run flask --app app run --debug --port $(PORT)

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

db-upgrade:
	uv run alembic upgrade head

db-revision:
	uv run alembic revision --autogenerate -m "$(m)"

db-current:
	uv run alembic current
