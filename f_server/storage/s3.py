from __future__ import annotations

from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from f_server.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint: str | None,
        public_endpoint: str | None,
        access_key: str | None,
        secret_key: str | None,
    ) -> None:
        self.bucket = bucket
        self.public_endpoint = public_endpoint
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )
        self.presign_client = self.client
        if public_endpoint:
            self.presign_client = boto3.client(
                "s3",
                region_name=region,
                endpoint_url=public_endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4"),
            )

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs={"ContentType": content_type})

    def open_stream(self, key: str) -> BinaryIO:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]

    def url_for(self, key: str, expires: int = 300) -> str | None:
        return self.presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                return False
            raise
