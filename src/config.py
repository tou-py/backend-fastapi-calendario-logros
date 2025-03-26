from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Configuración de la base de datos
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "mydatabase"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"  # Como cadena para compatibilidad con .env

    # Configuración para debug de consultas en BD
    ECHO_SQL: bool = False

    # Configuración de JWT
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Configuración de Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: str = "6379"  # Como cadena para compatibilidad con .env

    # Configuracion de CORS
    ALLOWED_ORIGINS: str
    ALLOWED_METHODS: str
    ALLOWED_HEADERS: str
    ALLOW_CREDENTIALS: bool

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
