from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_tables
from app.routers import assignments, auth, courses, grades, reports, results, submissions, topics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts."""
    create_tables()
    yield


app = FastAPI(title="ClassFlow API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(submissions.router)
app.include_router(grades.router)
app.include_router(topics.router)
app.include_router(results.router)
app.include_router(reports.router)


@app.get("/api/health")
def health_check():
    """Lets us (and tests) confirm the server is running."""
    return {"status": "ok"}
