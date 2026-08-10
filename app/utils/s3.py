import boto3
from app.config import settings

s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

def upload_file(key: str, contents: bytes, content_type: str | None) -> None:
    s3.put_object(
        Bucket=settings.s3_bucket_name, Key=key, Body=contents, ContentType=content_type
    )

def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )

def delete_file(key: str):
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)
