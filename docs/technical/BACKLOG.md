# Tech Debt

- [ ] @high-priority Generate request IDs on the server and keep the client's `X-Request-ID` as a separate `client_request_id`, so audit logs get a unique, unforgeable request key. Do before audit logging ships.
- [ ] @medium-priority Run readiness probes on a dedicated one-connection engine, so a saturated request pool does not fail readiness and pull healthy instances out of rotation. Do before the first deployed environment.
- [ ] @medium-priority Block one module from importing another module's internals in `apps/web` (per-module `no-restricted-imports` overrides or a JS Oxlint config). Do when the second module lands.
- [ ] @low-priority Log `status_code=None` and `outcome="aborted"` for requests cancelled before or during the response, instead of 500, so error-rate metrics stay accurate. Do when dashboards exist.
- [ ] @low-priority Fold `tools/openapi-codegen` back into `apps/web` and drop its TypeScript 5.9 once `openapi-typescript` supports TypeScript 7
