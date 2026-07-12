from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import settings
from .database.db import init_db
from .routes import chat, memory, files, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Nexus", lifespan=lifespan)

# FastAPI CORSMiddleware does not allow wildcard "*" origins if allow_credentials is True.
# If "*" is in the origins list, we must set allow_credentials to False to avoid a startup crash.
allow_all_origins = "*" in settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "Running", "application": "AI Nexus"}


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(files.router)
