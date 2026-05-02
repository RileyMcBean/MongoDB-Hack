from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    db_name: str = "access_agent"
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_request_channel: str = "access-requests"
    slack_approvals_channel: str = "access-approvals"

    model_config = {"env_file": ".env"}


settings = Settings()
