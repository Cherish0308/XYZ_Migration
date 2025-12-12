from __future__ import annotations

import pytest

from app.utils.json_utils import dumps, loads


class TestJsonDumps:
    
    
    def test_dumps_simple_dict(self):
        obj = {"key": "value", "number": 42}
        result = dumps(obj)
        assert '"key": "value"' in result
        assert '"number": 42' in result
    
    def test_dumps_with_date_object(self):
        from datetime import date
        obj = {"date": date(2025, 1, 15)}
        result = dumps(obj)
        # Should convert date to string using default=str
        assert "2025-01-15" in result
    
    def test_dumps_with_datetime_object(self):
        from datetime import datetime
        obj = {"timestamp": datetime(2025, 1, 15, 10, 30, 0)}
        result = dumps(obj)
        # Should convert datetime to string
        assert "2025-01-15" in result
        assert "10:30:00" in result
    
    def test_dumps_nested_structure(self):
        obj = {
            "level1": {
                "level2": {
                    "value": 123
                }
            }
        }
        result = dumps(obj)
        assert "level1" in result
        assert "level2" in result
        assert "123" in result
    
    def test_dumps_list(self):
        obj = [1, 2, 3, "four"]
        result = dumps(obj)
        assert "[1, 2, 3" in result
        assert "four" in result
    
    def test_dumps_empty_dict(self):
        result = dumps({})
        assert result == "{}"
    
    def test_dumps_none_value(self):
        obj = {"key": None}
        result = dumps(obj)
        assert "null" in result


class TestJsonLoads:
    
    def test_loads_simple_dict(self):
        json_str = '{"key": "value", "number": 42}'
        result = loads(json_str)
        assert result == {"key": "value", "number": 42}
    
    def test_loads_nested_structure(self):
        json_str = '{"level1": {"level2": {"value": 123}}}'
        result = loads(json_str)
        assert result["level1"]["level2"]["value"] == 123
    
    def test_loads_list(self):
        json_str = '[1, 2, 3, "four"]'
        result = loads(json_str)
        assert result == [1, 2, 3, "four"]
    
    def test_loads_empty_dict(self):
        result = loads("{}")
        assert result == {}
    
    def test_loads_null_value(self):
        json_str = '{"key": null}'
        result = loads(json_str)
        assert result["key"] is None
    
    def test_loads_boolean_values(self):
        json_str = '{"true_val": true, "false_val": false}'
        result = loads(json_str)
        assert result["true_val"] is True
        assert result["false_val"] is False
    
    def test_loads_invalid_json(self):
        with pytest.raises(Exception):  # json.JSONDecodeError
            loads("not valid json")
    
    def test_loads_empty_string(self):
        with pytest.raises(Exception):
            loads("")


class TestJsonRoundTrip:
    
    def test_round_trip_simple(self):
        original = {"key": "value", "number": 42}
        json_str = dumps(original)
        result = loads(json_str)
        assert result == original
    
    def test_round_trip_nested(self):
        original = {
            "data": {
                "users": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]
            }
        }
        json_str = dumps(original)
        result = loads(json_str)
        assert result == original
