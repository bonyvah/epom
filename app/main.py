from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import DBSession

from app.routers import project_router, auth_router, document_router

app = FastAPI(title="Epom")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(document_router)


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness(db: DBSession):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "db": "unavailable"},
        )
