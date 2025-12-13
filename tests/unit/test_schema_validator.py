from __future__ import annotations

import pytest

from app.exceptions import SchemaMismatchError
from app.repositories.metadata_repository import InMemoryMetadataRepository
from app.validators.schema_validator import SchemaValidator


@pytest.fixture
def metadata_repo():
    """Fixture for metadata repository."""
    return InMemoryMetadataRepository()


@pytest.fixture
def schema_validator(metadata_repo):
    """Fixture for schema validator with injected metadata repo."""
    return SchemaValidator(metadata_repo)


class TestSchemaValidator:

    
    def _make_validator(self) -> SchemaValidator:
        metadata_repo = InMemoryMetadataRepository()
        return SchemaValidator(metadata_repo)
    
    def test_validate_header_valid_utilization_history(self):
        validator = self._make_validator()
        header = ["employer_id", "gym_id", "product_code", "forecast_period", "actual_visits", "eligible_members", "utilization_rate"]
        validator.validate_header("utilization_history", header)
    
    def test_validate_header_valid_pricing_rules(self):
        validator = self._make_validator()
        header = [
            "rule_id", "product_code", "utilization_band_min", "utilization_band_max",
            "price_per_visit", "price_pmpm", "effective_start_date", "effective_end_date"
        ]
        validator.validate_header("pricing_rules", header)
    
    def test_validate_header_missing_required_column(self):
        validator = self._make_validator()
        header = ["employer_id", "gym_id", "product_code", "forecast_period"]
        
        with pytest.raises(SchemaMismatchError, match="Missing required columns"):
            validator.validate_header("utilization_history", header)
    
    def test_validate_header_empty_header(self):
        validator = self._make_validator()
        
        with pytest.raises(SchemaMismatchError, match="Empty header"):
            validator.validate_header("utilization_history", [])
    
    def test_validate_header_with_extra_columns(self):
        validator = self._make_validator()
        header = [
            "employer_id", "gym_id", "product_code", "forecast_period",
            "actual_visits", "eligible_members", "utilization_rate",
            "extra_column1", "extra_column2"
        ]
        
        validator.validate_header("utilization_history", header)
    
    def test_validate_header_case_sensitive(self):
        validator = self._make_validator()
        header = ["EMPLOYER_ID", "gym_id", "product_code", "forecast_period", "actual_visits"]
        
        with pytest.raises(SchemaMismatchError):
            validator.validate_header("utilization_history", header)
    
    def test_filter_known_columns_keeps_valid(self):
        validator = self._make_validator()
        row = {
            "employer_id": "E1",
            "gym_id": "G1",
            "product_code": "STANDARD",
            "forecast_period": "2025-01",
            "actual_visits": "10",
            "eligible_members": "5",
            "utilization_rate": "2.0"
        }
        
        result = validator.filter_known_columns("utilization_history", row)
        
        assert result == row
        assert len(result) == 7
    
    def test_filter_known_columns_removes_unknown(self):
        validator = self._make_validator()
        row = {
            "employer_id": "E1",
            "gym_id": "G1",
            "unknown_column": "should_be_removed",
            "another_unknown": "also_removed"
        }
        
        result = validator.filter_known_columns("utilization_history", row)
        
        assert "employer_id" in result
        assert "gym_id" in result
        assert "unknown_column" not in result
        assert "another_unknown" not in result
    
    def test_filter_known_columns_empty_row(self):
        validator = self._make_validator()
        result = validator.filter_known_columns("utilization_history", {})
        assert result == {}
    
    def test_filter_known_columns_only_unknown(self):
        validator = self._make_validator()
        row = {"unknown1": "value1", "unknown2": "value2"}
        result = validator.filter_known_columns("utilization_history", row)
        assert result == {}
    
    def test_validate_header_forecasts_table(self):
        validator = self._make_validator()
        header = ["run_id", "employer_id", "gym_id", "product_code", "forecast_period", "forecast_visits"]
        # Should not raise
        validator.validate_header("forecasts", header)
    
    def test_validate_header_forecast_runs_table(self):
        validator = self._make_validator()
        header = ["run_id", "forecast_period", "created_at", "model_version", "status"]
        validator.validate_header("forecast_runs", header)
    
    def test_filter_known_columns_pricing_rules(self):
        validator = self._make_validator()
        row = {
            "rule_id": "R1",
            "product_code": "STANDARD",
            "utilization_band_min": "0.0",
            "utilization_band_max": "1.0",
            "price_per_visit": "5.00",
            "price_pmpm": "10.00",
            "effective_start_date": "2025-01-01",
            "extra_field": "should_be_filtered"
        }
        
        result = validator.filter_known_columns("pricing_rules", row)
        
        assert "rule_id" in result
        assert "extra_field" not in result
    
    def test_validate_header_multiple_missing_columns(self):
        validator = self._make_validator()
        header = ["employer_id"]  
        
        with pytest.raises(SchemaMismatchError) as exc_info:
            validator.validate_header("utilization_history", header)
        
        error_msg = str(exc_info.value)
        assert "Missing required columns" in error_msg
        assert "gym_id" in error_msg or "product_code" in error_msg


class TestSchemaValidatorEdgeCases:
    """Edge case tests for SchemaValidator using fixtures."""
    
    def test_validate_header_with_whitespace_in_names(self, schema_validator):
        """Test header validation handles leading/trailing whitespace."""
        header = [" employer_id ", "gym_id", "product_code", "forecast_period", "actual_visits"]
        # Whitespace should cause validation to fail
        with pytest.raises(SchemaMismatchError):
            schema_validator.validate_header("utilization_history", header)
    
    def test_validate_header_duplicate_columns(self, schema_validator):
        """Test header with duplicate column names."""
        header = [
            "employer_id", "gym_id", "product_code", "forecast_period",
            "actual_visits", "gym_id"  # duplicate
        ]
        # Should not raise - duplicates allowed but unusual
        schema_validator.validate_header("utilization_history", header)
    
    def test_validate_header_all_columns_optional_table(self, schema_validator):
        """Test table where only minimal required columns are present."""
        header = ["run_id", "forecast_period", "created_at", "model_version", "status"]
        schema_validator.validate_header("forecast_runs", header)
    
    def test_filter_known_columns_preserves_order(self, schema_validator):
        """Test that filtering preserves the order of known columns."""
        row = {
            "utilization_rate": "2.0",
            "employer_id": "E1",
            "actual_visits": "10",
            "gym_id": "G1",
        }
        result = schema_validator.filter_known_columns("utilization_history", row)
        # All keys should be in result
        assert set(result.keys()) == set(row.keys())
    
    def test_filter_known_columns_with_none_values(self, schema_validator):
        """Test filtering keeps None values for known columns."""
        row = {
            "employer_id": "E1",
            "gym_id": None,
            "product_code": "STANDARD",
        }
        result = schema_validator.filter_known_columns("utilization_history", row)
        assert "gym_id" in result
        assert result["gym_id"] is None
    
    def test_filter_known_columns_empty_string_values(self, schema_validator):
        """Test filtering keeps empty strings for known columns."""
        row = {
            "employer_id": "",
            "gym_id": "G1",
            "product_code": "",
        }
        result = schema_validator.filter_known_columns("utilization_history", row)
        assert result["employer_id"] == ""
        assert result["product_code"] == ""
    
    def test_validate_header_all_tables(self, schema_validator):
        """Test header validation works for all supported tables."""
        test_cases = [
            ("utilization_history", ["employer_id", "gym_id", "product_code", "forecast_period", "actual_visits"]),
            ("pricing_rules", ["rule_id", "product_code", "utilization_band_min", "utilization_band_max", "price_per_visit", "price_pmpm", "effective_start_date"]),
            ("forecasts", ["run_id", "employer_id", "gym_id", "product_code", "forecast_period", "forecast_visits"]),
            ("forecast_runs", ["run_id", "forecast_period", "created_at", "model_version", "status"]),
        ]
        
        for table_name, header in test_cases:
            schema_validator.validate_header(table_name, header)
    
    def test_filter_columns_mixed_known_unknown(self, schema_validator):
        """Test filtering with mix of known and unknown columns."""
        row = {
            "employer_id": "E1",
            "unknown1": "bad",
            "gym_id": "G1",
            "unknown2": "also_bad",
            "product_code": "STANDARD",
        }
        result = schema_validator.filter_known_columns("utilization_history", row)
        assert len(result) == 3
        assert "unknown1" not in result
        assert "unknown2" not in result
