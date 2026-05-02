import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from .database import connect_db, close_db, get_db
from .routes import router
from .slack_handler import handler as slack_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    # Set Fireworks key in environment so LangChain picks it up
    from .config import settings
    if settings.fireworks_api_key:
        os.environ.setdefault("FIREWORKS_API_KEY", settings.fireworks_api_key)
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
    # Start change stream watchers for self-learning memory
    from .agents.watcher import start_watchers
    await start_watchers(get_db())
    yield
    await close_db()


app = FastAPI(title="Access Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)
