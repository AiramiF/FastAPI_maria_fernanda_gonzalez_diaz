from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Annotated, Any

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer

from .exceptions import CuentaBloqueada, NoAutenticado, Prohibido
from .mongodb import Repository
from .security import SecurityService, normalizar_utc


def get_repository(request: Request) -> Repository:
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise RuntimeError("El repositorio no fue inicializado")
    return repository


RepositoryDep = Annotated[Repository, Depends(get_repository)]


def pagination(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> tuple[int, int]:
    return skip, limit


PaginationDep = Annotated[tuple[int, int], Depends(pagination)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: RepositoryDep,
) -> Any:
    try:
        payload = SecurityService.decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise NoAutenticado("Credenciales inválidas") from exc

    if payload.get("type") != "access":
        raise NoAutenticado("Credenciales inválidas")

    user = db.get("usuarios", int(payload["sub"]))
    if user is None:
        raise NoAutenticado("Credenciales inválidas")
    if not user["activo"]:
        raise Prohibido("Usuario inactivo")

    blocked_until = normalizar_utc(user.get("bloqueado_hasta"))
    if blocked_until and blocked_until > datetime.now(timezone.utc):
        raise CuentaBloqueada("Cuenta bloqueada temporalmente")
    return SimpleNamespace(**user)


CurrentUser = Annotated[Any, Depends(get_current_user)]
Staff = ("admin", "bibliotecario")


def require_rol(*roles: str):
    allowed = {role.lower() for role in roles}

    def dependency(user: CurrentUser) -> Any:
        if user.rol.lower() not in allowed:
            raise Prohibido("No tiene permisos para esta operación")
        return user

    return dependency


AdminUser = Annotated[Any, Depends(require_rol("admin"))]
StaffUser = Annotated[Any, Depends(require_rol(*Staff))]
SocioUser = Annotated[Any, Depends(require_rol("socio"))]
