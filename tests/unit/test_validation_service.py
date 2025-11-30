from __future__ import annotations

from app.repositories.metadata_repository import InMemoryMetadataRepository
from app.validators import SchemaValidator, BusinessValidator
from app.services.validation_service import ValidationService


def _make_service() -> ValidationService:
    metadata = InMemoryMetadataRepository()
    schema_validator = SchemaValidator(metadata)
    business_validator = BusinessValidator()
    return ValidationService(schema_validator, business_validator)


def test_validation_service_valid_utilization_rows():
    service = _make_service()

    csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01,10,5,2.0
E2,G2,PLUS,2025-01,0,10,0.0
"""

    report = service.validate_csv("utilization_history", csv_text)

    assert report.table_name == "utilization_history"
    assert report.total_rows == 2
    assert report.valid_rows == 2
    assert report.invalid_rows == 0
    assert report.errors == []


def test_validation_service_catches_negative_visits():
    service = _make_service()

    csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01,-1,5,2.0
"""

    report = service.validate_csv("utilization_history", csv_text)

    assert report.total_rows == 1
    assert report.valid_rows == 0
    assert report.invalid_rows == 1
    assert len(report.errors) == 1
    assert "cannot be negative" in report.errors[0].message
