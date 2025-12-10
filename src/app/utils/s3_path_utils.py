from __future__ import annotations

from typing import NamedTuple


def build_validated_key(validated_prefix: str, raw_key: str) -> str:
   
    parts = raw_key.split("/", 1)
    if len(parts) == 2:
        # Drop whatever the first segment was (usually "raw") and replace with validated_prefix.
        suffix = parts[1]
    else:
        suffix = raw_key

    return f"{validated_prefix}/{suffix}"


def build_error_key(error_prefix: str, raw_key: str) -> str:
    
    parts = raw_key.split("/", 1)
    if len(parts) == 2:
        suffix = parts[1]
    else:
        suffix = raw_key

    return f"{error_prefix}/{suffix}"


def build_transformed_key(
    transformed_prefix: str,
    table_name: str,
    logical_period: str,
    source_key: str,
) -> str:
   
    filename = source_key.rsplit("/", 1)[-1]
    return f"{transformed_prefix}/{table_name}/forecast_period={logical_period}/{filename}"


def build_recon_key(recon_prefix: str, job_id: str, table_name: str) -> str:
    
    return f"{recon_prefix}/{job_id}/{table_name}.json"


class ParsedS3Path(NamedTuple):
   

    table_name: str
    logical_period: str
    filename: str


def parse_table_and_period_from_key(prefix: str, key: str) -> ParsedS3Path:
    
    # Strip the leading prefix/ if present
    if key.startswith(prefix + "/"):
        suffix = key[len(prefix) + 1 :]
    else:
        suffix = key

    parts = suffix.split("/")
    if len(parts) < 3:
        raise ValueError(f"Unexpected key structure for prefix '{prefix}': {key}")

    table_name = parts[0]
    period_part = parts[1]
    filename = "/".join(parts[2:])

    if not period_part.startswith("forecast_period="):
        raise ValueError(f"Unexpected period segment in key: {key}")

    logical_period = period_part.split("=", 1)[1]
    return ParsedS3Path(table_name=table_name, logical_period=logical_period, filename=filename)
