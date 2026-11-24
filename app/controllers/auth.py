from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from ..core.exceptions import Conflicto, CuentaBloqueada, NoAutenticado, Prohibido
from ..core.mongodb import Repository
from ..core.security import SecurityService, normalizar_utc
from ..schemas.auth import PasswordCambio, TokenPair
from ..schemas.usuario import UsuarioRegistro, UsuarioRespuesta


def _respuesta_usuario(user: dict) -> UsuarioRespuesta:
    return UsuarioRespuesta(
        id=user["id"],
        email=user["email"],
        nombre=user["nombre"],
        rol=user["rol"],
        activo=user["activo"],
        socio_id=user.get("socio_id"),
        creado_en=user["creado_en"],
    )


def registrar_usuario(db: Repository, datos: UsuarioRegistro) -> UsuarioRespuesta:
    email = datos.email.strip().lower()
    if db.collection("usuarios").find_one({"email": email}) or db.collection(
        "socios"
    ).find_one({"email": email}):
        raise Conflicto("El correo ya está registrado")

    nombre = datos.nombre.strip().title()
    socio = db.insert(
        "socios",
        {
            "nombre": nombre,
            "email": email,
            "telefono": datos.telefono.strip() if datos.telefono else None,
            "activo": True,
            "fecha_alta": datetime.now(timezone.utc),
            "usuario_id": None,
        },
    )
    user = db.insert(
        "usuarios",
        {
            "email": email,
            "nombre": nombre,
            "password_hash": SecurityService.hash_password(datos.password),
            "rol": "socio",
            "activo": True,
            "intentos_fallidos": 0,
            "bloqueado_hasta": None,
            "socio_id": socio["id"],
            "creado_en": datetime.now(timezone.utc),
        },
    )
    db.update("socios", socio["id"], {"usuario_id": user["id"]})
    return _respuesta_usuario(user)


def _crear_par_tokens(db: Repository, user: dict) -> TokenPair:
    access_token, access_exp, _ = SecurityService.create_token(
        user["id"], user["rol"], "access"
    )
    refresh_token, refresh_exp, refresh_jti = SecurityService.create_token(
        user["id"], user["rol"], "refresh"
    )
    db.insert(
        "refresh_tokens",
        {
            "jti": refresh_jti,
            "usuario_id": user["id"],
            "expira_en": refresh_exp,
            "revocado": False,
            "creado_en": datetime.now(timezone.utc),
        },
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_exp - datetime.now(timezone.utc)).total_seconds()),
    )


def login_usuario(db: Repository, email: str, password: str) -> TokenPair:
    user = db.collection("usuarios").find_one(
        {"email": email.strip().lower()}, {"_id": 0}
    )
    now = datetime.now(timezone.utc)
    if user is None:
        raise NoAutenticado("Credenciales inválidas")
    if not user["activo"]:
        raise Prohibido("Usuario inactivo")

    blocked_until = normalizar_utc(user.get("bloqueado_hasta"))
    if blocked_until is not None and blocked_until > now:
        raise CuentaBloqueada("Cuenta bloqueada temporalmente")

    if not SecurityService.verify_password(password, user["password_hash"]):
        attempts = user.get("intentos_fallidos", 0) + 1
        blocked_until = now + timedelta(minutes=15) if attempts >= 5 else None
        db.update(
            "usuarios",
            user["id"],
            {"intentos_fallidos": attempts, "bloqueado_hasta": blocked_until},
        )
        raise NoAutenticado("Credenciales inválidas")

    db.update(
        "usuarios",
        user["id"],
        {"intentos_fallidos": 0, "bloqueado_hasta": None},
    )
    return _crear_par_tokens(db, user)


def refresh_usuario(db: Repository, token: str) -> TokenPair:
    try:
        payload = SecurityService.decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise NoAutenticado("Credenciales inválidas") from exc
    if payload.get("type") != "refresh":
        raise NoAutenticado("Credenciales inválidas")

    record = db.collection("refresh_tokens").find_one(
        {"jti": payload["jti"]}, {"_id": 0}
    )
    now = datetime.now(timezone.utc)
    expires_at = normalizar_utc(record.get("expira_en")) if record else None
    if record is None or record["revocado"] or (expires_at and expires_at <= now):
        if record is not None and record["revocado"]:
            db.collection("refresh_tokens").update_many(
                {"usuario_id": record["usuario_id"]}, {"$set": {"revocado": True}}
            )
        raise NoAutenticado("Credenciales inválidas")

    db.update("refresh_tokens", record["id"], {"revocado": True})
    user = db.get("usuarios", int(payload["sub"]))
    if user is None:
        raise NoAutenticado("Credenciales inválidas")
    db.collection("refresh_tokens").update_many(
        {"usuario_id": user["id"], "revocado": False},
        {"$set": {"revocado": True}},
    )
    if not user["activo"]:
        raise Prohibido("Usuario inactivo")
    return _crear_par_tokens(db, user)


def logout_usuario(db: Repository, user: SimpleNamespace) -> None:
    db.collection("refresh_tokens").update_many(
        {"usuario_id": user.id}, {"$set": {"revocado": True}}
    )


def obtener_mi_perfil(user: SimpleNamespace) -> UsuarioRespuesta:
    return UsuarioRespuesta(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        rol=user.rol,
        activo=user.activo,
        socio_id=user.socio_id,
        creado_en=user.creado_en,
    )


def cambiar_password(
    db: Repository, user: SimpleNamespace, datos: PasswordCambio
) -> None:
    if datos.new_password != datos.confirm_password:
        raise NoAutenticado("Credenciales inválidas")
    if not SecurityService.verify_password(datos.current_password, user.password_hash):
        raise NoAutenticado("Credenciales inválidas")
    db.update(
        "usuarios",
        user.id,
        {"password_hash": SecurityService.hash_password(datos.new_password)},
    )
    db.collection("refresh_tokens").update_many(
        {"usuario_id": user.id}, {"$set": {"revocado": True}}
    )
