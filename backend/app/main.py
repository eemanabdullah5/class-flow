from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts."""
    create_tables()
    yield


app = FastAPI(title="ClassFlow API", lifespan=lifespan)


@app.get("/api/health")
def health_check():
    """Lets us (and tests) confirm the server is running."""
    return {"status": "ok"}
