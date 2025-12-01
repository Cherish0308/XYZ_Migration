from __future__ import annotations

from typing import Any, Dict, List

import types

from app.lambdas import validation_lambda


class FakeS3Repo:
    def __init__(self, csv_text: str) -> None:
        self._csv_text = csv_text
        self.copied: List[Dict[str, str]] = []
        self.written: List[Dict[str, str]] = []

    def read_text(self, bucket: str, key: str) -> str:
        return self._csv_text

    def write_text(self, bucket: str, key: str, body: str) -> None:
        self.written.append({"bucket": bucket, "key": key, "body": body})

    def copy_object(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        self.copied.append(
            {
                "src_bucket": src_bucket,
                "src_key": src_key,
                "dest_bucket": dest_bucket,
                "dest_key": dest_key,
            }
        )

    # Unused interface methods in this test
    def delete_object(self, bucket: str, key: str) -> None:  
        pass

    def list_keys(self, bucket: str, prefix: str):  
        return []

    def head_object(self, bucket: str, key: str):  
        return {}


def test_validation_lambda_routes_valid_file_to_validated_prefix(monkeypatch):
    # Arrange: env
    monkeypatch.setenv("S3_BUCKET", "xyz-bucket")
    monkeypatch.setenv("S3_RAW_PREFIX", "raw")
    monkeypatch.setenv("S3_VALIDATED_PREFIX", "validated")
    monkeypatch.setenv("S3_ERROR_PREFIX", "error")
    monkeypatch.setenv("S3_RECON_PREFIX", "recon")
    monkeypatch.setenv("REDSHIFT_HOST", "dummy")
    monkeypatch.setenv("REDSHIFT_DATABASE", "dummy")
    monkeypatch.setenv("REDSHIFT_USER", "dummy")
    monkeypatch.setenv("REDSHIFT_PASSWORD", "dummy")
    monkeypatch.setenv("REDSHIFT_IAM_ROLE_ARN", "arn:aws:iam::123456789012:role/Dummy")

    csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01,10,5,2.0
"""

    fake_repo = FakeS3Repo(csv_text)

    # Patch S3ObjectStorageRepository inside the lambda to return our fake
    def fake_s3_repo_ctor() -> FakeS3Repo:
        return fake_repo

    monkeypatch.setattr(validation_lambda, "S3ObjectStorageRepository", fake_s3_repo_ctor)

    # We don't care about real logging setup in unit test
    monkeypatch.setattr(validation_lambda, "configure_logging", lambda *args, **kwargs: None)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "xyz-bucket"},
                    "object": {"key": "raw/utilization_history/forecast_period=2025-01/file.csv"},
                }
            }
        ]
    }

    # Act
    result = validation_lambda.handler(event, context=None)

    # Assert
    assert result["results"][0]["outcome"] == "SUCCEEDED"
    assert fake_repo.copied, "File should be copied to validated prefix"
    dest_key = fake_repo.copied[0]["dest_key"]
    assert dest_key.startswith("validated/utilization_history/forecast_period=2025-01/")
