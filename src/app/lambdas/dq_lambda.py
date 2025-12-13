from __future__ import annotations

import csv
import logging
from typing import Any, Dict, List

from app.config import AppConfig
from app.exceptions import AppError
from app.logging_config import configure_logging
from app.repositories import InMemoryMetadataRepository, S3ObjectStorageRepository
from app.services import DQService, TransformationService
from app.utils import idempotency, json_utils, s3_path_utils

logger = logging.getLogger(__name__)


def _read_and_transform_csv(
    s3_repo: S3ObjectStorageRepository,
    bucket: str,
    key: str,
    table_name: str,
) -> List[Dict[str, Any]]:
    
    metadata_repo = InMemoryMetadataRepository()
    transform_service = TransformationService(metadata_repo)

    csv_text = s3_repo.read_text(bucket, key)
    reader = csv.DictReader(csv_text.splitlines())

    if reader.fieldnames is None:
        raise ValueError(f"CSV at {key} has no header")

    rows: List[Dict[str, Any]] = []
    for row in reader:
        normalized = {k.strip(): v for k, v in row.items() if k is not None}
        transformed = transform_service.transform_row(table_name, normalized)
        rows.append(transformed)

    return rows


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    
    config = AppConfig.from_env()
    configure_logging(config.app_name, config.log_level)

    logger.info("dq_lambda invoked", extra={"env": config.env})

    table_name: str = event["table_name"]
    numeric_columns: List[str] = event["numeric_columns"]
    baseline_key: str = event["baseline"]["s3_key"]
    migrated_key: str = event["migrated"]["s3_key"]
    tolerance_pct: float = float(event.get("tolerance_pct", 1.0))

    s3_repo = S3ObjectStorageRepository()
    dq_service = DQService()

    try:
        baseline_rows = _read_and_transform_csv(s3_repo, config.s3_bucket, baseline_key, table_name)
        migrated_rows = _read_and_transform_csv(s3_repo, config.s3_bucket, migrated_key, table_name)

        dq_result = dq_service.reconcile_table(
            table_name=table_name,
            baseline_rows=baseline_rows,
            migrated_rows=migrated_rows,
            numeric_columns=numeric_columns,
            tolerance_pct=tolerance_pct,
        )

        # Build a deterministic job id from input
        idem_key = idempotency.compute_idempotency_key(
            {
                "table_name": table_name,
                "baseline_key": baseline_key,
                "migrated_key": migrated_key,
                "numeric_columns": numeric_columns,
                "tolerance_pct": tolerance_pct,
            }
        )

        recon_key = s3_path_utils.build_recon_key(
            config.s3_recon_prefix,
            job_id=f"dq-{idem_key}",
            table_name=table_name,
        )

        summary = {
            "table_name": dq_result.table_name,
            "baseline_row_count": dq_result.baseline_row_count,
            "migrated_row_count": dq_result.migrated_row_count,
            "baseline_sums": dq_result.baseline_sums,
            "migrated_sums": dq_result.migrated_sums,
            "differences": dq_result.differences,
            "differences_pct": dq_result.differences_pct,
            "passed": dq_result.passed,
            "failed_metrics": dq_result.failed_metrics,
            "tolerance_pct": tolerance_pct,
            "baseline_key": baseline_key,
            "migrated_key": migrated_key,
        }

        s3_repo.write_text(config.s3_bucket, recon_key, json_utils.dumps(summary))

        logger.info(
            "DQ reconciliation completed",
            extra={
                "table_name": table_name,
                "recon_key": recon_key,
                "passed": dq_result.passed,
                "failed_metrics": dq_result.failed_metrics,
            },
        )

        return {
            "outcome": "SUCCEEDED",
            "recon_key": recon_key,
            "passed": dq_result.passed,
            "failed_metrics": dq_result.failed_metrics,
        }

    except AppError as exc:
        logger.error("Application error during DQ", extra={"table_name": table_name})
        return {
            "outcome": "ERROR",
            "error": str(exc),
        }
    except Exception as exc:  
        logger.exception("Unexpected exception during DQ", extra={"table_name": table_name})
        return {
            "outcome": "ERROR",
            "error": str(exc),
        }
