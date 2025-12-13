from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.config import AppConfig
from app.repositories import MetadataRepository, WarehouseRepository


@dataclass(frozen=True)
class LoadResult:
    table_name: str          
    redshift_table: str      
    logical_period: str
    s3_key: str
    s3_uri: str
    file_format: str


class LoadService:
   

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
        metadata_repo: MetadataRepository,
        config: AppConfig,
    ) -> None:
        self._warehouse_repo = warehouse_repo
        self._metadata_repo = metadata_repo
        self._config = config

    def _build_s3_uri(self, key: str) -> str:
        return f"s3://{self._config.s3_bucket}/{key}"

    def load_transformed_file(
        self,
        table_name: str,
        logical_period: str,
        s3_key: str,
        file_format: str = "CSV",
    ) -> LoadResult:
        
        redshift_table = self._metadata_repo.get_redshift_table(table_name)
        s3_uri = self._build_s3_uri(s3_key)

        copy_options: List[str] = [
            "IGNOREHEADER 1",
            "TIMEFORMAT AS 'auto'",
            "EMPTYASNULL",
            "BLANKSASNULL",
            "TRUNCATECOLUMNS",
        ]

        self._warehouse_repo.copy_from_s3(
            table_name=redshift_table,
            s3_uri=s3_uri,
            iam_role_arn=self._config.redshift_iam_role_arn,
            file_format=file_format,
            copy_options=copy_options,
        )

        return LoadResult(
            table_name=table_name,
            redshift_table=redshift_table,
            logical_period=logical_period,
            s3_key=s3_key,
            s3_uri=s3_uri,
            file_format=file_format,
        )
