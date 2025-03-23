from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    YANDEX_GEOCODER_API_KEY: str
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/courts"

    class Config:
        env_file = ".env"


settings = Settings()
