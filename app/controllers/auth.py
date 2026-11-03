from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.exceptions import Conflicto, CuentaBloqueada, NoAutenticado, Prohibido
from ..core.security import SecurityService, normalizar_utc
from ..models.refresh_token import RefreshToken
from ..models.socio import Socio
from ..models.usuario import RolUsuario, Usuario
from ..schemas.auth import PasswordCambio, TokenPair
from ..schemas.usuario import UsuarioRegistro, UsuarioRespuesta


def registrar_usuario(db: Session, datos: UsuarioRegistro) -> UsuarioRespuesta:
    email = datos.email.strip().lower()
    existe_email_usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()
    existe_email_socio = db.query(Socio).filter(func.lower(Socio.email) == email).first()

    if existe_email_usuario is not None or existe_email_socio is not None:
        raise Conflicto("El correo ya está registrado")

    nombre = datos.nombre.strip().title()
    telefono = datos.telefono.strip() if datos.telefono else None

    socio = Socio(
        nombre=nombre,
        email=email,
        telefono=telefono,
    )
    usuario = Usuario(
        email=email,
        nombre=nombre,
        password_hash=SecurityService.hash_password(datos.password),
        rol=RolUsuario.socio,
        activo=True,
        socio=socio,
    )
    db.add(socio)
    db.add(usuario)
    db.flush()
    db.commit()

    return UsuarioRespuesta(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        rol=usuario.rol.value,
        activo=usuario.activo,
        socio_id=usuario.socio_id,
        creado_en=usuario.creado_en,
    )


def _crear_par_tokens(db: Session, usuario: Usuario) -> TokenPair:
    access_token, access_exp, access_jti = SecurityService.create_token(usuario.id, usuario.rol.value, "access")
    refresh_token, refresh_exp, refresh_jti = SecurityService.create_token(usuario.id, usuario.rol.value, "refresh")

    db.add(
        RefreshToken(
            jti=refresh_jti,
            usuario_id=usuario.id,
            expira_en=refresh_exp,
        )
    )
    db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int((access_exp - datetime.now(timezone.utc)).total_seconds()),
    )


def login_usuario(db: Session, email: str, password: str) -> TokenPair:
    usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email.strip().lower()).first()
    ahora = datetime.now(timezone.utc)

    if usuario is None:
        raise NoAutenticado("Credenciales inválidas")

    if not usuario.activo:
        raise Prohibido("Usuario inactivo")

    bloqueado_hasta = normalizar_utc(usuario.bloqueado_hasta)
    if bloqueado_hasta is not None and bloqueado_hasta > ahora:
        raise CuentaBloqueada("Cuenta bloqueada temporalmente")

    if not SecurityService.verify_password(password, usuario.password_hash):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
        db.commit()
        raise NoAutenticado("Credenciales inválidas")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()
    return _crear_par_tokens(db, usuario)


def refresh_usuario(db: Session, token: str) -> TokenPair:
    try:
        payload = SecurityService.decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise NoAutenticado("Credenciales inválidas") from exc

    if payload.get("type") != "refresh":
        raise NoAutenticado("Credenciales inválidas")

    refresh_record = db.query(RefreshToken).filter_by(jti=payload["jti"]).first()
    now = datetime.now(timezone.utc)
    expira_en = normalizar_utc(refresh_record.expira_en) if refresh_record is not None else None
    if refresh_record is None or refresh_record.revocado or (expira_en is not None and expira_en <= now):
        if refresh_record is not None and refresh_record.revocado:
            db.query(RefreshToken).filter_by(usuario_id=refresh_record.usuario_id).update({"revocado": True})
            db.commit()
        raise NoAutenticado("Credenciales inválidas")

    refresh_record.revocado = True
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None:
        raise NoAutenticado("Credenciales inválidas")

    db.query(RefreshToken).filter(RefreshToken.usuario_id == usuario.id, RefreshToken.revocado.is_(False)).update({"revocado": True})
    db.commit()

    if not usuario.activo:
        raise Prohibido("Usuario inactivo")

    nuevo = _crear_par_tokens(db, usuario)
    return nuevo


def logout_usuario(db: Session, usuario: Usuario) -> None:
    db.query(RefreshToken).filter(RefreshToken.usuario_id == usuario.id).update({"revocado": True})
    db.commit()


def obtener_mi_perfil(usuario: Usuario) -> UsuarioRespuesta:
    return UsuarioRespuesta(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        rol=usuario.rol.value,
        activo=usuario.activo,
        socio_id=usuario.socio_id,
        creado_en=usuario.creado_en,
    )


def cambiar_password(db: Session, usuario: Usuario, datos: PasswordCambio) -> None:
    if datos.new_password != datos.confirm_password:
        raise NoAutenticado("Credenciales inválidas")

    if not SecurityService.verify_password(datos.current_password, usuario.password_hash):
        raise NoAutenticado("Credenciales inválidas")

    usuario.password_hash = SecurityService.hash_password(datos.new_password)
    db.query(RefreshToken).filter(RefreshToken.usuario_id == usuario.id).update({"revocado": True})
    db.commit()
