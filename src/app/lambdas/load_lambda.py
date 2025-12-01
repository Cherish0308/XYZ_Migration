from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List

from app.config import AppConfig
from app.exceptions import AppError
from app.logging_config import configure_logging
from app.repositories import InMemoryMetadataRepository, RedshiftWarehouseRepository
from app.services import LoadService
from app.utils import s3_path_utils  
logger = logging.getLogger(__name__)


def _extract_table_and_period_from_key(transformed_prefix: str, key: str) -> Dict[str, str]:
    
    if key.startswith(transformed_prefix + "/"):
        suffix = key[len(transformed_prefix) + 1 :]
    else:
        suffix = key

    parts = suffix.split("/")
    if len(parts) < 3:
        raise ValueError(f"Unexpected key structure for load: {key}")

    table_name = parts[0]
    period_part = parts[1]

    if not period_part.startswith("forecast_period="):
        raise ValueError(f"Unexpected period segment in key for load: {key}")

    logical_period = period_part.split("=", 1)[1]
    return {"table_name": table_name, "logical_period": logical_period}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("load_lambda invoked", extra={"env": config.env})

    metadata_repo = InMemoryMetadataRepository()
    warehouse_repo = RedshiftWarehouseRepository(config)
    load_service = LoadService(warehouse_repo, metadata_repo, config)

    results: List[Dict[str, Any]] = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        logger.info(
            "Processing load S3 record",
            extra={"bucket": bucket, "key": key},
        )

        if bucket != config.s3_bucket:
            logger.warning(
                "Skipping record for unexpected bucket in load",
                extra={"expected_bucket": config.s3_bucket, "actual_bucket": bucket},
            )
            continue

        try:
            meta = _extract_table_and_period_from_key(config.s3_transformed_prefix, key)
            table_name = meta["table_name"]
            logical_period = meta["logical_period"]

            load_result = load_service.load_transformed_file(
                table_name=table_name,
                logical_period=logical_period,
                s3_key=key,
            )

            logger.info(
                "Load completed for file",
                extra={
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "redshift_table": load_result.redshift_table,
                    "s3_uri": load_result.s3_uri,
                },
            )

            results.append(
                {
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "redshift_table": load_result.redshift_table,
                    "s3_uri": load_result.s3_uri,
                    "outcome": "LOADED",
                }
            )

        except AppError as exc:
            logger.error(
                "Application error during load",
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
        except Exception as exc:  
            logger.exception(
                "Unexpected exception during load",
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
