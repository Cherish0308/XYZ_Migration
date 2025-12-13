from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.config import AppConfig
from app.exceptions import AppError
from app.lambdas.transform_lambda_helpers import (
    CSVTransformProcessor,
    S3EventParser,
    S3TransformOrchestrator,
)
from app.logging_config import configure_logging
from app.repositories import InMemoryMetadataRepository, S3ObjectStorageRepository
from app.services import TransformationService
from app.utils import s3_path_utils

logger = logging.getLogger(__name__)


def _build_transformation_service() -> TransformationService:
    metadata_repo = InMemoryMetadataRepository()
    return TransformationService(metadata_repo)



def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for transforming CSV files from S3."""
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("transform_lambda invoked", extra={"env": config.env})

    # Initialize dependencies
    s3_repo = S3ObjectStorageRepository()
    transform_service = _build_transformation_service()
    csv_processor = CSVTransformProcessor(transform_service)
    orchestrator = S3TransformOrchestrator(s3_repo, csv_processor)
    event_parser = S3EventParser()

    results: List[Dict[str, Any]] = []

    # Parse S3 events
    try:
        records = event_parser.parse_records(event)
    except Exception as exc:
        logger.exception("Failed to parse S3 event records")
        return {"results": [{"error": str(exc), "outcome": "ERROR"}]}

    for record in records:
        bucket = record.bucket
        key = record.key

        logger.info(
            "Processing transform S3 record",
            extra={"bucket": bucket, "key": key},
        )

        # Validate bucket
        if bucket != config.s3_bucket:
            logger.warning(
                "Skipping record for unexpected bucket in transform",
                extra={"expected_bucket": config.s3_bucket, "actual_bucket": bucket},
            )
            continue

        try:
            # Parse S3 path to extract table name and period
            parsed = s3_path_utils.parse_table_and_period_from_key(
                config.s3_validated_prefix,
                key,
            )
            table_name = parsed.table_name
            logical_period = parsed.logical_period

            # Transform and upload
            result = orchestrator.transform_and_upload(
                bucket=bucket,
                source_key=key,
                table_name=table_name,
                logical_period=logical_period,
                transformed_prefix=config.s3_transformed_prefix,
            )
            results.append(result)

        except AppError as exc:
            logger.error(
                "Application error during transform",
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
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Unexpected exception during transform",
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
 
