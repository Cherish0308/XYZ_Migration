from __future__ import annotations

import csv
import io
import logging
import urllib.parse
from typing import Any, Dict, List

from app.config import AppConfig
from app.logging_config import configure_logging
from app.exceptions import AppError
from app.repositories import InMemoryMetadataRepository, S3ObjectStorageRepository
from app.services import TransformationService
from app.utils import s3_path_utils

logger = logging.getLogger(__name__)


def _build_transformation_service() -> TransformationService:
    metadata_repo = InMemoryMetadataRepository()
    return TransformationService(metadata_repo)


def _extract_table_and_period_from_key(validated_prefix: str, key: str) -> Dict[str, str]:
    """
    Expect keys like:
      validated/<table_name>/forecast_period=YYYY-MM/filename.csv
    """
    if key.startswith(validated_prefix + "/"):
        suffix = key[len(validated_prefix) + 1 :]
    else:
        suffix = key

    parts = suffix.split("/")
    if len(parts) < 3:
        raise ValueError(f"Unexpected key structure for transform: {key}")

    table_name = parts[0]
    period_part = parts[1]

    if not period_part.startswith("forecast_period="):
        raise ValueError(f"Unexpected period segment in key for transform: {key}")

    logical_period = period_part.split("=", 1)[1]
    return {"table_name": table_name, "logical_period": logical_period}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    S3-triggered Lambda:

    - Reads CSV from validated prefix
    - Type-transforms rows according to logical schema
    - Writes normalized CSV to transformed prefix

    This keeps Redshift load downstream simple and consistent.
    """
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("transform_lambda invoked", extra={"env": config.env})

    s3_repo = S3ObjectStorageRepository()
    transform_service = _build_transformation_service()

    results: List[Dict[str, Any]] = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        logger.info(
            "Processing transform S3 record",
            extra={"bucket": bucket, "key": key},
        )

        if bucket != config.s3_bucket:
            logger.warning(
                "Skipping record for unexpected bucket in transform",
                extra={"expected_bucket": config.s3_bucket, "actual_bucket": bucket},
            )
            continue

        try:
            meta = _extract_table_and_period_from_key(config.s3_validated_prefix, key)
            table_name = meta["table_name"]
            logical_period = meta["logical_period"]

            csv_text = s3_repo.read_text(bucket, key)

            reader = csv.DictReader(csv_text.splitlines())
            if reader.fieldnames is None:
                raise ValueError("Validated CSV has no header")

            header = [h.strip() for h in reader.fieldnames]

            transformed_rows: List[Dict[str, Any]] = []

            for row in reader:
                normalized = {k.strip(): v for k, v in row.items() if k is not None}
                transformed = transform_service.transform_row(table_name, normalized)
                # Convert back to string representation for CSV write
                transformed_rows.append({col: "" if v is None else str(v) for col, v in transformed.items()})

            # Write out normalized CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()

            for row in transformed_rows:
                # Only keep columns in the original header to keep file shape stable
                writer.writerow({col: row.get(col, "") for col in header})

            dest_key = s3_path_utils.build_transformed_key(
                config.s3_transformed_prefix,
                table_name,
                logical_period,
                key,
            )

            s3_repo.write_text(config.s3_bucket, dest_key, output.getvalue())

            logger.info(
                "Transform completed for file",
                extra={
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "dest_key": dest_key,
                    "row_count": len(transformed_rows),
                },
            )

            results.append(
                {
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "dest_key": dest_key,
                    "row_count": len(transformed_rows),
                    "outcome": "SUCCEEDED",
                }
            )

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
