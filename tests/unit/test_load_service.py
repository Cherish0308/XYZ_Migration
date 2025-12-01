from __future__ import annotations

from typing import List, Optional, Tuple

from app.config import AppConfig
from app.repositories.metadata_repository import InMemoryMetadataRepository
from app.repositories.base import WarehouseRepository
from app.services.load_service import LoadService


class FakeWarehouseRepo(WarehouseRepository):
    def __init__(self) -> None:
        self.copy_calls = []

    def copy_from_s3(
        self,
        table_name: str,
        s3_uri: str,
        iam_role_arn: str,
        file_format: str,
        copy_options: Optional[List[str]] = None,
    ) -> None:
        self.copy_calls.append(
            {
                "table_name": table_name,
                "s3_uri": s3_uri,
                "iam_role_arn": iam_role_arn,
                "file_format": file_format,
                "copy_options": copy_options or [],
            }
        )

    # Unused in this test
    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> None:  # pragma: no cover
        pass

    def fetch_one(self, sql: str, params: Optional[Tuple] = None):  # pragma: no cover
        return None


def _make_config() -> AppConfig:
    return AppConfig(
        env="test",
        app_name="xyz-pricing-migration",
        log_level="INFO",
        s3_bucket="xyz-bucket",
        s3_raw_prefix="raw",
        s3_validated_prefix="validated",
        s3_transformed_prefix="transformed",
        s3_error_prefix="error",
        s3_recon_prefix="recon",
        redshift_host="host",
        redshift_port=5439,
        redshift_database="db",
        redshift_user="user",
        redshift_password="pw",
        redshift_iam_role_arn="arn:aws:iam::123456789012:role/RedshiftRole",
        dry_run=False,
    )


def test_load_service_issues_copy_with_expected_params():
    config = _make_config()
    warehouse = FakeWarehouseRepo()
    metadata = InMemoryMetadataRepository()
    service = LoadService(warehouse, metadata, config)

    key = "transformed/utilization_history/forecast_period=2025-01/file.csv"

    result = service.load_transformed_file(
        table_name="utilization_history",
        logical_period="2025-01",
        s3_key=key,
    )

    # Assert LoadResult
    assert result.table_name == "utilization_history"
    assert result.redshift_table == "stg_utilization_history"
    assert result.s3_uri == f"s3://{config.s3_bucket}/{key}"

    # Assert COPY call
    assert len(warehouse.copy_calls) == 1
    call = warehouse.copy_calls[0]
    assert call["table_name"] == "stg_utilization_history"
    assert call["s3_uri"] == f"s3://{config.s3_bucket}/{key}"
    assert call["iam_role_arn"] == config.redshift_iam_role_arn
    assert call["file_format"] == "CSV"
    assert "IGNOREHEADER 1" in call["copy_options"]
