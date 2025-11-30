from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import psycopg2
from psycopg2.extensions import connection as PgConnection

from app.config import AppConfig
from app.exceptions import RepositoryError
from app.repositories.base import WarehouseRepository

logger = logging.getLogger(__name__)


class RedshiftWarehouseRepository(WarehouseRepository):
    """
    Redshift-backed implementation of WarehouseRepository.

    All direct DB access is encapsulated here so services remain testable
    and follow dependency inversion.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def _get_connection(self) -> PgConnection:
        try:
            conn = psycopg2.connect(
                host=self._config.redshift_host,
                port=self._config.redshift_port,
                dbname=self._config.redshift_database,
                user=self._config.redshift_user,
                password=self._config.redshift_password,
            )
            conn.autocommit = True
            return conn
        except Exception as exc:  # pragma: no cover (hard to hit in unit tests)
            logger.error("Failed to connect to Redshift")
            raise RepositoryError("Failed to connect to Redshift") from exc

    def copy_from_s3(
        self,
        table_name: str,
        s3_uri: str,
        iam_role_arn: str,
        file_format: str,
        copy_options: Optional[List[str]] = None,
    ) -> None:
        """
        Execute a Redshift COPY command from S3.

        file_format examples: 'CSV', 'PARQUET'
        copy_options examples: ['IGNOREHEADER 1', 'TIMEFORMAT AS \'auto\'']
        """
        copy_options = copy_options or []
        options_str = " ".join(copy_options)
        sql = f"""
            COPY {table_name}
            FROM %s
            IAM_ROLE %s
            FORMAT AS {file_format}
            {options_str}
        """
        logger.info(
            "Executing Redshift COPY",
            extra={"table_name": table_name, "s3_uri": s3_uri, "options": options_str},
        )
        self.execute_sql(sql, params=(s3_uri, iam_role_arn))

    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> None:
        """
        Execute a SQL statement without returning rows.
        """
        if self._config.dry_run:
            logger.info("DRY RUN - would execute SQL", extra={"sql": sql, "params": params})
            return

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(sql, params)
        except Exception as exc:  # pragma: no cover
            logger.error("Redshift SQL execution failed", extra={"sql": sql})
            raise RepositoryError("Redshift SQL execution failed") from exc

    def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        """
        Execute a SQL query and return a single row, or None.
        """
        if self._config.dry_run:
            logger.info("DRY RUN - would fetch SQL", extra={"sql": sql, "params": params})
            return None

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        except Exception as exc:  # pragma: no cover
            logger.error("Redshift fetch failed", extra={"sql": sql})
            raise RepositoryError("Redshift fetch failed") from exc
