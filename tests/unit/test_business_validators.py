from __future__ import annotations

import pytest

from app.validators.business_validator import (
    BusinessRuleViolation,
    ForecastRunsValidator,
    ForecastsValidator,
    PricingRulesValidator,
    UtilizationHistoryValidator,
)


def test_utilization_history_validator_valid():
    validator = UtilizationHistoryValidator()
    record = {
        "actual_visits": 10,
        "eligible_members": 5,
        "utilization_rate": 2.0,
    }
    validator.validate(record)  # Should not raise

def test_utilization_history_validator_negative_visits():
    validator = UtilizationHistoryValidator()
    record = {
        "actual_visits": -1,
        "eligible_members": 5,
        "utilization_rate": 2.0,
    }
    with pytest.raises(BusinessRuleViolation):
        validator.validate(record)

def test_pricing_rules_validator_invalid_band():
    validator = PricingRulesValidator()
    record = {
        "utilization_band_min": 5.0,
        "utilization_band_max": 4.0,
        "price_per_visit": 1.0,
        "price_pmpm": 1.0,
        "effective_start_date": "2025-01-01",
        "effective_end_date": "2025-01-02",
    }
    with pytest.raises(BusinessRuleViolation):
        validator.validate(record)

def test_forecasts_validator_negative_forecast():
    validator = ForecastsValidator()
    record = {"forecast_visits": -10.0}
    with pytest.raises(BusinessRuleViolation):
        validator.validate(record)

def test_forecast_runs_validator_invalid_status():
    validator = ForecastRunsValidator()
    record = {"status": "UNKNOWN"}
    with pytest.raises(BusinessRuleViolation):
        validator.validate(record)
