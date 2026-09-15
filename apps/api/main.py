from fastapi import FastAPI

app = FastAPI(
    title="ScanVideo API",
    version="0.1.0",
    description="AI-first short-video localization and publishing platform",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "scanvideo-api"}


@app.get("/api/v1")
def api_info() -> dict[str, str]:
    return {
        "name": "ScanVideo",
        "version": "0.1.0",
        "status": "foundation",
    }
