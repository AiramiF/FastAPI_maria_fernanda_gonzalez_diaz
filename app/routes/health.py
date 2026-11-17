from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..core.database import SessionLocal

router = APIRouter(tags=["Infraestructura"])


@router.get("/health", summary="Estado de salud de la API")
async def health_check() -> JSONResponse:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "ok", "database": "error"})
