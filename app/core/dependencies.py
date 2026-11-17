from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

from .database import SessionLocal
from .exceptions import CuentaBloqueada, NoAutenticado, Prohibido
from .security import SecurityService, normalizar_utc


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]


def pagination(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> tuple[int, int]:
    return skip, limit


PaginationDep = Annotated[tuple[int, int], Depends(pagination)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: SessionDep,
) -> Usuario:
    try:
        payload = SecurityService.decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise NoAutenticado("Credenciales inválidas") from exc

    if payload.get("type") != "access":
        raise NoAutenticado("Credenciales inválidas")

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None:
        raise NoAutenticado("Credenciales inválidas")

    if not usuario.activo:
        raise Prohibido("Usuario inactivo")

    bloqueado_hasta = normalizar_utc(usuario.bloqueado_hasta)
    if bloqueado_hasta and bloqueado_hasta > datetime.now(timezone.utc):
        raise CuentaBloqueada("Cuenta bloqueada temporalmente")

    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]
Staff = ("admin", "bibliotecario")


def require_rol(*roles: str):
    allowed = {rol.lower() for rol in roles}

    def _dependencia(usuario: CurrentUser) -> Usuario:
        if usuario.rol.value.lower() not in allowed:
            raise Prohibido("No tiene permisos para esta operación")
        return usuario

    return _dependencia


AdminUser = Annotated[Usuario, Depends(require_rol("admin"))]
StaffUser = Annotated[Usuario, Depends(require_rol(*Staff))]
SocioUser = Annotated[Usuario, Depends(require_rol("socio"))]
