from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    db_name: str = "access_agent"
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_request_channel: str = "access-requests"
    slack_approvals_channel: str = "access-approvals"
    fireworks_api_key: str = ""
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"

    model_config = {"env_file": ".env"}


settings = Settings()
