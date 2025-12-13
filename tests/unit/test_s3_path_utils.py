from __future__ import annotations

import pytest

from app.utils.s3_path_utils import (
    ParsedS3Path,
    build_error_key,
    build_recon_key,
    build_transformed_key,
    build_validated_key,
    parse_table_and_period_from_key,
)


class TestBuildValidatedKey:
    
    
    def test_build_validated_key_from_raw(self):
        result = build_validated_key("validated", "raw/utilization_history/forecast_period=2025-01/file.csv")
        assert result == "validated/utilization_history/forecast_period=2025-01/file.csv"
    
    def test_build_validated_key_without_prefix(self):
        result = build_validated_key("validated", "file.csv")
        assert result == "validated/file.csv"
    
    def test_build_validated_key_preserves_structure(self):
        result = build_validated_key("validated", "raw/table/partition=value/nested/file.csv")
        assert result == "validated/table/partition=value/nested/file.csv"


class TestBuildErrorKey:
    
    def test_build_error_key_from_raw(self):
        result = build_error_key("error", "raw/utilization_history/forecast_period=2025-01/file.csv")
        assert result == "error/utilization_history/forecast_period=2025-01/file.csv"
    
    def test_build_error_key_without_prefix(self):
        result = build_error_key("error", "file.csv")
        assert result == "error/file.csv"


class TestBuildTransformedKey:
    
    def test_build_transformed_key_standard(self):
        result = build_transformed_key(
            "transformed",
            "utilization_history",
            "2025-01",
            "validated/utilization_history/forecast_period=2025-01/file.csv"
        )
        assert result == "transformed/utilization_history/forecast_period=2025-01/file.csv"
    
    def test_build_transformed_key_extracts_filename(self):
        result = build_transformed_key(
            "transformed",
            "pricing_rules",
            "2025-02",
            "validated/pricing_rules/forecast_period=2025-02/data_20250201.csv"
        )
        assert result == "transformed/pricing_rules/forecast_period=2025-02/data_20250201.csv"
        assert "data_20250201.csv" in result
    
    def test_build_transformed_key_different_table(self):
        result = build_transformed_key(
            "transformed",
            "forecasts",
            "2025-12",
            "any/path/to/source.csv"
        )
        assert result == "transformed/forecasts/forecast_period=2025-12/source.csv"


class TestBuildReconKey:
    
    
    def test_build_recon_key_standard(self):
        result = build_recon_key("recon", "job123", "utilization_history")
        assert result == "recon/job123/utilization_history.json"
    
    def test_build_recon_key_different_table(self):
        result = build_recon_key("recon", "abc-def-ghi", "pricing_rules")
        assert result == "recon/abc-def-ghi/pricing_rules.json"
    
    def test_build_recon_key_with_uuid_job_id(self):
        job_id = "550e8400-e29b-41d4-a716-446655440000"
        result = build_recon_key("recon", job_id, "forecasts")
        assert result == f"recon/{job_id}/forecasts.json"


class TestParseTableAndPeriodFromKey:

    
    def test_parse_standard_key(self):
        result = parse_table_and_period_from_key(
            "validated",
            "validated/utilization_history/forecast_period=2025-01/file.csv"
        )
        assert isinstance(result, ParsedS3Path)
        assert result.table_name == "utilization_history"
        assert result.logical_period == "2025-01"
        assert result.filename == "file.csv"
    
    def test_parse_key_without_prefix(self):
        result = parse_table_and_period_from_key(
            "validated",
            "utilization_history/forecast_period=2025-01/file.csv"
        )
        assert result.table_name == "utilization_history"
        assert result.logical_period == "2025-01"
    
    def test_parse_key_with_nested_path(self):
        result = parse_table_and_period_from_key(
            "transformed",
            "transformed/pricing_rules/forecast_period=2025-12/nested/path/file.csv"
        )
        assert result.table_name == "pricing_rules"
        assert result.logical_period == "2025-12"
        assert result.filename == "nested/path/file.csv"
    
    def test_parse_key_different_table(self):
        result = parse_table_and_period_from_key(
            "raw",
            "raw/forecasts/forecast_period=2024-06/data.csv"
        )
        assert result.table_name == "forecasts"
        assert result.logical_period == "2024-06"
    
    def test_parse_key_missing_parts(self):
        with pytest.raises(ValueError, match="Unexpected key structure"):
            parse_table_and_period_from_key("validated", "validated/table_only")
    
    def test_parse_key_invalid_period_format(self):
        with pytest.raises(ValueError, match="Unexpected period segment"):
            parse_table_and_period_from_key(
                "validated",
                "validated/utilization_history/invalid_period_format/file.csv"
            )
    
    def test_parse_key_too_short(self):
        with pytest.raises(ValueError, match="Unexpected key structure"):
            parse_table_and_period_from_key("validated", "validated/utilization_history")
    
    def test_parse_key_edge_case_january(self):
        result = parse_table_and_period_from_key(
            "validated",
            "validated/utilization_history/forecast_period=2025-01/file.csv"
        )
        assert result.logical_period == "2025-01"
    
    def test_parse_key_edge_case_december(self):
        result = parse_table_and_period_from_key(
            "validated",
            "validated/utilization_history/forecast_period=2025-12/file.csv"
        )
        assert result.logical_period == "2025-12"


class TestParsedS3Path:
    
    
    def test_parsed_s3_path_attributes(self):
        parsed = ParsedS3Path(
            table_name="utilization_history",
            logical_period="2025-01",
            filename="file.csv"
        )
        assert parsed.table_name == "utilization_history"
        assert parsed.logical_period == "2025-01"
        assert parsed.filename == "file.csv"
    
    def test_parsed_s3_path_immutable(self):
        parsed = ParsedS3Path("table", "2025-01", "file.csv")
        with pytest.raises(AttributeError):
            parsed.table_name = "new_table"
    
    def test_parsed_s3_path_tuple_behavior(self):
        parsed = ParsedS3Path("table", "2025-01", "file.csv")
        table, period, filename = parsed
        assert table == "table"
        assert period == "2025-01"
        assert filename == "file.csv"
