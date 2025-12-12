from __future__ import annotations

from app.utils.idempotency import compute_idempotency_key


class TestComputeIdempotencyKey:
    
    
    def test_compute_idempotency_key_simple(self):
        payload = {"key1": "value1", "key2": "value2"}
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64  
    
    def test_compute_idempotency_key_deterministic(self):
        payload = {"key1": "value1", "key2": "value2"}
        result1 = compute_idempotency_key(payload)
        result2 = compute_idempotency_key(payload)
        assert result1 == result2
    
    def test_compute_idempotency_key_order_independent(self):
    
        payload1 = {"a": "1", "b": "2", "c": "3"}
        payload2 = {"c": "3", "a": "1", "b": "2"}
        result1 = compute_idempotency_key(payload1)
        result2 = compute_idempotency_key(payload2)
        assert result1 == result2
    
    def test_compute_idempotency_key_different_values(self):
        payload1 = {"key": "value1"}
        payload2 = {"key": "value2"}
        result1 = compute_idempotency_key(payload1)
        result2 = compute_idempotency_key(payload2)
        assert result1 != result2
    
    def test_compute_idempotency_key_different_keys(self):
        payload1 = {"key1": "value"}
        payload2 = {"key2": "value"}
        result1 = compute_idempotency_key(payload1)
        result2 = compute_idempotency_key(payload2)
        assert result1 != result2
    
    def test_compute_idempotency_key_empty_dict(self):
        result = compute_idempotency_key({})
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_compute_idempotency_key_single_item(self):
        payload = {"single": "item"}
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_compute_idempotency_key_numeric_values(self):
        payload = {"count": "123", "amount": "456"}
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_compute_idempotency_key_special_characters(self):
        payload = {"key": "value with spaces", "symbol": "!@#$%"}
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_compute_idempotency_key_many_keys(self):
        payload = {f"key{i}": f"value{i}" for i in range(100)}
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_compute_idempotency_key_collision_resistance(self):
        # Similar payloads should produce different hashes
        payload1 = {"bucket": "xyz-bucket", "key": "file1.csv"}
        payload2 = {"bucket": "xyz-bucket", "key": "file2.csv"}
        result1 = compute_idempotency_key(payload1)
        result2 = compute_idempotency_key(payload2)
        assert result1 != result2
    
    def test_compute_idempotency_key_real_world_example(self):
        # Simulate real ingestion payload
        payload = {
            "bucket": "xyz-bucket",
            "key": "raw/utilization_history/forecast_period=2025-01/file.csv",
            "etag": "abc123",
            "content_length": "1024",
        }
        result = compute_idempotency_key(payload)
        assert isinstance(result, str)
        assert len(result) == 64
        assert result == compute_idempotency_key(payload)
