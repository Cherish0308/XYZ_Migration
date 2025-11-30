from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TableDQResult:
    """
    Simple reconciliation summary between baseline and migrated data.

    This is intentionally generic and in-memory. Another layer (not here)
    can be responsible for fetching data from Snowflake exports / Redshift
    and feeding it into this service.
    """

    table_name: str
    baseline_row_count: int
    migrated_row_count: int
    baseline_sums: Dict[str, float]
    migrated_sums: Dict[str, float]
    differences: Dict[str, float]
    differences_pct: Dict[str, float]
    passed: bool
    failed_metrics: List[str]


class DQService:
    """
    Data quality / reconciliation calculations.

    Input:
      - baseline_rows: list of dicts (Snowflake export, already typed)
      - migrated_rows: list of dicts (Redshift query results, already typed)
      - numeric_columns: which columns to compare by sum
      - tolerance_pct: allowed percentage diff for sums and row counts

    Output:
      - TableDQResult with pass/fail and detailed metrics.
    """

    def reconcile_table(
        self,
        table_name: str,
        baseline_rows: List[Dict[str, Any]],
        migrated_rows: List[Dict[str, Any]],
        numeric_columns: List[str],
        tolerance_pct: float = 1.0,
    ) -> TableDQResult:
        baseline_row_count = len(baseline_rows)
        migrated_row_count = len(migrated_rows)

        baseline_sums = self._compute_sums(baseline_rows, numeric_columns)
        migrated_sums = self._compute_sums(migrated_rows, numeric_columns)

        differences: Dict[str, float] = {}
        differences_pct: Dict[str, float] = {}
        failed_metrics: List[str] = []

        # Row count metric
        row_diff = float(migrated_row_count - baseline_row_count)
        row_diff_pct = self._pct_diff(baseline_row_count, migrated_row_count)
        if abs(row_diff_pct) > tolerance_pct:
            failed_metrics.append("row_count")

        differences["row_count"] = row_diff
        differences_pct["row_count"] = row_diff_pct

        # Numeric column metrics
        for col in numeric_columns:
            base_val = baseline_sums.get(col, 0.0)
            mig_val = migrated_sums.get(col, 0.0)
            diff = mig_val - base_val
            diff_pct = self._pct_diff(base_val, mig_val)

            differences[col] = diff
            differences_pct[col] = diff_pct

            if abs(diff_pct) > tolerance_pct:
                failed_metrics.append(col)

        passed = not failed_metrics

        return TableDQResult(
            table_name=table_name,
            baseline_row_count=baseline_row_count,
            migrated_row_count=migrated_row_count,
            baseline_sums=baseline_sums,
            migrated_sums=migrated_sums,
            differences=differences,
            differences_pct=differences_pct,
            passed=passed,
            failed_metrics=failed_metrics,
        )

    @staticmethod
    def _compute_sums(rows: List[Dict[str, Any]], numeric_columns: List[str]) -> Dict[str, float]:
        sums: Dict[str, float] = {col: 0.0 for col in numeric_columns}
        for row in rows:
            for col in numeric_columns:
                value = row.get(col)
                if value is None:
                    continue
                try:
                    sums[col] += float(value)
                except (TypeError, ValueError):
                    # Ignore non-numeric values; caller should clean upstream
                    continue
        return sums

    @staticmethod
    def _pct_diff(baseline: float, migrated: float) -> float:
        if baseline == 0 and migrated == 0:
            return 0.0
        if baseline == 0:
            # If baseline is zero but migrated isn't, treat as 100% diff.
            return 100.0
        return (migrated - baseline) * 100.0 / baseline
