from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )
    APP_NAME: str = "Simple Social"
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False
    LOG_NAME: str = "{APP_NAME}.app_logs"
    LOG_ACCESS_NAME: str = "{APP_NAME}.access_logs"


    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    DEBUG: bool = False

    SECRET_KEY: str = "djd232df34kdjfiejwinccdknslejdjf"
    COOKIE_MAX_AGE: int = 3600 * 24 * 7  # 7 days

    #s3 compatibible object storage
    REGION_NAME: str = ""
    BUCKET_NAME: str = ""
    ENDPOINT_URL: str | None = None
    ACCESS_KEY_ID: str | None = None
    SECRET_ACCESS_KEY: str | None = None
    
    PUBLIC_URL: str | None = None
    


settings = Settings()