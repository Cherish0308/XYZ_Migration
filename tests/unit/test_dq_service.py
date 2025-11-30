from __future__ import annotations

from app.services.dq_service import DQService


def test_dq_service_passes_within_tolerance():
    dq = DQService()

    baseline_rows = [
        {"actual_visits": 10, "eligible_members": 5},
        {"actual_visits": 20, "eligible_members": 10},
    ]
    migrated_rows = [
        {"actual_visits": 10.1, "eligible_members": 5.0},
        {"actual_visits": 19.9, "eligible_members": 10.0},
    ]

    result = dq.reconcile_table(
        table_name="utilization_history",
        baseline_rows=baseline_rows,
        migrated_rows=migrated_rows,
        numeric_columns=["actual_visits", "eligible_members"],
        tolerance_pct=2.0,
    )

    assert result.passed is True
    assert result.failed_metrics == []


def test_dq_service_flags_large_differences():
    dq = DQService()

    baseline_rows = [
        {"actual_visits": 10},
        {"actual_visits": 20},
    ]
    migrated_rows = [
        {"actual_visits": 50},
    ]

    result = dq.reconcile_table(
        table_name="utilization_history",
        baseline_rows=baseline_rows,
        migrated_rows=migrated_rows,
        numeric_columns=["actual_visits"],
        tolerance_pct=10.0,
    )

    assert result.passed is False
    assert "row_count" in result.failed_metrics or "actual_visits" in result.failed_metrics
