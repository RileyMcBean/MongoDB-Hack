from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from .database import connect_db, close_db
from .routes import router
from .slack_handler import handler as slack_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Access Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)
