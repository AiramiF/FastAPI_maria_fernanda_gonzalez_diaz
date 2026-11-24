from io import BytesIO
from typing import Any

import cloudinary
from cloudinary import uploader

from .config import get_settings
from .exceptions import ServicioExternoError


def _configurar() -> None:
    settings = get_settings()
    if not all(
        (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    ):
        raise ServicioExternoError("El servicio de portadas no está configurado")

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def subir_portada(contenido: bytes) -> tuple[str, str]:
    try:
        _configurar()
        resultado: dict[str, Any] = uploader.upload(
            BytesIO(contenido),
            folder="biblioteca/portadas",
        )
    except Exception as exc:
        raise ServicioExternoError("No fue posible subir la portada") from exc

    if not isinstance(resultado, dict):
        raise ServicioExternoError("No fue posible subir la portada")
    url = resultado.get("secure_url")
    public_id = resultado.get("public_id")
    if not isinstance(url, str) or not isinstance(public_id, str):
        raise ServicioExternoError("No fue posible subir la portada")
    return url, public_id


def eliminar_portada(public_id: str) -> None:
    try:
        _configurar()
        resultado = uploader.destroy(public_id, invalidate=True)
    except Exception as exc:
        raise ServicioExternoError("No fue posible eliminar la portada") from exc

    if not isinstance(resultado, dict) or resultado.get("result") not in {
        "ok",
        "not found",
    }:
        raise ServicioExternoError("No fue posible eliminar la portada")
