from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Any, Dict, List

from app.config import AppConfig
from app.exceptions import AppError
from app.logging_config import configure_logging
from app.repositories import (
    InMemoryMetadataRepository,
    S3ObjectStorageRepository,
)
from app.services import ValidationService
from app.validators import SchemaValidator, BusinessValidator
from app.utils import s3_path_utils, json_utils

logger = logging.getLogger(__name__)


def _build_validation_service() -> ValidationService:
    metadata_repo = InMemoryMetadataRepository()
    schema_validator = SchemaValidator(metadata_repo)
    business_validator = BusinessValidator()
    return ValidationService(schema_validator, business_validator)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
   
    # Bootstrap config + logging
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("validation_lambda invoked", extra={"env": config.env})

    s3_repo = S3ObjectStorageRepository()
    validation_service = _build_validation_service()

    results: List[Dict[str, Any]] = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        logger.info(
            "Processing S3 event record",
            extra={"bucket": bucket, "key": key},
        )

        # Only handle events for our configured bucket
        if bucket != config.s3_bucket:
            logger.warning(
                "Skipping record for unexpected bucket",
                extra={"expected_bucket": config.s3_bucket, "actual_bucket": bucket},
            )
            continue

        try:
            parsed = s3_path_utils.parse_table_and_period_from_key(config.s3_raw_prefix, key)
            table_name = parsed.table_name
            logical_period = parsed.logical_period

            csv_text = s3_repo.read_text(bucket, key)
            report = validation_service.validate_csv(table_name, csv_text)

            if report.invalid_rows > 0:
                dest_key = s3_path_utils.build_error_key(
                    config.s3_error_prefix,
                    table_name,
                    logical_period,
                    key,
                )
                outcome = "FAILED"
            else:
                dest_key = s3_path_utils.build_transformed_key(
                    config.s3_validated_prefix,
                    table_name,
                    logical_period,
                    key,
                )
                outcome = "SUCCEEDED"

            # Copy file to validated/error location
            s3_repo.copy_object(
                src_bucket=bucket,
                src_key=key,
                dest_bucket=config.s3_bucket,
                dest_key=dest_key,
            )

            # Write a small validation summary into recon prefix
            recon_key = s3_path_utils.build_recon_key(
                config.s3_recon_prefix,
                job_id=f"validation-{table_name}-{logical_period}",
                table_name=table_name,
            )
            summary = {
                "table_name": table_name,
                "logical_period": logical_period,
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows,
                "invalid_rows": report.invalid_rows,
                "outcome": outcome,
            }
            s3_repo.write_text(config.s3_bucket, recon_key, json_utils.dumps(summary))

            logger.info(
                "Validation completed for file",
                extra={
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "outcome": outcome,
                    "total_rows": report.total_rows,
                    "invalid_rows": report.invalid_rows,
                    "dest_key": dest_key,
                    "recon_key": recon_key,
                },
            )

            results.append(summary)

        except AppError as exc:
            logger.error(
                "Application error during validation",
                extra={"bucket": bucket, "key": key},
            )
            # We don't re-raise to avoid retry storms; this can be tuned.
            results.append(
                {
                    "bucket": bucket,
                    "key": key,
                    "error": str(exc),
                    "outcome": "ERROR",
                }
            )
        except Exception as exc:  
            logger.exception(
                "Unexpected exception during validation",
                extra={"bucket": bucket, "key": key},
            )
            results.append(
                {
                    "bucket": bucket,
                    "key": key,
                    "error": str(exc),
                    "outcome": "ERROR",
                }
            )

    return {"results": results}
