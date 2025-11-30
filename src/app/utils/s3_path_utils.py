from __future__ import annotations

from pathlib import PurePosixPath


def build_raw_prefix(base_prefix: str, table_name: str, logical_period: str) -> str:
    """
    raw/<table_name>/forecast_period=YYYY-MM/
    """
    return f"{base_prefix}/{table_name}/forecast_period={logical_period}/"


def build_error_key(base_prefix: str, table_name: str, logical_period: str, original_key: str) -> str:
    """
    error/<table_name>/forecast_period=YYYY-MM/validation_failed/<filename>
    """
    filename = PurePosixPath(original_key).name
    return f"{base_prefix}/{table_name}/forecast_period={logical_period}/validation_failed/{filename}"


def build_transformed_key(base_prefix: str, table_name: str, logical_period: str, original_key: str) -> str:
    """
    transformed/<table_name>/forecast_period=YYYY-MM/<filename>
    """
    filename = PurePosixPath(original_key).name
    return f"{base_prefix}/{table_name}/forecast_period={logical_period}/{filename}"


def build_recon_key(base_prefix: str, job_id: str, table_name: str) -> str:
    """
    recon/<job_id>/<table_name>.json
    """
    return f"{base_prefix}/{job_id}/{table_name}.json"


def build_job_metadata_key(base_prefix: str, job_id: str) -> str:
    """
    recon/<job_id>/job_metadata.json
    """
    return f"{base_prefix}/{job_id}/job_metadata.json"
