from enum import Enum
from typing import NotRequired, TypedDict

from datetime import date, datetime


class RolUsuario(str, Enum):
    admin = "admin"
    bibliotecario = "bibliotecario"
    socio = "socio"


class UsuarioDoc(TypedDict):
    id: int
    email: str
    nombre: str
    password_hash: str
    rol: str
    activo: bool
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    socio_id: int | None
    creado_en: datetime


class RefreshTokenDoc(TypedDict):
    id: int
    jti: str
    usuario_id: int
    expira_en: datetime
    revocado: bool
    creado_en: datetime


class AutorDoc(TypedDict):
    id: int
    nombre: str
    nacionalidad: str | None
    anio_nacimiento: int | None


class CategoriaDoc(TypedDict):
    id: int
    nombre: str
    descripcion: str | None


class LibroDoc(TypedDict):
    id: int
    titulo: str
    isbn: str
    anio_publicacion: int
    ejemplares: int
    autor_id: int
    categoria_ids: list[int]
    portada_url: str | None
    portada_public_id: NotRequired[str | None]


class SocioDoc(TypedDict):
    id: int
    nombre: str
    email: str
    telefono: str | None
    activo: bool
    fecha_alta: datetime
    usuario_id: int | None


class PrestamoDoc(TypedDict):
    id: int
    libro_id: int
    socio_id: int
    fecha_prestamo: date
    fecha_limite: date
    fecha_devolucion: date | None
    multa: str
    multa_pagada: bool
    registrado_por_id: int | None


class MultaDoc(TypedDict):
    id: int
    prestamo_id: int
    socio_id: int
    monto: str
    pagada: bool
    fecha_creada: date
    fecha_pago: date | None


__all__ = [
    "AutorDoc",
    "CategoriaDoc",
    "LibroDoc",
    "MultaDoc",
    "PrestamoDoc",
    "RefreshTokenDoc",
    "RolUsuario",
    "SocioDoc",
    "UsuarioDoc",
]
