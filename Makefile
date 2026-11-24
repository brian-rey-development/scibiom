SHELL := bash
.DEFAULT_GOAL := help

BANNED_NAMES := utils helpers common misc shared types
BANNED_FIND := $(foreach name,$(BANNED_NAMES),-o -type d -name $(name) -o -name $(name).py)
PYTHON_PACKAGES := apps/api packages/core packages/infrastructure
API_SCHEMA := apps/web/src/core/api/schema.d.ts

.PHONY: help setup db-up db-down db-reset migrate migration dev dev-api dev-web \
	lint format typecheck arch test test-unit test-integration test-web openapi \
	openapi-check build-web check

help: ## List available targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install Python and web dependencies, create .env if missing
	uv sync --all-packages --locked
	pnpm install --frozen-lockfile
	[ -f .env ] || cp .env.example .env

db-up: ## Start local Postgres and wait until healthy
	docker compose up -d --wait

db-down: ## Stop local Postgres, keep its data
	docker compose down

db-reset: ## Destroy local Postgres data and start fresh
	docker compose down --volumes && $(MAKE) db-up

migrate: ## Apply migrations as the owner role
	uv run alembic upgrade head

migration: ## Autogenerate a migration, pass name=add_foo
	@[ -n "$(name)" ] || { echo "Pass a migration name, for example make migration name=add_foo" >&2; exit 1; }
	uv run alembic revision --autogenerate -m "$$name"

dev: ## Run API and web with reload
	$(MAKE) -j2 dev-api dev-web

dev-api: ## Run the API with reload on :8000
	uv run uvicorn scibiom_api.main:create_app --factory --reload \
		--reload-dir apps/api/src --reload-dir packages \
		--no-access-log --host 127.0.0.1 --port 8000

dev-web: ## Run the web app with reload on :3000
	pnpm --filter web dev

lint: ## Check Python and web code without changing it
	uv run ruff check .
	uv run ruff format --check .
	@for package in $(PYTHON_PACKAGES); do (cd $$package && uv run --no-sync deptry src) || exit 1; done
	pnpm --filter web lint

format: ## Format and autofix Python and web code
	uv run ruff format .
	uv run ruff check --fix .
	pnpm --filter web format

typecheck: ## Type check Python and web code
	uv run pyright
	pnpm --filter web typecheck

arch: ## Enforce import contracts and banned module names
	uv run lint-imports
	@banned=$$(find apps/api/src apps/api/tests packages \( -name .venv -o -name node_modules -o -name __pycache__ \) -prune \
		-o \( -false $(BANNED_FIND) \) -print) || exit 1; \
	if [ -n "$$banned" ]; then \
		echo "Banned module or package names ($(BANNED_NAMES)):" >&2; \
		echo "$$banned" >&2; \
		exit 1; \
	fi

test: test-unit test-integration ## Run Python unit tests, then integration tests

test-unit: ## Run Python tests that need no services
	uv run pytest -m "not integration"

test-integration: ## Run Python tests against local Postgres
	uv run pytest -m integration

test-web: ## Run web tests
	pnpm --filter web test

openapi: ## Export the OpenAPI schema and regenerate web API types
	uv run scibiom-openapi apps/api/openapi.json
	pnpm --filter web generate:api

openapi-check: ## Fail if the committed API contract differs from the regenerated one
	@set -e; snapshot=$$(mktemp -d); trap 'rm -rf "$$snapshot"' EXIT; \
	cp apps/api/openapi.json "$$snapshot/openapi.json"; \
	cp $(API_SCHEMA) "$$snapshot/schema.d.ts"; \
	$(MAKE) openapi; \
	drift=0; \
	diff -u "$$snapshot/openapi.json" apps/api/openapi.json || drift=1; \
	diff -u "$$snapshot/schema.d.ts" $(API_SCHEMA) || drift=1; \
	[ $$drift -eq 0 ] || { echo "API contract drifted, commit the regenerated files" >&2; exit 1; }

build-web: ## Build the web app for production
	pnpm --filter web build

check: lint arch openapi-check typecheck test test-web build-web ## Run everything CI runs, needs make db-up migrate first
