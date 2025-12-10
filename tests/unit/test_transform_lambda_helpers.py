from __future__ import annotations

import pytest
from typing import Dict, Any

from app.lambdas.transform_lambda_helpers import (
    S3EventParser,
    S3EventRecord,
    CSVTransformProcessor,
    S3TransformOrchestrator,
)
from app.repositories.metadata_repository import InMemoryMetadataRepository
from app.services.transformation_service import TransformationService


class TestS3EventParser:
    """Tests for S3EventParser class."""
    
    def test_parse_single_record(self):
        parser = S3EventParser()
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "my-bucket"},
                        "object": {"key": "path/to/file.csv"},
                    }
                }
            ]
        }
        
        records = parser.parse_records(event)
        
        assert len(records) == 1
        assert records[0].bucket == "my-bucket"
        assert records[0].key == "path/to/file.csv"
    
    def test_parse_multiple_records(self):
        parser = S3EventParser()
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "bucket1"},
                        "object": {"key": "file1.csv"},
                    }
                },
                {
                    "s3": {
                        "bucket": {"name": "bucket2"},
                        "object": {"key": "file2.csv"},
                    }
                },
            ]
        }
        
        records = parser.parse_records(event)
        
        assert len(records) == 2
        assert records[0].bucket == "bucket1"
        assert records[1].bucket == "bucket2"
    
    def test_parse_url_encoded_key(self):
        parser = S3EventParser()
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "my-bucket"},
                        "object": {"key": "path%2Fwith%20spaces%2Ffile.csv"},
                    }
                }
            ]
        }
        
        records = parser.parse_records(event)
        
        # URL decoding should convert %2F to / and %20 to space
        assert "path/with spaces/file.csv" in records[0].key
    
    def test_parse_empty_records(self):
        parser = S3EventParser()
        event = {"Records": []}
        
        records = parser.parse_records(event)
        
        assert len(records) == 0


class TestCSVTransformProcessor:
    """Tests for CSVTransformProcessor class."""
    
    def _make_processor(self) -> CSVTransformProcessor:
        metadata_repo = InMemoryMetadataRepository()
        transform_service = TransformationService(metadata_repo)
        return CSVTransformProcessor(transform_service)
    
    def test_process_csv_valid(self):
        processor = self._make_processor()
        csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01-15,10,5,2.0
"""
        
        rows, header = processor.process_csv(csv_text, "utilization_history")
        
        assert len(rows) == 1
        assert header == ["employer_id", "gym_id", "product_code", "forecast_period", "actual_visits", "eligible_members", "utilization_rate"]
        # forecast_period should be normalized to 2025-01
        assert rows[0]["forecast_period"] == "2025-01"
        assert rows[0]["actual_visits"] == "10"
    
    def test_process_csv_no_header(self):
        processor = self._make_processor()
        csv_text = ""
        
        with pytest.raises(ValueError, match="CSV has no header"):
            processor.process_csv(csv_text, "utilization_history")
    
    def test_write_csv_output(self):
        processor = self._make_processor()
        rows = [
            {"col1": "value1", "col2": "value2"},
            {"col1": "value3", "col2": "value4"},
        ]
        header = ["col1", "col2"]
        
        csv_output = processor.write_csv(rows, header)
        
        assert "col1,col2" in csv_output
        assert "value1,value2" in csv_output
        assert "value3,value4" in csv_output
    
    def test_write_csv_with_none_values(self):
        processor = self._make_processor()
        rows = [
            {"col1": "value1", "col2": ""},
        ]
        header = ["col1", "col2"]
        
        csv_output = processor.write_csv(rows, header)
        
        assert "value1," in csv_output


class TestS3TransformOrchestrator:
    """Tests for S3TransformOrchestrator class."""
    
    class FakeS3Repo:
        def __init__(self, csv_text: str) -> None:
            self._csv_text = csv_text
            self.written = []
        
        def read_text(self, bucket: str, key: str) -> str:
            return self._csv_text
        
        def write_text(self, bucket: str, key: str, body: str) -> None:
            self.written.append({"bucket": bucket, "key": key, "body": body})
    
    def _make_orchestrator(self, csv_text: str) -> tuple[S3TransformOrchestrator, FakeS3Repo]:
        fake_repo = self.FakeS3Repo(csv_text)
        metadata_repo = InMemoryMetadataRepository()
        transform_service = TransformationService(metadata_repo)
        processor = CSVTransformProcessor(transform_service)
        orchestrator = S3TransformOrchestrator(fake_repo, processor)
        return orchestrator, fake_repo
    
    def test_transform_and_upload(self):
        csv_text = """employer_id,gym_id,product_code,forecast_period,actual_visits,eligible_members,utilization_rate
E1,G1,STANDARD,2025-01-15,10,5,2.0
"""
        orchestrator, fake_repo = self._make_orchestrator(csv_text)
        
        result = orchestrator.transform_and_upload(
            bucket="test-bucket",
            source_key="validated/utilization_history/forecast_period=2025-01/file.csv",
            table_name="utilization_history",
            logical_period="2025-01",
            transformed_prefix="transformed",
        )
        
        assert result["outcome"] == "SUCCEEDED"
        assert result["table_name"] == "utilization_history"
        assert result["logical_period"] == "2025-01"
        assert result["row_count"] == 1
        assert result["dest_key"].startswith("transformed/utilization_history/")
        
        # Verify file was written
        assert len(fake_repo.written) == 1
        assert fake_repo.written[0]["key"] == result["dest_key"]
        # Verify normalized period in output
        assert "2025-01" in fake_repo.written[0]["body"]
