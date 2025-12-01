from __future__ import annotations

from typing import Dict, List

from app.exceptions import SchemaMismatchError
from app.repositories import MetadataRepository


class SchemaValidator:
    

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        self._metadata_repo = metadata_repo

    def validate_header(self, table_name: str, header: List[str]) -> None:
       
        if not header:
            raise SchemaMismatchError(f"Empty header for table '{table_name}'")

        schema: Dict[str, str] = self._metadata_repo.get_table_schema(table_name)
        required = set(self._metadata_repo.get_required_columns(table_name))

        header_set = set(header)
        missing = required - header_set

        if missing:
            raise SchemaMismatchError(
                f"Missing required columns for table '{table_name}': {sorted(missing)}"
            )

        # We don't fail on extras, but they can be useful for debugging.
        extras = header_set - set(schema.keys())
        if extras:
            
            pass

    def filter_known_columns(self, table_name: str, row: Dict[str, str]) -> Dict[str, str]:
        
        schema = self._metadata_repo.get_table_schema(table_name)
        return {col: value for col, value in row.items() if col in schema}
