from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    app_env: str
    resend_api_key: str
    sender_email: str
    app_url:str
    s3_bucket_name: str 
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    file_size_limit_mb:int

settings = Settings() # type: ignore