"""Private storage backends.

The fixture backend keeps bytes on local disk under a private directory and is
explicitly labelled FIXTURE. The S3-compatible backend uses boto3 against a
private bucket; it activates only with configured credentials. Access always
flows through the first-party authorization proxy; direct object URLs are never
handed to shoppers, so revocation blocks new access immediately.
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    mode: str

    @abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes | None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class FixtureStorageBackend(StorageBackend):
    """Local private directory; demo and test use only, never a production claim."""

    mode = 'FIXTURE'

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or os.getenv('ANCHOR_STORAGE_DIR') or '.anchor-storage')

    def _path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put(self, key: str, data: bytes) -> None:
        self._path(key).write_bytes(data)

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()


class S3StorageBackend(StorageBackend):
    """Private S3-compatible bucket via boto3; requires explicit configuration."""

    mode = 'LIVE'

    def __init__(self) -> None:
        import boto3  # type: ignore[import-untyped]

        self._client = boto3.client(
            's3', endpoint_url=os.environ.get('OBJECT_STORAGE_ENDPOINT'),
            aws_access_key_id=os.environ.get('OBJECT_STORAGE_ACCESS_KEY'),
            aws_secret_access_key=os.environ.get('OBJECT_STORAGE_SECRET_KEY'))
        self._bucket = os.environ['OBJECT_STORAGE_BUCKET']

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError  # type: ignore[import-untyped]

        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError:
            return None
        return response['Body'].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def create_backend() -> StorageBackend:
    if os.getenv('OBJECT_STORAGE_ACCESS_KEY'):
        return S3StorageBackend()
    return FixtureStorageBackend()
