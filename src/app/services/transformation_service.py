from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.repositories import MetadataRepository
from app.utils.time_utils import parse_date, parse_timestamp, normalize_period


@dataclass
class TransformedBatch:
    table_name: str
    records: List[Dict[str, Any]]


class TransformationService:
    

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        self._metadata_repo = metadata_repo

    def transform_row(self, table_name: str, raw_row: Dict[str, str]) -> Dict[str, Any]:
        
        schema = self._metadata_repo.get_table_schema(table_name)
        transformed: Dict[str, Any] = {}

        for col, logical_type in schema.items():
            raw_value = raw_row.get(col)

            if raw_value is None or raw_value == "":
                transformed[col] = None
                continue

            if logical_type == "STRING":
                transformed[col] = str(raw_value)
            elif logical_type == "INT":
                transformed[col] = int(raw_value)
            elif logical_type == "DECIMAL":
                transformed[col] = float(raw_value)
            elif logical_type == "DATE":
                transformed[col] = parse_date(str(raw_value))
            elif logical_type == "TIMESTAMP":
                transformed[col] = parse_timestamp(str(raw_value))
            elif logical_type == "PERIOD":
                transformed[col] = normalize_period(str(raw_value))
            else:
                # Fallback: leave as string
                transformed[col] = raw_value

        return transformed

    def transform_rows(self, table_name: str, rows: List[Dict[str, str]]) -> TransformedBatch:
        
        return TransformedBatch(
            table_name=table_name,
            records=[self.transform_row(table_name, row) for row in rows],
        )
