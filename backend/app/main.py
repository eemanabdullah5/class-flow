from fastapi import FastAPI

app = FastAPI(title="ClassFlow API")


@app.get("/api/health")
def health_check():
    """Lets us (and tests) confirm the server is running."""
    return {"status": "ok"}
