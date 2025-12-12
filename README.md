# XYZ Dynamic Pricing & Utilization Migration (Snowflake → Redshift)

## 1. Overview

This repository implements a production-style data pipeline for **XYZ Fitness**, a multi-tenant fitness subscription platform.

XYZ sells subscription products to employers and insurers that give members access to a network of gyms and studios. Pricing and payouts are driven by **actual utilization** (gym visits) and **forecasted utilization** per employer / gym / product / month.

Today, the core pricing and utilization analytics run in **Snowflake**. XYZ is migrating these workloads to **Amazon Redshift** to:

- Reduce platform cost by consolidating analytics on AWS.
- Bring pricing and utilization logic closer to upstream AWS data sources.
- Standardize on **S3-based ingestion** and **Redshift-based serving**.

This codebase simulates a **Snowflake → Redshift migration** for the dynamic pricing & utilization engine, using **Python, S3, and AWS Lambda**, with a **SOLID, testable architecture**.

---

## 2. Business Problem

### 2.1 Domain

Key entities:

- **Employers / Insurers** – sponsors of the membership.
- **Members** – end users visiting gyms.
- **Gyms / Studios** – providers receiving payouts.
- **Products** – e.g. `STANDARD`, `SELECT` membership tiers.
- **Utilization history** – per employer / gym / product / forecast_period:
  - `actual_visits`
  - `eligible_members`
  - `utilization_rate`
- **Pricing rules** – utilization bands → employer pricing and gym payouts.
- **Forecasts** – projected utilization by month.
- **Forecast runs** – metadata about forecast jobs, status, and timing.

### 2.2 Core migration challenge

XYZ is migrating utilization and pricing analytics from **Snowflake** to **Redshift** while:

- Preserving **data correctness** across historical periods.
- Keeping **schemas compatible** (Snowflake exports → Redshift staging).
- Enforcing **data quality & reconciliation** (Snowflake vs Redshift aggregates).
- Making the migration **repeatable and automated** (idempotent, event-driven).

This project focuses on the `utilization_history` dataset as a representative slice of the overall migration, but the design is metadata-driven and extendable to other tables (`pricing_rules`, `forecasts`, `forecast_runs`, etc.).

---

## 3. High-Level Architecture

### 3.1 Data flow

End-to-end flow: **Snowflake → S3 → Redshift**, with validation and DQ checks:

1. **Snowflake exports to S3 (raw zone)**  
   Periodic CSV exports (or CDC-style extracts) land in S3 under the `raw/` prefix, e.g.:

   - `raw/utilization_history/forecast_period=2025-01/file.csv`

2. **Ingestion Lambda (`ingestion_lambda`)**

   - Triggered by S3 events on the `raw/` prefix.
   - Registers an ingestion job with an **idempotency key**.
   - Writes a small JSON **reconciliation record** to the `recon/` prefix (job id, table, period, source key).
   - Designed to be **idempotent**: repeated events for the same file do not create duplicate jobs.

3. **Validation Lambda (`validation_lambda`)**

   - Triggered by S3 events on the `raw/` prefix (or wired via S3 notifications / EventBridge).
   - Reads the raw CSV and validates:
     - Required columns.
     - Basic type checks (INT, DECIMAL, DATE-like).
     - Business constraints (e.g., non-negative visits, utilization rate consistency).
   - Routes the file to:
     - `validated/` prefix on success.
     - `error/` prefix on failure.
   - Writes a validation summary JSON into `recon/`.

4. **Transform Lambda (`transform_lambda`)**

   - Triggered by S3 events on the `validated/` prefix.
   - Uses **metadata** to:
     - Normalize header names.
     - Enforce consistent types (INT/DECIMAL/DATE/PERIOD).
     - Normalize `forecast_period`.
   - Writes normalized CSV to the `transformed/` prefix.
   - Implementation is split into:
     - `transform_lambda.py` – thin AWS Lambda handler.
     - `transform_lambda_helpers.py` – orchestration and CSV processing helpers.

5. **Load Lambda (`load_lambda`)**

   - Triggered by S3 events on the `transformed/` prefix.
   - Uses `LoadService` and `RedshiftWarehouseRepository` to:
     - Issue a **Redshift COPY** from S3 into a staging table (e.g. `stg_utilization_history`).
   - COPY options (ignore header, null handling, date format, etc.) are centrally managed in the repository.

6. **DQ Lambda (`dq_lambda`)**

   - Invoked with an explicit event payload:
     - `table_name`, `numeric_columns`, `baseline.s3_key`, `migrated.s3_key`, `tolerance_pct`.
   - Reads:
     - Baseline CSV (Snowflake export before migration).
     - Migrated CSV (Redshift snapshot after COPY).
   - Uses `TransformationService` for consistent typing, and `DQService` to reconcile:
     - Row counts.
     - Column sums for numeric metrics (e.g. `actual_visits`, `eligible_members`).
   - Writes a DQ summary JSON into `recon/` and marks pass/fail based on tolerance thresholds.

### 3.2 S3 zones / prefixes

- `raw/` – Snowflake exports and raw feeds.
- `validated/` – schema- and rule-validated files.
- `transformed/` – type-normalized, Redshift-ready files.
- `error/` – rejected files.
- `recon/` – small JSON artifacts:
  - Ingestion registrations.
  - Validation summaries.
  - DQ reconciliation reports.

---

## 4. Project Layout

```text
.
├── src/
│   └── app/
│       ├── config.py                 # AppConfig & env loading (env vars)
│       ├── logging_config.py         # CloudWatch-friendly logging setup
│       ├── exceptions.py             # AppError hierarchy
│       ├── models/                   # Domain models (e.g., ingestion jobs, DQ results)
│       ├── repositories/             # S3, Redshift, metadata repositories
│       ├── services/                 # Validation, transform, load, DQ services
│       ├── validators/               # Schema & business validators (per-table)
│       ├── utils/                    # JSON, S3 path utils, idempotency, time parsing
│       └── lambdas/                  # Lambda entrypoints (handlers)
│           ├── ingestion_lambda.py
│           ├── validation_lambda.py
│           ├── transform_lambda.py
│           ├── transform_lambda_helpers.py
│           ├── load_lambda.py
│           └── dq_lambda.py
├── tests/
│   ├── unit/                         # Unit tests for services, utils, lambdas
│   └── integration/                  # Placeholder for future integration tests
├── infra/                            # (Optional) IaC stubs / notes for AWS deployment
├── pytest.ini
├── requirements.txt
└── README.md
