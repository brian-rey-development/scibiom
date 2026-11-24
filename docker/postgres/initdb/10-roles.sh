#!/usr/bin/env bash
set -euo pipefail

: "${SCIBIOM_OWNER_PASSWORD:?}"
: "${SCIBIOM_APP_PASSWORD:?}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\getenv owner_password SCIBIOM_OWNER_PASSWORD
\getenv app_password SCIBIOM_APP_PASSWORD

CREATE ROLE scibiom_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'owner_password';
CREATE ROLE scibiom_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';

CREATE DATABASE scibiom OWNER scibiom_owner;
REVOKE ALL ON DATABASE scibiom FROM PUBLIC;
GRANT CONNECT ON DATABASE scibiom TO scibiom_app;

\connect scibiom

REVOKE ALL ON SCHEMA public FROM PUBLIC;

SQL
