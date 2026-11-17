import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,64}$")


class UsuarioRegistro(BaseModel):
    email: EmailStr = Field(max_length=150)
    nombre: str = Field(min_length=3, max_length=100)
    telefono: str | None = Field(default=None, min_length=7, max_length=15)
    password: str = Field(min_length=8, max_length=64)
    confirmar_password: str = Field(min_length=8, max_length=64)

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        nombre = value.strip()
        if not nombre:
            raise ValueError("El nombre no puede estar vacío")
        return nombre.title()

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not 7 <= len(value) <= 15 or any(character not in "0123456789 +" for character in value):
                raise ValueError("El teléfono debe tener 7-15 dígitos, espacios o +")
        return value

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not PASSWORD_REGEX.match(value):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y número")
        return value

    @model_validator(mode="after")
    def validar_confirmacion(self) -> "UsuarioRegistro":
        if self.password != self.confirmar_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str
    rol: str
    activo: bool
    socio_id: int | None = None
    creado_en: datetime


class UsuarioAdminCreate(BaseModel):
    email: EmailStr = Field(max_length=150)
    nombre: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=64)
    rol: str = Field(default="bibliotecario")

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        nombre = value.strip()
        if not nombre:
            raise ValueError("El nombre no puede estar vacío")
        return nombre.title()

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not PASSWORD_REGEX.match(value):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y número")
        return value

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, value: str) -> str:
        rol = value.strip().lower()
        if rol not in {"admin", "bibliotecario"}:
            raise ValueError("El rol debe ser admin o bibliotecario")
        return rol


class UsuarioRolUpdate(BaseModel):
    rol: str

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, value: str) -> str:
        rol = value.strip().lower()
        if rol not in {"admin", "bibliotecario", "socio"}:
            raise ValueError("Rol inválido")
        return rol


class UsuarioActivoUpdate(BaseModel):
    activo: bool
