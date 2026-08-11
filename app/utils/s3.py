import boto3
from botocore.config import Config
import asyncio
from app.config import settings

s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
    config=Config(signature_version="s3v4", s3={'addressing_style': 'virtual'}),
)


async def upload_file(key: str, contents: bytes, content_type: str | None) -> None:
    await asyncio.to_thread(
        s3.put_object,
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=contents,
        ContentType=content_type,
    )


async def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return await asyncio.to_thread(
        s3.generate_presigned_url,
        ClientMethod='get_object',
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )


async def delete_file(key: str):
    await asyncio.to_thread(s3.delete_object, Bucket=settings.s3_bucket_name, Key=key)
