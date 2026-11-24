# Database roles and migrations

The API and the migration tool connect to the same Postgres database under two different roles, so that a bug in request handling can never change the schema. [ADR 0002](adr/0002-least-privilege-database-roles.md) explains why the split exists, and this page describes how it is wired.

## Roles

| Role | Used by | Rights |
|---|---|---|
| `scibiom_owner` | `alembic upgrade head` and other administrative commands | Owns the database and every context schema, so it can create, alter and drop objects. |
| `scibiom_app` | The API process | Reads and writes rows, and nothing else. Created with `NOINHERIT`, so it holds only the privileges granted to it directly. |

The API never receives the owner credentials. Each role has its own connection setting, so the split is visible in every environment.

| Setting | Role |
|---|---|
| `SCIBIOM_DATABASE__URL` | `scibiom_app` |
| `SCIBIOM_MIGRATION_DATABASE_URL` | `scibiom_owner` |

## Local setup

The Postgres container runs `docker/postgres/initdb/10-roles.sh` the first time it initialises. The script creates both roles, creates the `scibiom` database owned by `scibiom_owner`, gives `scibiom_app` permission to connect, and revokes everything else from `PUBLIC`. It grants no schema or table access. Alembic's `env.py` creates the `alembic` schema as the owner before the first migration, and since nothing grants the application role access to it, the role cannot read or rewrite which migrations have run.

Hosted environments will create the same roles through infrastructure code. `make db-reset` destroys local data and runs the script again.

## Writing a migration

A migration that creates a context schema also grants the application role access to it, in the same migration, with the two statements in `AGENTS.md`. A context that needs less, such as an append-only audit log, grants fewer privileges. `test_schema_privileges_integration.py` fails for any schema without these grants, and it checks itself against a schema created without them. Migrations run with `lock_timeout` set from `SCIBIOM_MIGRATION_LOCK_TIMEOUT_MS`, which defaults to 5000. A migration that cannot take its lock in that time fails instead of queueing every request behind it.

Offline migrations are not supported, and `env.py` raises if asked for one. `make migration name=...` autogenerates a revision across all schemas. Until the first context passes its table metadata to `env.py`, autogenerate stops with an error instead of producing an empty or destructive migration.

The integration tests in `packages/infrastructure/tests/database/` run against real Postgres after `make migrate`, so a missing grant fails CI and does not wait to surface as a runtime permission error.

## Connection behavior

The API engine uses a pool of 5 connections with 5 overflow, a 5 second connect timeout and a 15 second statement timeout. Each value has bounds validated at startup, and an invalid value stops the process. The engine hides SQL parameters from error output, and `SecretStr` keeps the URLs out of logs.

## Debugging

Connect to a local database with the role you actually want to test. Using `scibiom_owner` for ad hoc queries bypasses row-level security once it exists, so it will hide the very problems the application role would hit.
