from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    db_name: str = "access_agent"

    model_config = {"env_file": ".env"}


settings = Settings()
