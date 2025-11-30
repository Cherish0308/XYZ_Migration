from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol, Tuple


class ObjectStorageRepository(Protocol):
    """
    Abstraction over S3-like object storage.

    Services depend on this interface; the concrete implementation
    (boto3-based S3) lives in a separate module.
    """

    def read_text(self, bucket: str, key: str) -> str:
        ...

    def write_text(self, bucket: str, key: str, body: str) -> None:
        ...

    def copy_object(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        ...

    def delete_object(self, bucket: str, key: str) -> None:
        ...

    def list_keys(self, bucket: str, prefix: str) -> List[str]:
        ...

    def head_object(self, bucket: str, key: str) -> Dict[str, str]:
        ...


class WarehouseRepository(Protocol):
    """
    Abstraction over a Redshift-like warehouse.
    """

    def copy_from_s3(
        self,
        table_name: str,
        s3_uri: str,
        iam_role_arn: str,
        file_format: str,
        copy_options: Optional[List[str]] = None,
    ) -> None:
        ...

    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> None:
        ...

    def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        ...


class MetadataRepository(ABC):
    """
    Source of table schemas and mappings (Snowflake → Redshift).

    Implementations could be in-memory, Glue, dbt manifest, etc.
    """

    @abstractmethod
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Return column_name → logical_type mapping."""

    @abstractmethod
    def get_required_columns(self, table_name: str) -> List[str]:
        """Columns that must be present and non-null for each table."""

    @abstractmethod
    def get_redshift_table(self, snowflake_table: str) -> str:
        """Target Redshift table name for a given Snowflake source."""

    @abstractmethod
    def get_business_keys(self, table_name: str) -> List[str]:
        """Business key columns for dedupe and DQ checks."""
