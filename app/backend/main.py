from fastapi import FastAPI

try:
    from app.backend.api import router as api_router
except ModuleNotFoundError:
    from api import router as api_router

app = FastAPI(title="Sofadata API", version="0.1.0")
app.include_router(api_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
