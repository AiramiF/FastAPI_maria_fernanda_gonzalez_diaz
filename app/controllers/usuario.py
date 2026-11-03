from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from ..core.security import SecurityService
from ..models.refresh_token import RefreshToken
from ..models.usuario import RolUsuario, Usuario
from ..schemas.pagina import Pagina
from ..schemas.usuario import (
    UsuarioAdminCreate,
    UsuarioActivoUpdate,
    UsuarioRespuesta,
    UsuarioRolUpdate,
)


def listar_usuarios(
    db: Session,
    skip: int,
    limit: int,
    rol: str | None = None,
    activo: bool | None = None,
) -> Pagina[UsuarioRespuesta]:
    statement = select(Usuario)
    if rol is not None:
        rol_normalizado = rol.strip().lower()
        if rol_normalizado in {"admin", "bibliotecario", "socio"}:
            statement = statement.where(Usuario.rol == RolUsuario(rol_normalizado))
    if activo is not None:
        statement = statement.where(Usuario.activo.is_(activo))
    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    items = db.scalars(statement.order_by(Usuario.id).offset(skip).limit(limit)).all()
    return Pagina(items=list(items), total=int(total or 0), skip=skip, limit=limit)


def crear_usuario_admin(db: Session, datos: UsuarioAdminCreate) -> Usuario:
    email = datos.email.strip().lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first() is not None:
        raise Conflicto("El correo ya está registrado")

    usuario = Usuario(
        email=email,
        nombre=datos.nombre.strip().title(),
        password_hash=SecurityService.hash_password(datos.password),
        rol=RolUsuario(datos.rol),
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_rol_usuario(
    db: Session, usuario_id: int, datos: UsuarioRolUpdate, usuario_actual: Usuario
) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")

    nuevo_rol = RolUsuario(datos.rol)
    if (
        usuario.rol == RolUsuario.admin
        and usuario.activo
        and nuevo_rol != RolUsuario.admin
        and db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.rol == RolUsuario.admin,
                Usuario.activo.is_(True),
            )
        )
        <= 1
    ):
        raise ReglaNegocio("Debe mantenerse al menos un administrador activo")

    usuario.rol = nuevo_rol
    db.query(RefreshToken).filter(RefreshToken.usuario_id == usuario.id).update({"revocado": True})
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_activo_usuario(
    db: Session, usuario_id: int, datos: UsuarioActivoUpdate, usuario_actual: Usuario
) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")

    if (
        usuario.rol == RolUsuario.admin
        and usuario.activo
        and not datos.activo
        and db.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.rol == RolUsuario.admin,
                Usuario.activo.is_(True),
            )
        )
        <= 1
    ):
        raise ReglaNegocio("Debe mantenerse al menos un administrador activo")

    usuario.activo = datos.activo
    db.query(RefreshToken).filter(RefreshToken.usuario_id == usuario.id).update({"revocado": True})
    db.commit()
    db.refresh(usuario)
    return usuario
