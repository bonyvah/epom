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

settings = Settings() # type: ignore