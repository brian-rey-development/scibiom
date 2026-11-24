# Scibiom engineering contract

Scibiom is a personal health research and protocols assistant that will hold sensitive health data. These rules bind every human and AI contributor, and CI enforces most of them. Web-specific rules live in `apps/web/AGENTS.md`.

## Architecture

The backend is a modular monolith built on ports and adapters. Business logic lives in one framework-free package, every entry point (REST today, MCP, agent tools and workflows later) is a thin adapter over the same use cases, and every external system sits behind a port the core defines. `docs/technical/ARCHITECTURE.md` holds the repository layout and the dependency, type and data rules, and they bind every change as much as this file does.

## Code conventions

- Python 3.14 with Pyright strict and Ruff (nearly all rules). TypeScript strict with no `any`.
- Functions of 20 lines or fewer, early returns, immutable data, named constants.
- Dependencies are passed explicitly. No singletons, service locators or import-time side effects.
- Empty `__init__.py` files, absolute imports.
- Comments only for a non-obvious why. Docstrings only on public contracts.
- Tests follow the Testing section below.
- Never add a dependency, abstraction, option or file the current capability does not use.

## Testing

A test earns its place only when a bug in our code can make it fail. Each test is named as a sentence about the behavior it proves, so the test names of a module read as its rules.

| Layer | Proves | How |
|---|---|---|
| Domain | The rules of one model or value | Plain calls, no fixtures |
| Use case | Behavior across ports, commit and rollback included | In-memory fakes with real transaction semantics, a fixed clock, never mocks |
| Adapter | Our SQL, migrations and provider protocol | Real Postgres and Mailpit under the `integration` marker |
| API | Status codes, headers, cookies, validation and error bodies | `TestClient` with use cases replaced through the container factory |
| End to end | One flow through every layer | One `integration` test per flow |

Test these:

- Every rule in the spec at its boundary, meaning the last allowed value and the first rejected one.
- Every error path, and that failures stay indistinguishable wherever the spec requires it.
- Security properties, such as nothing sensitive reaching logs, errors or responses.
- Persisted formats that must never change, by pinning their exact encoding.
- Concurrency and transaction guarantees, against real Postgres with independent connections.

Do not test these:

- The standard library or a framework itself, such as Pydantic defaults, required fields and `Field` bounds, `secrets` randomness or `uuid7` uniqueness.
- Dataclass mechanics, such as equality, immutability or `replace`.
- Private functions and attributes. Reach behavior through the public surface of the module.
- A behavior that another test at the same layer already proves.

Each test covers one behavior in three blocks, arrange, act and assert, separated by blank lines. Tests are deterministic, with fixed clocks, no sleeps and no network outside `integration`, and integration tests create unique data so reruns within the same hour pass. Before a new test lands, break the rule it guards once and watch it fail.

Tests mirror the source folders of their package, integration tests end in `_integration.py`, and fakes shared by a folder live in its `conftest.py`.

## Security invariants

- No secrets in the repository. `.env.example` holds local development values only.
- Configuration is validated at startup, and invalid configuration stops the process.
- CORS origins are explicit, and staging and production require `https`.
- Logs never contain bodies, query strings, headers other than the request ID, or exception messages.
- Errors are RFC 9457 problem details with the request ID and no internal detail or submitted input.
- The API connects as `scibiom_app` and migrations as `scibiom_owner`, and database access is an allowlist granted per schema, as the Data section of `ARCHITECTURE.md` shows.
- Interactive API docs exist only in `local` and `test`.

Authentication follows `docs/specs/2026-11-24-identity-and-authentication-design.md` and ADR 0004. Tenant isolation, row-level security, consent, audit logging and data retention are future capabilities. Never add placeholders for them or claim healthcare compliance.

## Workflow

```bash
make setup      # dependencies and .env
make db-up      # Postgres
make migrate    # migrations as the owner role
make dev        # API on :8000, web on :3000
make check      # everything CI runs
```

Every change passes `make check`.

## Documentation

Each document has one job, and nothing is written twice.

| Document | Job |
|---|---|
| `docs/technical/ARCHITECTURE.md` | The repository layout and the rules the code follows, updated in the same change as the code |
| `docs/technical/adr/` | Macro decisions that are costly to reverse, with the alternatives rejected, never policy values or implementation detail |
| `docs/specs/` | Designs for the owner to review before a capability is built, not kept in sync after it merges |
| `docs/technical/database.dbml` | The current schema, updated by every table change |
| `docs/technical/BACKLOG.md` | Known technical debt and when to pay it |
