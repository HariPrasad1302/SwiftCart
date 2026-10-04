from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "dev"
    secret_key: str
    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()