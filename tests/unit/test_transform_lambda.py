from __future__ import annotations

from typing import Any, Dict, List

from app.lambdas import transform_lambda


class FakeS3Repo:
    def __init__(self, csv_text: str) -> None:
        self._csv_text = csv_text
        self.written: List[Dict[str, str]] = []

    def read_text(self, bucket: str, key: str) -> str:
        return self._csv_text

    def write_text(self, bucket: str, key: str, body: str) -> None:
        self.written.append({"bucket": bucket, "key": key, "body": body})

    # Unused methods to satisfy interface
    def copy_object(self, *args, **kwargs):  
        pass

    def delete_object(self, *args, **kwargs):  
        pass

    def list_keys(self, *args, **kwargs):  
        return []

    def head_object(self, *args, **kwargs):  
        return {}


def test_transform_lambda_writes_to_transformed_prefix(monkeypatch):
    # Arrange env
    monkeypatch.setenv("S3_BUCKET", "xyz-bucket")
    monkeypatch.setenv("S3_VALIDATED_PREFIX", "validated")
    monkeypatch.setenv("S3_TRANSFORMED_PREFIX", "transformed")
    monkeypatch.setenv("S3_ERROR_PREFIX", "error")
    monkeypatch.setenv("S3_RECON_PREFIX", "recon")
    monkeypatch.setenv("REDSHIFT_HOST", "dummy")
    monkeypatch.setenv("REDSHIFT_DATABASE", "dummy")
    monkeypatch.setenv("REDSHIFT_USER", "dummy")
    monkeypatch.setenv("REDSHIFT_PASSWORD", "dummy")
    monkeypatch.setenv("REDSHIFT_IAM_ROLE_ARN", "arn:aws:iam::123456789012:role/Dummy")

    csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01-15,10,5,2.0
"""

    fake_repo = FakeS3Repo(csv_text)

    # Patch S3ObjectStorageRepository to return our fake instance
    def fake_s3_repo_ctor() -> FakeS3Repo:
        return fake_repo

    monkeypatch.setattr(transform_lambda, "S3ObjectStorageRepository", fake_s3_repo_ctor)

    # Avoid real logging setup in unit tests
    monkeypatch.setattr(transform_lambda, "configure_logging", lambda *args, **kwargs: None)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "xyz-bucket"},
                    "object": {"key": "validated/utilization_history/forecast_period=2025-01/file.csv"},
                }
            }
        ]
    }

    # Act
    result = transform_lambda.handler(event, context=None)

    # Assert
    assert result["results"][0]["outcome"] == "SUCCEEDED"
    assert fake_repo.written, "Transform lambda should write a file"

    written = fake_repo.written[0]
    assert written["key"].startswith("transformed/utilization_history/forecast_period=2025-01/")

    # Body should contain normalized period 2025-01 (not 2025-01-15)
    assert "2025-01-15" not in written["body"]
    assert "2025-01" in written["body"]
