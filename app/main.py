import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from . import models
from .core.config import get_settings
from .core.exceptions import (
    CuentaBloqueada,
    ErrorAplicacion,
    NoAutenticado,
    Prohibido,
)
from .core.rate_limit import limiter
from .routes import (
    auth,
    autores,
    categorias,
    health,
    libros,
    prestamos,
    reportes,
    socios,
    usuario,
)

settings = get_settings()
logger = logging.getLogger("biblioteca.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Biblioteca",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "prod" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "prod" else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(autores.router, prefix="/api/v1")
app.include_router(categorias.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(libros.router, prefix="/api/v1")
app.include_router(socios.router, prefix="/api/v1")
app.include_router(prestamos.router, prefix="/api/v1")
app.include_router(usuario.router, prefix="/api/v1")
app.include_router(reportes.router, prefix="/api/v1")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    inicio = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - inicio) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s %s %s ms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(NoAutenticado)
async def no_autenticado_handler(_: Request, exc: NoAutenticado) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        content={"detail": exc.mensaje},
    )


@app.exception_handler(Prohibido)
async def prohibido_handler(_: Request, exc: Prohibido) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": exc.mensaje})


@app.exception_handler(CuentaBloqueada)
async def cuenta_bloqueada_handler(_: Request, exc: CuentaBloqueada) -> JSONResponse:
    return JSONResponse(status_code=423, content={"detail": exc.mensaje})


@app.exception_handler(ErrorAplicacion)
async def error_aplicacion_handler(
    _: Request, exc: ErrorAplicacion
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.mensaje},
    )


@app.exception_handler(Exception)
async def exception_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
