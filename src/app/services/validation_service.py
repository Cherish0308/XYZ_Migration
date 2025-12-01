from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Any, Dict, List

from app.exceptions import BusinessRuleViolation
from app.validators import SchemaValidator, BusinessValidator


@dataclass
class RowValidationError:
    row_number: int
    message: str
    raw_row: Dict[str, Any]


@dataclass
class FileValidationReport:
    table_name: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: List[RowValidationError]


class ValidationService:
    

    def __init__(self, schema_validator: SchemaValidator, business_validator: BusinessValidator) -> None:
        self._schema_validator = schema_validator
        self._business_validator = business_validator

    def validate_csv(self, table_name: str, csv_text: str) -> FileValidationReport:
        
        # csv.DictReader expects an iterable of lines
        reader = csv.DictReader(csv_text.splitlines())

        # Header validation
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        header = [h.strip() for h in reader.fieldnames]
        self._schema_validator.validate_header(table_name, header)

        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        errors: List[RowValidationError] = []

        for idx, row in enumerate(reader, start=2):  # start=2 to account for header line
            total_rows += 1

            # Normalize keys (strip spaces) and filter to known columns
            normalized = {k.strip(): v for k, v in row.items() if k is not None}
            filtered = self._schema_validator.filter_known_columns(table_name, normalized)

            try:
                self._business_validator.validate(table_name, filtered)
                valid_rows += 1
            except BusinessRuleViolation as exc:
                invalid_rows += 1
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        message=str(exc),
                        raw_row=filtered,
                    )
                )

        return FileValidationReport(
            table_name=table_name,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            errors=errors,
        )
