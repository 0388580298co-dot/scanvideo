from fastapi import FastAPI

from apps.api.routes.dashboard import router as dashboard_router
from apps.api.routes.jobs import router as jobs_router
from apps.api.routes.schedule import router as schedule_router

app = FastAPI(
    title="ScanVideo API",
    version="0.3.0",
    description="AI-first short-video localization and publishing platform",
)

app.include_router(jobs_router)
app.include_router(schedule_router)
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "scanvideo-api"}


@app.get("/api/v1")
def api_info() -> dict[str, str]:
    return {"name": "ScanVideo", "version": "0.3.0", "status": "pipeline-ready"}
