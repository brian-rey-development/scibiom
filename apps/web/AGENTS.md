<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Web architecture

The web app calls the FastAPI backend directly from the browser with TanStack Query. `pnpm lint` enforces the import rules below through `.oxlintrc.json`.

## Tree

```text
src/
  app/        Next.js routing only (layout, pages, globals.css)
  core/       app-wide foundations: env, api (client and generated schema), query, providers
  modules/    one folder per product capability
  shared/     generic building blocks with no business meaning (ui, hooks, utils)
```

Folders are created when their first file arrives. Imports use `@core/*`, `@modules/*` and `@shared/*`. `../` is forbidden, and `./` is allowed only inside the same folder. Tests sit beside the file they test as `x.test.ts`.

## Dependency direction

`app` imports modules, modules import `core` and `shared`, and `core` and `shared` never import modules. `shared` never imports `core`. `app` reaches a module only through `@modules/<name>`, and a module never imports another module's internals.

## Module segments

| Segment    | Contains                                                              | May import                        |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| `types/`   | TypeScript types, usually derived from `@core/api/schema`             | nothing from other segments       |
| `schemas/` | zod schemas for input and form validation                             | `types/`                          |
| `api/`     | typed fetchers over `apiClient`, one per backend operation            | `types/`, `schemas/`, `@core/api` |
| `hooks/`   | TanStack Query hooks wrapping `api/`, with query keys colocated       | `api/`, `types/`, `schemas/`      |
| `ui/`      | components                                                            | `hooks/`, `types/`, `schemas/`    |
| `index.ts` | the module's public surface, reaching its segments through `./` paths | own segments                      |

Only `api/` may import `@core/api/client`. `types/` may also import `@core/api/schema`.

## Environment

`core/env/public-env.ts` validates `NEXT_PUBLIC_*` values with zod and exports `parsePublicEnv(source)` and the parsed `publicEnv`. `next.config.ts` runs the same validation after loading the repo root `.env` files, so `next dev`, `next build` and `next start` stop on an invalid value.

## TypeScript

The app uses the native TypeScript 7 compiler, and `next build` runs it through the project `tsc` CLI. `openapi-typescript` needs the TypeScript 5.9 JavaScript API, which TypeScript 7 does not provide, so the generator lives in `tools/openapi-codegen` with its own TypeScript 5.9 and `generate:api` calls it.

## Lint notes

`typescript/prefer-readonly-parameter-types` stays off because it flags every parameter typed from a library or generated type, which makes it noise for this codebase.

## Known lint gap

`no-restricted-imports` matches import paths but does not know which module a file belongs to, so a segment such as `api/` can still import another module's internals through `@modules/<other>/<segment>` and the linter will not object. Reviewers check that case.
