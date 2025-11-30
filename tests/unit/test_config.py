from __future__ import annotations

from app.config import AppConfig


def test_app_config_from_env(monkeypatch):
    # Arrange
    monkeypatch.setenv("S3_BUCKET", "xyz-bucket")
    monkeypatch.setenv("REDSHIFT_HOST", "redshift.xyz.com")
    monkeypatch.setenv("REDSHIFT_DATABASE", "analytics")
    monkeypatch.setenv("REDSHIFT_USER", "user")
    monkeypatch.setenv("REDSHIFT_PASSWORD", "pw")
    monkeypatch.setenv("REDSHIFT_IAM_ROLE_ARN", "arn:aws:iam::123456789012:role/RedshiftCopyRole")

    # Act
    cfg = AppConfig.from_env()

    # Assert
    assert cfg.s3_bucket == "xyz-bucket"
    assert cfg.redshift_host == "redshift.xyz.com"
    assert cfg.redshift_database == "analytics"
    assert cfg.redshift_user == "user"
    assert cfg.redshift_password == "pw"
    assert cfg.redshift_iam_role_arn.startswith("arn:")
