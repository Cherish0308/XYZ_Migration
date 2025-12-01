# XYZ Dynamic Pricing & Utilization Migration (Snowflake → Redshift)

## 1. Overview

This project implements an end-to-end, production-style data pipeline for **XYZ Fitness**, a multi-tenant fitness subscription platform.

XYZ offers subscription products to **employers** and **insurers** that give **members** access to a network of gyms and studios. Pricing and payouts are driven by **actual utilization** (gym visits) and **forecasted utilization** per employer / gym / product / month.

Today, the core pricing and utilization analytics run in **Snowflake**. XYZ is migrating these workloads to **Amazon Redshift** to:

- Reduce platform cost by consolidating analytics on AWS.
- Bring pricing and utilization logic closer to upstream AWS data sources.
- Standardize on S3-based ingestion and Redshift-based serving.

This codebase simulates a **Snowflake → Redshift** migration for the **dynamic pricing & utilization engine**, using Python 3, S3 and AWS Lambda with a SOLID, testable architecture.

It is designed as a portfolio-quality repository that shows how I would structure a real-world migration project for a role like:

- **Senior Data Engineer – Snowflake / Redshift Migration**
- **AWS Data Engineer – Redshift & S3-based Data Warehouse**


## 2. Business Problem

### 2.1 Domain

Key entities:

- **Employers / Insurers** – who pay for members’ access.
- **Members** – end users visiting gyms.
- **Gyms / Studios** – who receive payouts for visits.
- **Products** – e.g. `STANDARD`, `SELECT` memberships.
- **Utilization history** – per employer / gym / product / forecast_period:
  - `actual_visits`
  - `eligible_members`
  - `utilization_rate`
- **Pricing rules** – how utilization bands map to employer pricing and gym payouts.
- **Forecasts** – projected utilization by month.

### 2.2 Core migration challenge

XYZ is migrating the **utilization and pricing analytics** from Snowflake to Redshift while:

- Preserving **data correctness** across historical periods.
- Keeping **schemas compatible** (Snowflake exports → Redshift staging).
- Enforcing **data quality and reconciliation** (Snowflake vs Redshift aggregates).
- Making the migration **repeatable and automated** (idempotent, event-driven).

The project focuses on the **utilization_history** dataset as a representative slice of the migration.


## 3. High-Level Architecture

### 3.1 Data flow

**Snowflake → S3 → Redshift**, with validation and DQ:

1. **Snowflake exports**:
   - Periodic CSV exports (or CDC-style extracts) land in S3 under the **raw** prefix.

2. **Ingestion Lambda** (`ingestion_lambda`):
   - Triggered by S3 events on the `raw/` prefix.
   - Registers an **ingestion job** with an idempotency key.
   - Writes a small JSON record into the `recon/` prefix.

3. **Validation Lambda** (`validation_lambda`):
   - Triggered by S3 events on the `raw/` prefix (or wired via notifications).
   - Reads the raw CSV, validates **schema** and **business rules**:
     - Required columns.
     - Basic type checks.
     - Business constraints (e.g. non-negative visits).
   - Routes the file to:
     - `validated/` prefix on success.
     - `error/` prefix on failure.
   - Logs a validation summary into `recon/`.

4. **Transform Lambda** (`transform_lambda`):
   - Triggered by S3 events on the `validated/` prefix.
   - Uses **logical schema metadata** to:
     - Normalize header names.
     - Enforce consistent types (e.g. INT, DECIMAL, DATE-like).
     - Normalize forecast period fields.
   - Writes normalized CSV to the `transformed/` prefix.

5. **Load Lambda** (`load_lambda`):
   - Triggered by S3 events on the `transformed/` prefix.
   - Uses a `LoadService` and `RedshiftWarehouseRepository` to:
     - Issue a **Redshift COPY** from S3 into a staging table (e.g. `stg_utilization_history`).
   - COPY options (ignore header, null handling, truncation, etc.) are centrally managed.

6. **DQ Lambda** (`dq_lambda`):
   - Invoked with an explicit event payload:
     - `table_name`, `numeric_columns`, `baseline.s3_key`, `migrated.s3_key`, `tolerance_pct`.
   - Reads **baseline** (Snowflake export) and **migrated** (Redshift snapshot) CSVs from S3.
   - Uses `TransformationService` for consistent typing.
   - Uses `DQService` to reconcile:
     - Row counts.
     - Column sums for selected numeric metrics.
   - Writes a DQ summary JSON into `recon/`.


### 3.2 S3 zones / prefixes

- `raw/` – Snowflake exports and raw feeds.
- `validated/` – schema- and rule-validated files.
- `transformed/` – type-normalized, Redshift-ready files.
- `error/` – rejected files.
- `recon/` – small JSON artifacts:
  - Ingestion registrations.
  - Validation summaries.
  - DQ reconciliation reports.


## 4. Project Layout

```text
.
├── src/
│   └── app/
│       ├── config.py               # AppConfig & env loading
│       ├── logging_config.py       # CloudWatch-friendly logging setup
│       ├── exceptions.py           # AppError hierarchy
│       ├── models/                 # Domain models (utilization, jobs, etc.)
│       ├── repositories/           # S3, Redshift, metadata repositories
│       ├── services/               # Validation, transform, load, DQ services
│       ├── validators/             # Schema & business validators
│       ├── utils/                  # JSON, S3 path utils, idempotency helpers
│       └── lambdas/                # Lambda entrypoints (handlers)
│           ├── ingestion_lambda.py
│           ├── validation_lambda.py
│           ├── transform_lambda.py
│           ├── load_lambda.py
│           └── dq_lambda.py
├── tests/
│   ├── unit/                       # Unit tests for services, utils, lambdas
│   └── integration/                # (placeholder for future integration tests)
├── pytest.ini
├── requirements.txt
└── README.md
