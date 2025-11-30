from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """
    Central application configuration.

    All AWS / Redshift / S3 settings come from here so that the rest of the
    codebase never calls os.getenv() directly. This makes testing and
    environment switching much easier.
    """

    env: str
    app_name: str
    log_level: str

    s3_bucket: str
    s3_raw_prefix: str
    s3_validated_prefix: str
    s3_transformed_prefix: str
    s3_error_prefix: str
    s3_recon_prefix: str

    redshift_host: str
    redshift_port: int
    redshift_database: str
    redshift_user: str
    redshift_password: str
    redshift_iam_role_arn: str

    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Build AppConfig from environment variables.

        This should be called only at process boundaries (Lambda handlers,
        CLI entrypoints). Other code receives an AppConfig instance via DI.
        """
        env = os.getenv("APP_ENV", "dev")
        app_name = os.getenv("APP_NAME", "xyz-pricing-migration")
        log_level = os.getenv("LOG_LEVEL", "INFO")

        bucket = _require("S3_BUCKET")

        return cls(
            env=env,
            app_name=app_name,
            log_level=log_level,
            s3_bucket=bucket,
            s3_raw_prefix=os.getenv("S3_RAW_PREFIX", "raw"),
            s3_validated_prefix=os.getenv("S3_VALIDATED_PREFIX", "validated"),
            s3_transformed_prefix=os.getenv("S3_TRANSFORMED_PREFIX", "transformed"),
            s3_error_prefix=os.getenv("S3_ERROR_PREFIX", "error"),
            s3_recon_prefix=os.getenv("S3_RECON_PREFIX", "recon"),
            redshift_host=_require("REDSHIFT_HOST"),
            redshift_port=int(os.getenv("REDSHIFT_PORT", "5439")),
            redshift_database=_require("REDSHIFT_DATABASE"),
            redshift_user=_require("REDSHIFT_USER"),
            redshift_password=_require("REDSHIFT_PASSWORD"),
            redshift_iam_role_arn=_require("REDSHIFT_IAM_ROLE_ARN"),
            dry_run=_get_bool("DRY_RUN", False),
        )


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y"}
