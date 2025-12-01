from __future__ import annotations

import json
from typing import Any, Dict

from app.lambdas import dq_lambda


class FakeS3Repo:
    def __init__(self, objects: Dict[str, str]) -> None:
        self._objects = objects
        self.written = []

    def read_text(self, bucket: str, key: str) -> str:
        return self._objects[key]

    def write_text(self, bucket: str, key: str, body: str) -> None:
        self.written.append({"bucket": bucket, "key": key, "body": body})

    # Unused methods
    def copy_object(self, *args, **kwargs):  
        pass

    def delete_object(self, *args, **kwargs): 
        pass

    def list_keys(self, *args, **kwargs):  
        return []

    def head_object(self, *args, **kwargs):  
        return {}


def test_dq_lambda_reconciles_baseline_and_migrated(monkeypatch):
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

    # Baseline: 10 + 20 visits, 5 + 10 members
    baseline_csv = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01,10,5,2.0
E2,G2,STANDARD,2025-01,20,10,2.0
"""


    migrated_csv = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01,10,5,2.04
E2,G2,STANDARD,2025-01,20,10,1.98
"""

    baseline_key = "dq/baseline/utilization_history_2025-01.csv"
    migrated_key = "dq/migrated/utilization_history_2025-01.csv"

    objects = {
        baseline_key: baseline_csv,
        migrated_key: migrated_csv,
    }

    fake_repo = FakeS3Repo(objects)

    def fake_s3_repo_ctor() -> FakeS3Repo:
        return fake_repo

    # Patch S3ObjectStorageRepository inside dq_lambda
    monkeypatch.setattr(dq_lambda, "S3ObjectStorageRepository", fake_s3_repo_ctor)
    monkeypatch.setattr(dq_lambda, "configure_logging", lambda *args, **kwargs: None)

    event = {
        "table_name": "utilization_history",
        "numeric_columns": ["actual_visits", "eligible_members"],
        "baseline": {"s3_key": baseline_key},
        "migrated": {"s3_key": migrated_key},
        "tolerance_pct": 5.0,
    }

    # Act
    result = dq_lambda.handler(event, context=None)

    # Assert Lambda result
    assert result["outcome"] == "SUCCEEDED"
    assert result["passed"] is True


    assert fake_repo.written, "DQ lambda should write a recon record"
    written = fake_repo.written[0]
    assert written["key"].startswith("recon/")
    assert "utilization_history" in written["key"]

    body = json.loads(written["body"])
    assert body["passed"] is True
    assert body["table_name"] == "utilization_history"
    assert body["baseline_key"] == baseline_key
    assert body["migrated_key"] == migrated_key
    assert "actual_visits" in body["baseline_sums"]
    assert "eligible_members" in body["baseline_sums"]
