from __future__ import annotations

from app.repositories.metadata_repository import InMemoryMetadataRepository
from app.services.transformation_service import TransformationService


def _make_service() -> TransformationService:
    metadata = InMemoryMetadataRepository()
    return TransformationService(metadata)


def test_transform_row_utilization_history_types():
    service = _make_service()

    raw = {
        "employer_id": "E1",
        "gym_id": "G1",
        "product_code": "STANDARD",
        "forecast_period": "2025-01-15",  # should normalize to 2025-01
        "actual_visits": "10",
        "eligible_members": "5",
        "utilization_rate": "2.0",
    }

    transformed = service.transform_row("utilization_history", raw)

    assert transformed["employer_id"] == "E1"
    assert transformed["gym_id"] == "G1"
    assert transformed["product_code"] == "STANDARD"
    assert transformed["forecast_period"] == "2025-01"
    assert transformed["actual_visits"] == 10
    assert transformed["eligible_members"] == 5
    assert transformed["utilization_rate"] == 2.0
