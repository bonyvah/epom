from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db, DBSession

app = FastAPI(title="Epom")


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness(db:DBSession):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db":"connected"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status":"error", "db":"unavailable"}
        )