from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .core.database import Base, engine
from .core.exceptions import ErrorAplicacion


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Biblioteca", lifespan=lifespan)


@app.exception_handler(ErrorAplicacion)
async def error_aplicacion_handler(
    _: Request, exc: ErrorAplicacion
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.mensaje},
    )
