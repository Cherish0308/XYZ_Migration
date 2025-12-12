from __future__ import annotations

import pytest

from app.repositories.metadata_repository import InMemoryMetadataRepository


class TestInMemoryMetadataRepository:
    
    def test_get_table_schema_utilization_history(self):
        repo = InMemoryMetadataRepository()
        schema = repo.get_table_schema("utilization_history")
        
        assert "employer_id" in schema
        assert schema["employer_id"] == "STRING"
        assert schema["actual_visits"] == "INT"
        assert schema["utilization_rate"] == "DECIMAL"
        assert schema["forecast_period"] == "PERIOD"
    
    def test_get_table_schema_pricing_rules(self):
        repo = InMemoryMetadataRepository()
        schema = repo.get_table_schema("pricing_rules")
        
        assert "rule_id" in schema
        assert schema["price_per_visit"] == "DECIMAL"
        assert schema["effective_start_date"] == "DATE"
    
    def test_get_table_schema_forecasts(self):
        repo = InMemoryMetadataRepository()
        schema = repo.get_table_schema("forecasts")
        
        assert "run_id" in schema
        assert "forecast_visits" in schema
        assert schema["forecast_visits"] == "DECIMAL"
    
    def test_get_table_schema_forecast_runs(self):
        repo = InMemoryMetadataRepository()
        schema = repo.get_table_schema("forecast_runs")
        
        assert "run_id" in schema
        assert "created_at" in schema
        assert schema["created_at"] == "TIMESTAMP"
        assert schema["status"] == "STRING"
    
    def test_get_required_columns_utilization_history(self):
        repo = InMemoryMetadataRepository()
        required = repo.get_required_columns("utilization_history")
        
        assert "employer_id" in required
        assert "gym_id" in required
        assert "product_code" in required
        assert "forecast_period" in required
        assert "actual_visits" in required
        # eligible_members is not required
        assert len(required) == 5
    
    def test_get_required_columns_pricing_rules(self):
        repo = InMemoryMetadataRepository()
        required = repo.get_required_columns("pricing_rules")
        
        assert "rule_id" in required
        assert "product_code" in required
        assert "effective_start_date" in required
        # effective_end_date is optional
    
    def test_get_redshift_table_standard(self):
        repo = InMemoryMetadataRepository()
        redshift_table = repo.get_redshift_table("utilization_history")
        assert redshift_table == "stg_utilization_history"
    
    def test_get_redshift_table_pricing_rules(self):
        repo = InMemoryMetadataRepository()
        redshift_table = repo.get_redshift_table("pricing_rules")
        assert redshift_table == "stg_pricing_rules"
    
    def test_get_redshift_table_forecasts(self):
        repo = InMemoryMetadataRepository()
        redshift_table = repo.get_redshift_table("forecasts")
        assert redshift_table == "stg_forecasts"
    
    def test_get_business_keys_utilization_history(self):
        repo = InMemoryMetadataRepository()
        business_keys = repo.get_business_keys("utilization_history")
        
        assert "employer_id" in business_keys
        assert "gym_id" in business_keys
        assert "product_code" in business_keys
        assert "forecast_period" in business_keys
        assert len(business_keys) == 4
    
    def test_get_business_keys_pricing_rules(self):
        repo = InMemoryMetadataRepository()
        business_keys = repo.get_business_keys("pricing_rules")
        
        assert business_keys == ["rule_id"]
    
    def test_get_business_keys_forecasts(self):
        repo = InMemoryMetadataRepository()
        business_keys = repo.get_business_keys("forecasts")
        
        assert "run_id" in business_keys
        assert "employer_id" in business_keys
        assert "gym_id" in business_keys
        assert len(business_keys) == 5
    
    def test_all_tables_have_schemas(self):
        repo = InMemoryMetadataRepository()
        tables = ["utilization_history", "pricing_rules", "forecasts", "forecast_runs"]
        
        for table in tables:
            schema = repo.get_table_schema(table)
            assert isinstance(schema, dict)
            assert len(schema) > 0
    
    def test_all_tables_have_required_columns(self):
        repo = InMemoryMetadataRepository()
        tables = ["utilization_history", "pricing_rules", "forecasts", "forecast_runs"]
        
        for table in tables:
            required = repo.get_required_columns(table)
            assert isinstance(required, list)
            assert len(required) > 0
    
    def test_all_tables_have_business_keys(self):
        repo = InMemoryMetadataRepository()
        tables = ["utilization_history", "pricing_rules", "forecasts", "forecast_runs"]
        
        for table in tables:
            business_keys = repo.get_business_keys(table)
            assert isinstance(business_keys, list)
            assert len(business_keys) > 0
