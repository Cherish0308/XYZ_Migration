from __future__ import annotations

from typing import Any, Dict

from app.exceptions import BusinessRuleViolation


class UtilizationHistoryValidator:
    def validate(self, record: Dict[str, Any]) -> None:
        try:
            actual_visits = int(record.get("actual_visits", 0))
            eligible_members = int(record.get("eligible_members", 0))
            utilization_rate = float(record.get("utilization_rate", 0.0))
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("Invalid numeric values in utilization_history") from exc

        if actual_visits < 0:
            raise BusinessRuleViolation("actual_visits cannot be negative")
        if eligible_members < 0:
            raise BusinessRuleViolation("eligible_members cannot be negative")
        if utilization_rate < 0.0 or utilization_rate > 5.0:
            raise BusinessRuleViolation("utilization_rate outside expected range [0, 5.0]")


class PricingRulesValidator:
    def validate(self, record: Dict[str, Any]) -> None:
        from app.utils.time_utils import parse_date
        try:
            band_min = float(record.get("utilization_band_min", 0.0))
            band_max = float(record.get("utilization_band_max", 0.0))
            price_per_visit = float(record.get("price_per_visit", 0.0))
            price_pmpm = float(record.get("price_pmpm", 0.0))
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("Invalid numeric values in pricing_rules") from exc

        if band_min < 0.0 or band_max <= band_min:
            raise BusinessRuleViolation("Invalid utilization band range")
        if price_per_visit < 0.0 or price_pmpm < 0.0:
            raise BusinessRuleViolation("Pricing cannot be negative")

        start_raw = record.get("effective_start_date")
        end_raw = record.get("effective_end_date")
        if start_raw:
            start = parse_date(str(start_raw))
            if end_raw:
                end = parse_date(str(end_raw))
                if end < start:
                    raise BusinessRuleViolation("effective_end_date cannot be before effective_start_date")


class ForecastsValidator:
    def validate(self, record: Dict[str, Any]) -> None:
        try:
            forecast_visits = float(record.get("forecast_visits", 0.0))
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("Invalid forecast_visits value") from exc
        if forecast_visits < 0.0:
            raise BusinessRuleViolation("forecast_visits cannot be negative")


class ForecastRunsValidator:
    def validate(self, record: Dict[str, Any]) -> None:
        status = str(record.get("status", "")).upper()
        allowed = {"SUCCEEDED", "FAILED", "PARTIAL"}
        if status not in allowed:
            raise BusinessRuleViolation(f"Invalid forecast_runs status: {status}")


class BusinessValidator:
    def __init__(self) -> None:
        self._validators = {
            "utilization_history": UtilizationHistoryValidator(),
            "pricing_rules": PricingRulesValidator(),
            "forecasts": ForecastsValidator(),
            "forecast_runs": ForecastRunsValidator(),
        }

    def validate(self, table_name: str, record: Dict[str, Any]) -> None:
        validator = self._validators.get(table_name)
        if validator:
            validator.validate(record)
        # else: unknown table, no business rules
