# Scibiom

Scibiom is a personal health research and protocols assistant. The repository holds the foundation only, meaning the monorepo layout, the backend skeleton, database wiring, health checks and the engineering rules that CI enforces. The next capability is Identity & Personal Accounts, which will let each person own their data and keep it isolated from everyone else's.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/), which also installs Python 3.14, along with Node.js 24, pnpm and Docker with the Compose plugin, because the local Postgres runs in a container.

## Getting started

```bash
make setup
make db-up
make migrate
make dev
```

When `make dev` reports that both servers are ready, open http://localhost:3000 for the web app and http://127.0.0.1:8000/docs for the API documentation, which is served only in the `local` and `test` environments. Run `make help` to list every other target, and `make check` to run everything CI runs.

## Configuration

Settings come from the root `.env`, which `make setup` creates from `.env.example`. The process validates them at startup and refuses to run with invalid values. Names use the `SCIBIOM_` prefix, and a double underscore separates nested settings, so `SCIBIOM_DATABASE__URL` sets the `url` field of the `database` section. The example file holds local development values only, and `.env` is ignored by git.

## Documentation

- [AGENTS.md](AGENTS.md) is the engineering contract for every contributor, human or AI.
- [docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md) maps the system and its dependency direction.
- [docs/technical/](docs/technical/) explains how individual mechanisms work today.
- [docs/technical/adr/](docs/technical/adr/) records decisions that are costly to reverse, with the alternatives rejected.
- [docs/technical/database.dbml](docs/technical/database.dbml) is the current database schema.
- [docs/roadmap.md](docs/roadmap.md) lists the planned capabilities.
- [docs/technical/BACKLOG.md](docs/technical/BACKLOG.md) tracks known technical debt.
