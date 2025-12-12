from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.repositories import S3ObjectStorageRepository, MetadataRepository
from app.services import TransformationService
from app.utils import s3_path_utils

logger = logging.getLogger(__name__)


@dataclass
class S3EventRecord:
   
    bucket: str
    key: str


class S3EventParser:
   
    
    @staticmethod
    def parse_records(event: Dict[str, Any]) -> List[S3EventRecord]:
        """Extract S3 records from Lambda event."""
        records = []
        for record in event.get("Records", []):
            bucket = record["s3"]["bucket"]["name"]
            raw_key = record["s3"]["object"]["key"]
            # URL decode the key
            import urllib.parse
            key = urllib.parse.unquote_plus(raw_key)
            records.append(S3EventRecord(bucket=bucket, key=key))
        return records


class CSVTransformProcessor:
    
    
    def __init__(self, transform_service: TransformationService) -> None:
        self._transform_service = transform_service
    
    def process_csv(
        self,
        csv_text: str,
        table_name: str,
    ) -> tuple[List[Dict[str, Any]], List[str]]:
       
        reader = csv.DictReader(csv_text.splitlines())
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        
        header = [h.strip() for h in reader.fieldnames]
        transformed_rows: List[Dict[str, Any]] = []
        
        for row in reader:
            normalized = {k.strip(): v for k, v in row.items() if k is not None}
            transformed = self._transform_service.transform_row(table_name, normalized)
            # Convert back to string representation for CSV write
            transformed_rows.append({
                col: "" if v is None else str(v)
                for col, v in transformed.items()
            })
        
        return transformed_rows, header
    
    @staticmethod
    def write_csv(
        transformed_rows: List[Dict[str, Any]],
        header: List[str],
    ) -> str:
        """Write transformed rows to CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=header)
        writer.writeheader()
        
        for row in transformed_rows:
            # Only keep columns in the original header to keep file shape stable
            writer.writerow({col: row.get(col, "") for col in header})
        
        return output.getvalue()


class S3TransformOrchestrator:
    """Orchestrates the S3 transform workflow."""
    
    def __init__(
        self,
        s3_repo: S3ObjectStorageRepository,
        csv_processor: CSVTransformProcessor,
    ) -> None:
        self._s3_repo = s3_repo
        self._csv_processor = csv_processor
    
    def transform_and_upload(
        self,
        bucket: str,
        source_key: str,
        table_name: str,
        logical_period: str,
        transformed_prefix: str,
    ) -> Dict[str, Any]:
       
        # Read source CSV
        csv_text = self._s3_repo.read_text(bucket, source_key)
        
        # Transform CSV
        transformed_rows, header = self._csv_processor.process_csv(csv_text, table_name)
        
        # Write transformed CSV
        transformed_csv = self._csv_processor.write_csv(transformed_rows, header)
        
        # Build destination key and upload
        dest_key = s3_path_utils.build_transformed_key(
            transformed_prefix,
            table_name,
            logical_period,
            source_key,
        )
        
        self._s3_repo.write_text(bucket, dest_key, transformed_csv)
        
        logger.info(
            "Transform completed for file",
            extra={
                "table_name": table_name,
                "logical_period": logical_period,
                "dest_key": dest_key,
                "row_count": len(transformed_rows),
            },
        )
        
        return {
            "table_name": table_name,
            "logical_period": logical_period,
            "dest_key": dest_key,
            "row_count": len(transformed_rows),
            "outcome": "SUCCEEDED",
        }
