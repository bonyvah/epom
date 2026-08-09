import boto3
from app.config import settings

s3 = boto3.client('s3')

def upload_file(key:str, file) -> dict:
    return s3.put_object(Bucket=settings.s3_bucket_name, Key=key, Body=file)

def fetch_file(key:str):
    with open ("filename","wb") as data:
        s3.download_fileobj(settings.s3_bucket_name, key, data)
    print(data)
    return data

def delete_file(key:str) -> bool:
    return s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)['DeleteMarker']
