from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Infraestructura"])


@router.get("/health", summary="Estado de salud de la API")
async def health_check(request: Request) -> JSONResponse:
    repository = request.app.state.repository
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": repository.mode},
    )
