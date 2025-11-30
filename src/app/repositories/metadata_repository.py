from __future__ import annotations

from typing import Dict, List

from app.repositories.base import MetadataRepository


class InMemoryMetadataRepository(MetadataRepository):
    """
    Simple in-memory schema registry for XYZ pricing migration.

    In a real system this might be backed by AWS Glue, a dbt manifest, or a
    dedicated metadata service. Keeping it in-memory makes unit tests fast
    and keeps business logic decoupled from infrastructure.
    """

    def __init__(self) -> None:
        # column_name -> logical_type
        self._schemas: Dict[str, Dict[str, str]] = {
            "utilization_history": {
                "employer_id": "STRING",
                "gym_id": "STRING",
                "product_code": "STRING",
                "forecast_period": "PERIOD",
                "actual_visits": "INT",
                "eligible_members": "INT",
                "utilization_rate": "DECIMAL",
            },
            "pricing_rules": {
                "rule_id": "STRING",
                "product_code": "STRING",
                "utilization_band_min": "DECIMAL",
                "utilization_band_max": "DECIMAL",
                "price_per_visit": "DECIMAL",
                "price_pmpm": "DECIMAL",
                "effective_start_date": "DATE",
                "effective_end_date": "DATE",
            },
            "forecasts": {
                "run_id": "STRING",
                "employer_id": "STRING",
                "gym_id": "STRING",
                "product_code": "STRING",
                "forecast_period": "PERIOD",
                "forecast_visits": "DECIMAL",
            },
            "forecast_runs": {
                "run_id": "STRING",
                "forecast_period": "PERIOD",
                "created_at": "TIMESTAMP",
                "model_version": "STRING",
                "status": "STRING",
            },
        }

        # required columns for validation
        self._required: Dict[str, List[str]] = {
            "utilization_history": [
                "employer_id",
                "gym_id",
                "product_code",
                "forecast_period",
                "actual_visits",
            ],
            "pricing_rules": [
                "rule_id",
                "product_code",
                "utilization_band_min",
                "utilization_band_max",
                "price_per_visit",
                "price_pmpm",
                "effective_start_date",
            ],
            "forecasts": [
                "run_id",
                "employer_id",
                "gym_id",
                "product_code",
                "forecast_period",
                "forecast_visits",
            ],
            "forecast_runs": [
                "run_id",
                "forecast_period",
                "created_at",
                "model_version",
                "status",
            ],
        }

        # business keys for dedupe/DQ
        self._business_keys: Dict[str, List[str]] = {
            "utilization_history": ["employer_id", "gym_id", "product_code", "forecast_period"],
            "pricing_rules": ["rule_id"],
            "forecasts": ["run_id", "employer_id", "gym_id", "product_code", "forecast_period"],
            "forecast_runs": ["run_id"],
        }

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        return self._schemas[table_name]

    def get_required_columns(self, table_name: str) -> List[str]:
        return self._required[table_name]

    def get_redshift_table(self, snowflake_table: str) -> str:
        # Simple convention: stg_<source_table>
        return f"stg_{snowflake_table}"

    def get_business_keys(self, table_name: str) -> List[str]:
        return self._business_keys[table_name]
