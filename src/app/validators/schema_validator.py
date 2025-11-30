from __future__ import annotations

from typing import Dict, List

from app.exceptions import SchemaMismatchError
from app.repositories import MetadataRepository


class SchemaValidator:
    """
    Performs structural/schema validation only:

    - Do the columns in the file match what we expect for this table?
    - Are all required columns present?

    It does NOT convert types – that is handled by the transformation layer.
    """

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        self._metadata_repo = metadata_repo

    def validate_header(self, table_name: str, header: List[str]) -> None:
        """
        Validate that the file header matches the known schema.

        We allow extra columns (they will be ignored later), but all known
        columns must be present.
        """
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
            # No exception – we just let the caller log this if they want.
            # Keeping this function pure & side-effect-free.
            pass

    def filter_known_columns(self, table_name: str, row: Dict[str, str]) -> Dict[str, str]:
        """
        Strip any unknown columns so downstream code only sees defined schema.

        This keeps the system resilient to Snowflake adding new columns that
        we haven't modeled yet.
        """
        schema = self._metadata_repo.get_table_schema(table_name)
        return {col: value for col, value in row.items() if col in schema}
