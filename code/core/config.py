from pathlib import Path

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    DEBUG: bool = False

    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "password_123"
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_DISPLAY_NAME: str = "Admin"

    SECRET_KEY: str = "djd232df34kdjfiejwinccdknslejdjf"
    COOKIE_MAX_AGE: int = 3600 * 24 * 7  # 7 days

    ENABLE_METRICS: bool = True

    POSTGRES_SERVER: str
    POSTGRES_PORT: int | None = None
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # s3 compatibible object storage
    # boto3 get access key and secret access key from env variables
    REGION_NAME: str = ""
    BUCKET_NAME: str = ""
    ENDPOINT_URL: str | None = None
    ACCESS_KEY_ID: str | None = None
    SECRET_ACCESS_KEY: str | None = None

    PUBLIC_URL: str | None = None


settings = Settings()
