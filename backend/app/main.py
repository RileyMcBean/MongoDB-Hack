from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import connect_db, close_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Access Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)
