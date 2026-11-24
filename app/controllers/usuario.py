from datetime import datetime, timezone

from ..core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from ..core.mongodb import Repository
from ..core.security import SecurityService
from ..schemas.pagina import Pagina
from ..schemas.usuario import UsuarioAdminCreate, UsuarioActivoUpdate, UsuarioRolUpdate


def listar_usuarios(
    db: Repository,
    skip: int,
    limit: int,
    rol: str | None = None,
    activo: bool | None = None,
) -> Pagina:
    query = {}
    if rol is not None and rol.strip().lower() in {"admin", "bibliotecario", "socio"}:
        query["rol"] = rol.strip().lower()
    if activo is not None:
        query["activo"] = activo
    collection = db.collection("usuarios")
    items = list(collection.find(query, {"_id": 0, "password_hash": 0}).sort("id", 1))
    total = collection.count_documents(query)
    return Pagina(items=items[skip : skip + limit], total=total, skip=skip, limit=limit)


def crear_usuario_admin(db: Repository, datos: UsuarioAdminCreate) -> dict:
    email = datos.email.strip().lower()
    if db.collection("usuarios").find_one({"email": email}):
        raise Conflicto("El correo ya está registrado")
    return db.insert(
        "usuarios",
        {
            "email": email,
            "nombre": datos.nombre.strip().title(),
            "password_hash": SecurityService.hash_password(datos.password),
            "rol": datos.rol,
            "activo": True,
            "intentos_fallidos": 0,
            "bloqueado_hasta": None,
            "socio_id": None,
            "creado_en": datetime.now(timezone.utc),
        },
    )


def _obtener_usuario(db: Repository, usuario_id: int) -> dict:
    user = db.get("usuarios", usuario_id)
    if user is None:
        raise NoEncontrado("Usuario no encontrado")
    return user


def _asegurar_admin_activo(db: Repository, user: dict, nuevo_rol: str, activo: bool) -> None:
    if user["rol"] != "admin" or not user["activo"]:
        return
    if nuevo_rol == "admin" and activo:
        return
    if db.collection("usuarios").count_documents({"rol": "admin", "activo": True}) <= 1:
        raise ReglaNegocio("Debe mantenerse al menos un administrador activo")


def actualizar_rol_usuario(
    db: Repository, usuario_id: int, datos: UsuarioRolUpdate
) -> dict:
    user = _obtener_usuario(db, usuario_id)
    _asegurar_admin_activo(db, user, datos.rol, user["activo"])
    updated = db.update("usuarios", usuario_id, {"rol": datos.rol})
    db.collection("refresh_tokens").update_many(
        {"usuario_id": usuario_id}, {"$set": {"revocado": True}}
    )
    return updated or _obtener_usuario(db, usuario_id)


def actualizar_activo_usuario(
    db: Repository, usuario_id: int, datos: UsuarioActivoUpdate
) -> dict:
    user = _obtener_usuario(db, usuario_id)
    _asegurar_admin_activo(db, user, user["rol"], datos.activo)
    updated = db.update("usuarios", usuario_id, {"activo": datos.activo})
    db.collection("refresh_tokens").update_many(
        {"usuario_id": usuario_id}, {"$set": {"revocado": True}}
    )
    return updated or _obtener_usuario(db, usuario_id)
