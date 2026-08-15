from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    app_env: Literal["dev","prod", "test"]
    resend_api_key: str
    sender_email: str
    app_url:str
    s3_bucket_name: str 
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str

settings = Settings() # type: ignore