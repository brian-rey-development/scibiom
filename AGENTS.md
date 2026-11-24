# Scibiom engineering contract

Scibiom is a personal health research and protocols assistant that will hold sensitive health data. These rules bind every human and AI contributor, and CI enforces most of them. Web-specific rules live in `apps/web/AGENTS.md`.

## Architecture

The backend is a modular monolith built on ports and adapters. Business logic lives in one framework-free package, every entry point (REST today, MCP, agent tools and workflows later) is a thin adapter over the same use cases, and every external system sits behind a port the core defines. `docs/technical/ARCHITECTURE.md` maps the layout, and `docs/technical/adr/0001-modular-monolith.md` records why.

## Package layout

```text
packages/core/src/scibiom_core/
  kernel/                    primitives more than one context needs
  <context>/
    domain/
    use_cases/               one module per use case
    ports/                   one module per port
packages/infrastructure/src/scibiom_infrastructure/
  database/
    tables/<context>/        one module per table
    repositories/<context>/  one module per repository
    migrations/
  auth/                      one module per provider, such as supabase.py
  observability/
```

A folder exists only when it groups several modules. Something that fits in one module stays a module, and no folder is created ahead of its code.

New apps and packages (`worker`, `mcp`, `ai`, `integrations`) are created by the first capability that needs them.

## Python dependency rules

1. Apps import packages, packages never import apps.
2. `core` imports only the standard library. `infrastructure` may import `core` but never FastAPI, Starlette or Uvicorn.
3. Bounded contexts never import each other, in core or in infrastructure's `tables/` and `repositories/`. A context that needs another's data declares a port, and the composition root wires it.
4. Inside a context, `domain` imports only `kernel`, and `use_cases` imports `domain` and `ports`.
5. No Python module or package is named `utils`, `helpers`, `common`, `misc`, `shared` or `types`.

Import Linter and `make arch` enforce rules 1, 2 and 5. Rules 3 and 4 get contracts with the first context.

## Where types live

| Kind | Location |
|---|---|
| Domain types | `core/<context>/domain`, private to the context |
| Use case inputs and outputs | `core/<context>/use_cases` |
| Wire schemas (Pydantic) | the app that serves them |
| Persistence rows | `infrastructure/database/tables/<context>/` |
| Frontend API types | generated from `apps/api/openapi.json`, never hand-written |

Each context owns one Postgres schema, foreign keys never cross schemas, IDs are UUIDv7 from `uuid.uuid7()`, and tenant-owned rows carry `workspace_id`.

## Code conventions

- Python 3.14 with Pyright strict and Ruff (nearly all rules). TypeScript strict with no `any`.
- Functions of 20 lines or fewer, early returns, immutable data, named constants.
- Dependencies are passed explicitly. No singletons, service locators or import-time side effects.
- Empty `__init__.py` files, absolute imports.
- Comments only for a non-obvious why. Docstrings only on public contracts.
- Tests target behavior. Domain tests need no fixtures, use cases use in-memory fakes, adapters run against real Postgres under the `integration` marker.
- Never add a dependency, abstraction, option or file the current capability does not use.

## Security invariants

- No secrets in the repository. `.env.example` holds local development values only.
- Configuration is validated at startup, and invalid configuration stops the process.
- CORS origins are explicit, and staging and production require `https`.
- Logs never contain bodies, query strings, headers other than the request ID, or exception messages.
- Errors are RFC 9457 problem details with the request ID and no internal detail or submitted input.
- The API connects as `scibiom_app` (rows only), migrations as `scibiom_owner` (schema owner).
- Database access is an allowlist. The migration that creates a context schema grants `scibiom_app` access in the same migration, and nothing grants it globally.

  ```sql
  GRANT USAGE ON SCHEMA <context> TO scibiom_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA <context>
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scibiom_app;
  ```

  Grant fewer privileges where the context needs it, such as `INSERT` only for an append-only audit log. `test_schema_privileges_integration.py` fails CI for any schema without these grants.
- Interactive API docs exist only in `local` and `test`.

Authentication, tenant isolation, row-level security, consent, audit logging and data retention are future capabilities. Never add placeholders for them or claim healthcare compliance.

## Workflow

```bash
make setup      # dependencies and .env
make db-up      # Postgres
make migrate    # migrations as the owner role
make dev        # API on :8000, web on :3000
make check      # everything CI runs
```

Every change passes `make check`. Decisions that are hard to reverse get an ADR in `docs/technical/adr/`, written in English, and the reasoning stays there. How a mechanism works today goes in `docs/technical/`, the system map in `docs/technical/ARCHITECTURE.md`, and any table or schema change updates `docs/technical/database.dbml` in the same change.
