from fastapi import APIRouter, status

from ..controllers import usuario as usuario_controller
from ..core.dependencies import AdminUser, PaginationDep, SessionDep
from ..schemas.pagina import Pagina
from ..schemas.usuario import (
    UsuarioActivoUpdate,
    UsuarioAdminCreate,
    UsuarioRespuesta,
    UsuarioRolUpdate,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=Pagina[UsuarioRespuesta])
def listar(
    db: SessionDep,
    paginacion: PaginationDep,
    _: AdminUser,
    rol: str | None = None,
    activo: bool | None = None,
) -> Pagina[UsuarioRespuesta]:
    skip, limit = paginacion
    usuarios = usuario_controller.listar_usuarios(db, skip, limit, rol, activo)
    return Pagina[
        UsuarioRespuesta
    ](
        items=[UsuarioRespuesta.model_validate(usuario) for usuario in usuarios.items],
        total=usuarios.total,
        skip=usuarios.skip,
        limit=usuarios.limit,
    )


@router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear(
    datos: UsuarioAdminCreate,
    db: SessionDep,
    _: AdminUser,
) -> UsuarioRespuesta:
    usuario = usuario_controller.crear_usuario_admin(db, datos)
    return UsuarioRespuesta.model_validate(usuario)


@router.patch("/{usuario_id}/rol", response_model=UsuarioRespuesta)
def actualizar_rol(
    usuario_id: int,
    datos: UsuarioRolUpdate,
    db: SessionDep,
    usuario_actual: AdminUser,
) -> UsuarioRespuesta:
    usuario = usuario_controller.actualizar_rol_usuario(
        db, usuario_id, datos, usuario_actual
    )
    return UsuarioRespuesta.model_validate(usuario)


@router.patch("/{usuario_id}/activo", response_model=UsuarioRespuesta)
def actualizar_activo(
    usuario_id: int,
    datos: UsuarioActivoUpdate,
    db: SessionDep,
    usuario_actual: AdminUser,
) -> UsuarioRespuesta:
    usuario = usuario_controller.actualizar_activo_usuario(
        db, usuario_id, datos, usuario_actual
    )
    return UsuarioRespuesta.model_validate(usuario)
