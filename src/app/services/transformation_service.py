from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from app.repositories import MetadataRepository
from app.utils.time_utils import parse_date, parse_timestamp, normalize_period


@dataclass
class TransformedBatch:
    table_name: str
    records: List[Dict[str, Any]]


# Type transformer dispatch table - replaces conditional logic with data structure
TYPE_TRANSFORMERS: Dict[str, Callable[[str], Any]] = {
    "STRING": str,
    "INT": int,
    "DECIMAL": float,
    "DATE": lambda v: parse_date(str(v)),
    "TIMESTAMP": lambda v: parse_timestamp(str(v)),
    "PERIOD": lambda v: normalize_period(str(v)),
}


class TransformationService:
    """Service for transforming raw CSV data into typed records.
    
    Uses a dispatch table pattern to eliminate conditional logic and
    enable easy extension of new data types.
    """

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        self._metadata_repo = metadata_repo

    def transform_row(self, table_name: str, raw_row: Dict[str, str]) -> Dict[str, Any]:
        """Transform a single raw CSV row into typed values.
        
        Args:
            table_name: Name of the table for schema lookup.
            raw_row: Dictionary of column name to raw string value.
        
        Returns:
            Dictionary with typed values according to schema.
        """
        schema = self._metadata_repo.get_table_schema(table_name)
        transformed: Dict[str, Any] = {}

        for col, logical_type in schema.items():
            raw_value = raw_row.get(col)

            if raw_value is None or raw_value == "":
                transformed[col] = None
                continue

            # Use dispatch table instead of if/elif chain
            transformer = TYPE_TRANSFORMERS.get(logical_type, str)
            transformed[col] = transformer(raw_value)

        return transformed

    def transform_rows(self, table_name: str, rows: List[Dict[str, str]]) -> TransformedBatch:
        """Transform multiple rows for batch processing.
        
        Args:
            table_name: Name of the table for schema lookup.
            rows: List of raw row dictionaries.
        
        Returns:
            TransformedBatch containing table name and typed records.
        """
        return TransformedBatch(
            table_name=table_name,
            records=[self.transform_row(table_name, row) for row in rows],
        )
