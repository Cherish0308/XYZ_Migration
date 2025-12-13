from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List

from app.config import AppConfig
from app.exceptions import AppError
from app.logging_config import configure_logging
from app.repositories import S3ObjectStorageRepository
from app.utils import idempotency, json_utils, s3_path_utils

logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("ingestion_lambda invoked", extra={"env": config.env})

    s3_repo = S3ObjectStorageRepository()
    results: List[Dict[str, Any]] = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        logger.info(
            "Processing ingestion S3 record",
            extra={"bucket": bucket, "key": key},
        )

        if bucket != config.s3_bucket:
            logger.warning(
                "Skipping record for unexpected bucket in ingestion",
                extra={"expected_bucket": config.s3_bucket, "actual_bucket": bucket},
            )
            continue

        try:
            parsed = s3_path_utils.parse_table_and_period_from_key(config.s3_raw_prefix, key)
            table_name = parsed.table_name
            logical_period = parsed.logical_period

            head = s3_repo.head_object(bucket, key)
            payload = {
                "bucket": bucket,
                "key": key,
                "etag": head.get("ETag", ""),
                "content_length": head.get("ContentLength", "0"),
            }
            idem_key = idempotency.compute_idempotency_key(payload)

            recon_key = s3_path_utils.build_recon_key(
                config.s3_recon_prefix,
                job_id=idem_key,
                table_name=table_name,
            )

            record_doc = {
                "job_type": "INGESTION",
                "idempotency_key": idem_key,
                "bucket": bucket,
                "key": key,
                "table_name": table_name,
                "logical_period": logical_period,
                "content_length": head.get("ContentLength", "0"),
                "content_type": head.get("ContentType", ""),
            }

            s3_repo.write_text(config.s3_bucket, recon_key, json_utils.dumps(record_doc))

            logger.info(
                "Ingestion registered for file",
                extra={
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "recon_key": recon_key,
                    "idempotency_key": idem_key,
                },
            )

            results.append(
                {
                    "table_name": table_name,
                    "logical_period": logical_period,
                    "recon_key": recon_key,
                    "outcome": "REGISTERED",
                }
            )

        except AppError as exc:
            logger.error(
                "Application error during ingestion",
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
                "Unexpected exception during ingestion",
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
