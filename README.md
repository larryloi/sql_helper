# sql_helper
## Introduction
It is a tools to simulate rdbms activities, there is 2 type of databases below support currently 
- MySQL
- SQL Server

```markdown
# sql-helper

Small collection of data-faker services that target MySQL and MSSQL for local/dev testing.

This repo provides:
- a single Dockerfile at the repository root that is used to build the service image
- two per-backend folders containing compose files and Python services:
  - `mysql_inventory/`
  - `mssql_inventory/`

This README focuses on building the image and how the compose files are intended to be used.

Prerequisites
- Docker (20.10+)
- Docker Compose v2 (use the `docker compose` command)

Build the image

The project uses a repo-level Dockerfile (located at `/docker/sql-helper/Dockerfile`).
You can build the runtime image directly or via the per-backend compose files (they point the build context to the repo root):

```bash
# from repo root (recommended)
cd /docker/sql-helper
docker build -t quay.io/larryloi/sql_helper-faker:local -f Dockerfile .

# or let compose build the image when bringing up a service (see per-backend README files)
cd mssql_inventory
docker compose build --pull
```

Quick commands (examples)

```bash
# Build app image from repo root
cd /docker/sql-helper
make build.app

# Start MSSQL orders creator (compose file lives in mssql_inventory/)
cd /docker/sql-helper/mssql_inventory
docker compose up -d --build orders-creator
docker compose logs -f --tail=200 orders-creator

# Start MySQL orders creator
cd /docker/sql-helper/mysql_inventory
docker compose up -d --build orders-creator
docker compose logs -f --tail=200 orders-creator
```

Running services
- Each backend folder contains a `docker-compose.yml` that mounts the folder's `config.yml` into the container and runs a single Python service.
- To run an individual service (example: MSSQL orders-creator):

```bash
cd /docker/sql-helper/mssql_inventory
docker compose up -d --build orders-creator
docker compose logs -f --tail=200 orders-creator
```

Configuration
- See `mssql_inventory/config.yml` and `mysql_inventory/config.yml` for service-specific settings.
- Important keys:
  - `default_config.DATABASE_URL` — DSN used by SQLAlchemy. For MSSQL use a pyodbc DSN like:
    `mssql+pyodbc://user:Pass@hostname:1433/database?driver=ODBC+Driver+18+for+SQL+Server`
    - The Dockerfile installs ODBC Driver 18 by default. If your environment uses Driver 17, either change the DSN or install the matching driver.
    - For dev environments with self-signed certs you can append `&TrustServerCertificate=yes` to the DSN (not recommended for production).
  - `WAIT_TIME_MS` — a 2-element list of milliseconds [min_ms, max_ms]. Services pick a random millisecond value between them before each run and log the chosen value.
  - `PREGENERATE_COUNT` (under `supplier_creator`) — number of suppliers to pre-generate at startup. `orders_creator` will use this to create suppliers if none exist.

Schema / DDL
- The repository contains DDL files you can apply before running services:
  - MySQL: `mysql_inventory/DDL.sql`, `mysql_inventory/ACL.sql`
  - MSSQL: `mssql_inventory/DDL.sql`
- During development the services will auto-create minimal `suppliers` / `orders` tables if they're missing. For production or realistic testing run the DDL first.

Init DB (manual)

If you prefer to apply the DDL files manually, here are example commands you can adapt for your environment:

# MySQL (local or remote) — replace placeholders and run from a machine with mysql client installed
```bash
mysql -h <mysql_host> -P 3306 -u <user> -p'<password>' < mysql_inventory/DDL.sql
```

# MSSQL using sqlcmd (replace placeholders)
```bash
sqlcmd -S <mssql_server>,1433 -U <user> -P '<password>' -i mssql_inventory/DDL.sql
```

You can also run a client container to execute the DDL against a network-accessible database (use `--network` to reach the DB container).

Troubleshooting notes
- MSSQL SSL errors: if you see an error like `SSL Provider: certificate verify failed` and you're using a self-signed cert, add `&TrustServerCertificate=yes` to the `DATABASE_URL` in `mssql_inventory/config.yml` for lab/dev use.
- ODBC driver not found: if pyodbc reports it can't open `ODBC Driver 17 for SQL Server`, either change the DSN to `ODBC Driver 18 for SQL Server` (the image installs msodbcsql18) or install the driver matching the DSN in the Dockerfile.
- MySQL "Command Out of Sync" or lost connections: avoid creating/holding database engines in the parent process before forking child worker processes — the services attempt to close the parent engine after any pre-fork DB work to avoid this.

Per-backend instructions
- `mssql_inventory/README.md` — MSSQL-specific run instructions and debugging tips.
- `mysql_inventory/README.md` — MySQL-specific run instructions and debugging tips.

If you want I can add an `init-db` helper (Makefile target or compose service) that applies the DDL automatically before starting services.
```