# Web architecture

The web app is a single-page React app built with Vite, and it calls the FastAPI backend directly from the browser with TanStack Query. A separate frontend server would add nothing, because the API already owns every server concern and `vite build` emits static files any host can serve. `pnpm lint` enforces the import rules below through `.oxlintrc.json`.

## Tree

```text
src/
  app/        entry point (main.tsx), root component, pages and globals.css
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

`core/env/public-env.ts` validates the `VITE_*` values the browser needs with zod and exports `parsePublicEnv(source)`. `core/env/build-env.ts` wraps it for `vite.config.ts`, which loads the repo root `.env` files and stops `vite dev`, `vite build` and `vite preview` on any invalid value. Every `VITE_*` value is inlined into the browser bundle, so the build also rejects any `VITE_*` key that `public-env.ts` does not declare, which keeps a stray secret in the shared root `.env` from shipping. The build reads `SCIBIOM_ENVIRONMENT`, the same setting the API uses, and in `staging` and `production` it requires an `https` API URL with a public host, so a deploy has to set both in its build environment.

`core/env/browser-env.ts` exports the parsed `publicEnv` from `import.meta.env`. It lives apart because the config imports the parsers in Node, where `import.meta.env` does not exist.

## TypeScript

The app uses the native TypeScript 7 compiler through `pnpm typecheck`, since `vite build` strips types without checking them. `tsconfig.json` covers `src/` with browser types only, so `process` is a type error there, and `tsconfig.node.json` covers the Vite and Vitest configs with Node types. `openapi-typescript` needs the TypeScript 5.9 JavaScript API, which TypeScript 7 does not provide, so the generator lives in `tools/openapi-codegen` with its own TypeScript 5.9 and `generate:api` calls it.

## Lint notes

`typescript/prefer-readonly-parameter-types` stays off because it flags every parameter typed from a library or generated type, which makes it noise for this codebase.

## Known lint gap

`no-restricted-imports` matches import paths but does not know which module a file belongs to, so a segment such as `api/` can still import another module's internals through `@modules/<other>/<segment>` and the linter will not object. Reviewers check that case.
