mssql_inventory — how to run
============================

This folder contains the MSSQL variant of the data faker services. Key files:
- `docker-compose.yml` — Compose file to run individual services (orders-creator, orders-modifier, orders-purger)
- `config.yml` — service configuration (DATABASE_URL, WAIT_TIME_MS, PREGENERATE_COUNT, etc.)
- Python services: `orders_creator.py`, `supplier_creator.py`, `orders_modifier.py`, `orders_purger.py`

Prerequisites
- Docker and docker-compose
- A reachable Microsoft SQL Server instance (hostname/port in `config.yml`)

Quick start (recommended)
1. Build the image (the compose file is configured to use the repo-level Dockerfile):

```bash
cd /docker/sql-helper/mssql_inventory
# build the image(s) referenced by this compose file
docker compose build --pull
```

2. Start one service (example: orders-creator):

```bash
# start only the orders-creator service
docker compose up -d --build orders-creator
# view logs
docker compose logs -f --tail=200 orders-creator
```

Configuration notes
- `config.yml` contains `default_config.DATABASE_URL` — update this to match your environment.
  - Example DSN (uses ODBC Driver 18):
    mssql+pyodbc://user:Pass@hostname:1433/database?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
  - If you see: `SSL Provider: ... self-signed certificate`, add `&TrustServerCertificate=yes` (lab/dev only). For production, use CA-signed certs.
  - If pyodbc errors with "Can't open lib 'ODBC Driver 17 for SQL Server'", either change the driver name to the installed version or install the matching driver in the image.

- `services.supplier_creator.PREGENERATE_COUNT` controls how many suppliers to pre-generate at startup (orders-creator uses this value). If `PREGENERATE_COUNT` is 0 and no suppliers exist, the service will create 1 supplier to ensure orders can reference a supplier.

- `services.*.WAIT_TIME_MS` expects a 2-element list of milliseconds [min_ms, max_ms]; services pick a random value between them before each run and log the chosen duration.

Troubleshooting
- "NoSuchTableError: suppliers" or "orders" — the services will now auto-create minimal tables if they're missing. For production-like data, apply your DDL (see project DDL.sql) to create the full schema.
- "Command Out of Sync" or "Lost connection to MySQL server during query" (MySQL) — this is caused by sharing DB connections across forked processes. The services close/dispose the parent engine after pre-generation; avoid creating engines in the parent before forking.

Stopping services

```bash
docker compose stop orders-creator
docker compose down
```

Logs and debugging
- Tail logs with `docker compose logs -f orders-creator` or check `/var/log/sql-helper/` if you mounted logs.

Next steps
- If you want a single command to apply the project's DDL before starting services, I can add a `make init-db` or `docker-compose run` helper that runs `DDL.sql` against the target database.
