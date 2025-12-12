from __future__ import annotations

import pytest
from datetime import datetime, date

from app.utils.time_utils import parse_date, parse_timestamp, normalize_period


class TestParseDate:

    
    def test_parse_standard_date(self):
        result = parse_date("2025-01-15")
        assert result == date(2025, 1, 15)
    
    def test_parse_date_with_timestamp(self):
        
        result = parse_date("2025-12-31 23:59:59")
        assert result == date(2025, 12, 31)
    
    def test_parse_date_edge_case_february_leap_year(self):
        result = parse_date("2024-02-29")
        assert result == date(2024, 2, 29)
    
    def test_parse_date_edge_case_february_non_leap_year(self):
        with pytest.raises(ValueError):
            parse_date("2025-02-29")
    
    def test_parse_date_invalid_format(self):
        with pytest.raises(ValueError):
            parse_date("01-15-2025")
    
    def test_parse_date_empty_string(self):
        with pytest.raises(ValueError):
            parse_date("")


class TestParseTimestamp:
    
    
    def test_parse_iso_format_with_z(self):
        result = parse_timestamp("2025-01-15T10:30:00Z")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0
    
    def test_parse_iso_format_with_offset(self):
        result = parse_timestamp("2025-01-15T10:30:00+00:00")
        assert result.year == 2025
        assert result.hour == 10
    
    def test_parse_simple_timestamp(self):
        result = parse_timestamp("2025-01-15 10:30:00")
        assert result == datetime(2025, 1, 15, 10, 30, 0)
    
    def test_parse_timestamp_with_microseconds(self):
        result = parse_timestamp("2025-01-15T10:30:00.123456Z")
        assert result.microsecond == 123456
    
    def test_parse_timestamp_invalid_format(self):
        with pytest.raises(ValueError):
            parse_timestamp("not-a-timestamp")


class TestNormalizePeriod:
    
    
    def test_normalize_period_yyyy_mm(self):
        result = normalize_period("2025-01")
        assert result == "2025-01"
    
    def test_normalize_period_from_full_date(self):
        result = normalize_period("2025-01-15")
        assert result == "2025-01"
    
    def test_normalize_period_from_timestamp(self):
        result = normalize_period("2025-12-31 23:59:59")
        assert result == "2025-12"
    
    def test_normalize_period_edge_case_december(self):
        result = normalize_period("2024-12-01")
        assert result == "2024-12"
    
    def test_normalize_period_edge_case_january(self):
        result = normalize_period("2025-01-01")
        assert result == "2025-01"
    
    def test_normalize_period_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid period"):
            normalize_period("01-2025")
    
    def test_normalize_period_too_short(self):
        with pytest.raises(ValueError, match="Invalid period"):
            normalize_period("2025")
    
    def test_normalize_period_no_hyphen(self):
        with pytest.raises(ValueError, match="Invalid period"):
            normalize_period("202501")
