from __future__ import annotations

import logging
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.exceptions import RepositoryError
from app.repositories.base import ObjectStorageRepository

logger = logging.getLogger(__name__)


class S3ObjectStorageRepository(ObjectStorageRepository):
    

    def __init__(self, s3_client: Optional[boto3.client] = None) -> None:
        # Allow injecting a fake/mocked client for tests
        self._s3 = s3_client or boto3.client("s3")

    def read_text(self, bucket: str, key: str) -> str:
        try:
            resp = self._s3.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read().decode("utf-8")
        except ClientError as exc:  # pragma: no cover (hard to hit in unit tests)
            logger.error(
                "Failed to read S3 object",
                extra={"bucket": bucket, "key": key},
            )
            raise RepositoryError(f"Failed to read s3://{bucket}/{key}") from exc

    def write_text(self, bucket: str, key: str, body: str) -> None:
        try:
            self._s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))
        except ClientError as exc:  # pragma: no cover
            logger.error(
                "Failed to write S3 object",
                extra={"bucket": bucket, "key": key},
            )
            raise RepositoryError(f"Failed to write s3://{bucket}/{key}") from exc

    def copy_object(self, src_bucket: str, src_key: str, dest_bucket: str, dest_key: str) -> None:
        try:
            self._s3.copy_object(
                Bucket=dest_bucket,
                Key=dest_key,
                CopySource={"Bucket": src_bucket, "Key": src_key},
            )
        except ClientError as exc:  # pragma: no cover
            logger.error(
                "Failed to copy S3 object",
                extra={
                    "src_bucket": src_bucket,
                    "src_key": src_key,
                    "dest_bucket": dest_bucket,
                    "dest_key": dest_key,
                },
            )
            raise RepositoryError(
                f"Failed to copy s3://{src_bucket}/{src_key} to s3://{dest_bucket}/{dest_key}"
            ) from exc

    def delete_object(self, bucket: str, key: str) -> None:
        try:
            self._s3.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:  # pragma: no cover
            logger.error(
                "Failed to delete S3 object",
                extra={"bucket": bucket, "key": key},
            )
            raise RepositoryError(f"Failed to delete s3://{bucket}/{key}") from exc

    def list_keys(self, bucket: str, prefix: str) -> List[str]:
        keys: List[str] = []
        token: Optional[str] = None

        while True:
            try:
                if token:
                    resp = self._s3.list_objects_v2(
                        Bucket=bucket,
                        Prefix=prefix,
                        ContinuationToken=token,
                    )
                else:
                    resp = self._s3.list_objects_v2(
                        Bucket=bucket,
                        Prefix=prefix,
                    )
            except ClientError as exc:  # pragma: no cover
                logger.error(
                    "Failed to list S3 objects",
                    extra={"bucket": bucket, "prefix": prefix},
                )
                raise RepositoryError(f"Failed to list s3://{bucket}/{prefix}") from exc

            for obj in resp.get("Contents", []):
                keys.append(obj["Key"])

            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
            else:
                break

        return keys

    def head_object(self, bucket: str, key: str) -> Dict[str, str]:
        try:
            resp = self._s3.head_object(Bucket=bucket, Key=key)
            return {
                "ContentLength": str(resp.get("ContentLength", "0")),
                "ETag": resp.get("ETag", ""),
                "ContentType": resp.get("ContentType", ""),
            }
        except ClientError as exc:  # pragma: no cover
            logger.error(
                "Failed to head S3 object",
                extra={"bucket": bucket, "key": key},
            )
            raise RepositoryError(f"Failed to head s3://{bucket}/{key}") from exc
