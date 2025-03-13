from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    ECHO_SQL: bool

    class Config:
        env_file = ".env"


settings = Settings()
