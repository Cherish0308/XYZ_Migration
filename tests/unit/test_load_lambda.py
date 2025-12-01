from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.lambdas import load_lambda


class FakeWarehouseRepo:
    def __init__(self) -> None:
        self.copy_calls: List[Dict[str, Any]] = []

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

    # Unused in this test, but required by the interface
    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> None:  # pragma: no cover
        pass

    def fetch_one(self, sql: str, params: Optional[Tuple] = None):  # pragma: no cover
        return None


def test_load_lambda_triggers_redshift_copy(monkeypatch):
    # Arrange env
    monkeypatch.setenv("S3_BUCKET", "xyz-bucket")
    monkeypatch.setenv("S3_RAW_PREFIX", "raw")
    monkeypatch.setenv("S3_VALIDATED_PREFIX", "validated")
    monkeypatch.setenv("S3_TRANSFORMED_PREFIX", "transformed")
    monkeypatch.setenv("S3_ERROR_PREFIX", "error")
    monkeypatch.setenv("S3_RECON_PREFIX", "recon")
    monkeypatch.setenv("REDSHIFT_HOST", "dummy")
    monkeypatch.setenv("REDSHIFT_DATABASE", "dummy")
    monkeypatch.setenv("REDSHIFT_USER", "dummy")
    monkeypatch.setenv("REDSHIFT_PASSWORD", "dummy")
    monkeypatch.setenv("REDSHIFT_IAM_ROLE_ARN", "arn:aws:iam::123456789012:role/Dummy")

    fake_repo = FakeWarehouseRepo()

    # Patch RedshiftWarehouseRepository to return our fake repo
    def fake_redshift_repo_ctor(config) -> FakeWarehouseRepo:  
        return fake_repo

    monkeypatch.setattr(load_lambda, "RedshiftWarehouseRepository", fake_redshift_repo_ctor)
    monkeypatch.setattr(load_lambda, "configure_logging", lambda *args, **kwargs: None)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "xyz-bucket"},
                    "object": {
                        "key": "transformed/utilization_history/forecast_period=2025-01/file.csv"
                    },
                }
            }
        ]
    }

    # Act
    result = load_lambda.handler(event, context=None)

    # Assert Lambda result
    assert result["results"][0]["outcome"] == "LOADED"
    assert result["results"][0]["table_name"] == "utilization_history"
    assert result["results"][0]["logical_period"] == "2025-01"

    # Assert COPY was called on our fake repo
    assert len(fake_repo.copy_calls) == 1
    call = fake_repo.copy_calls[0]
    assert call["table_name"] == "stg_utilization_history"
    assert call["s3_uri"].startswith("s3://xyz-bucket/transformed/utilization_history/")
    assert call["iam_role_arn"] == "arn:aws:iam::123456789012:role/Dummy"
    assert call["file_format"] == "CSV"
    assert "IGNOREHEADER 1" in call["copy_options"]
