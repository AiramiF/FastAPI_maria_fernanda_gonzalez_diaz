from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.core import cloudinary as cloudinary_service
from app.models import Libro

JPEG_VALIDO = b"\xff\xd8\xff" + b"contenido de prueba"


@pytest.fixture
def cloudinary_mock(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    subidas: list[dict[str, Any]] = []
    eliminaciones: list[tuple[str, bool]] = []

    def subir(*args: Any, **kwargs: Any) -> dict[str, str]:
        identificador = f"biblioteca/portadas/test-{len(subidas) + 1}"
        subidas.append({"args": args, "kwargs": kwargs})
        return {
            "secure_url": f"https://res.cloudinary.test/{identificador}.jpg",
            "public_id": identificador,
        }

    def eliminar(public_id: str, *, invalidate: bool) -> dict[str, str]:
        eliminaciones.append((public_id, invalidate))
        return {"result": "ok"}

    monkeypatch.setattr(
        cloudinary_service,
        "get_settings",
        lambda: SimpleNamespace(
            CLOUDINARY_CLOUD_NAME="nube-ficticia",
            CLOUDINARY_API_KEY="clave-ficticia",
            CLOUDINARY_API_SECRET="secreto-ficticio",
        ),
    )
    monkeypatch.setattr(cloudinary_service.cloudinary, "config", lambda **_: None)
    monkeypatch.setattr(cloudinary_service.uploader, "upload", subir)
    monkeypatch.setattr(cloudinary_service.uploader, "destroy", eliminar)
    return {"uploads": subidas, "deletions": eliminaciones}


def _upload(
    client: TestClient,
    libro_id: int,
    headers: dict[str, str] | None = None,
    *,
    content: bytes = JPEG_VALIDO,
    content_type: str = "image/jpeg",
) -> Response:
    return client.post(
        f"/api/v1/libros/{libro_id}/portada",
        headers=headers,
        files={"archivo": ("portada.jpg", content, content_type)},
    )


def test_subir_portada_guarda_url_y_public_id(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog

    response = _upload(client, libro.id, bibliotecario_headers)

    assert response.status_code == 200
    assert response.json()["portada_url"] == (
        "https://res.cloudinary.test/biblioteca/portadas/test-1.jpg"
    )
    db_session.refresh(libro)
    assert libro.portada_public_id == "biblioteca/portadas/test-1"
    assert len(cloudinary_mock["uploads"]) == 1
    assert cloudinary_mock["uploads"][0]["kwargs"]["folder"] == "biblioteca/portadas"


def test_reemplazar_portada_elimina_la_anterior(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog
    libro.portada_url = "https://res.cloudinary.test/portada-anterior.jpg"
    libro.portada_public_id = "biblioteca/portadas/anterior"
    db_session.commit()

    response = _upload(client, libro.id, bibliotecario_headers)

    assert response.status_code == 200
    db_session.refresh(libro)
    assert libro.portada_public_id == "biblioteca/portadas/test-1"
    assert cloudinary_mock["deletions"] == [
        ("biblioteca/portadas/anterior", True)
    ]


def test_eliminar_portada_limpia_la_base_y_cloudinary(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog
    libro.portada_url = "https://res.cloudinary.test/portada.jpg"
    libro.portada_public_id = "biblioteca/portadas/portada"
    db_session.commit()

    response = client.delete(
        f"/api/v1/libros/{libro.id}/portada",
        headers=bibliotecario_headers,
    )

    assert response.status_code == 204
    db_session.refresh(libro)
    assert libro.portada_url is None
    assert libro.portada_public_id is None
    assert cloudinary_mock["deletions"] == [
        ("biblioteca/portadas/portada", True)
    ]


def test_rechazar_tipo_de_archivo_invalido(
    client: TestClient,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    response = _upload(
        client,
        catalog[0].id,
        bibliotecario_headers,
        content=b"no es una imagen",
        content_type="text/plain",
    )

    assert response.status_code == 422
    assert cloudinary_mock["uploads"] == []


def test_rechazar_archivo_que_excede_5_mb(
    client: TestClient,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    response = _upload(
        client,
        catalog[0].id,
        bibliotecario_headers,
        content=b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024),
    )

    assert response.status_code == 413
    assert cloudinary_mock["uploads"] == []


def test_rechazar_firma_que_no_coincide_con_el_tipo(
    client: TestClient,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    response = _upload(
        client,
        catalog[0].id,
        bibliotecario_headers,
        content=b"\x89PNG\r\n\x1a\ncontenido",
        content_type="image/jpeg",
    )

    assert response.status_code == 422
    assert cloudinary_mock["uploads"] == []


def test_subir_portada_requiere_token(
    client: TestClient, catalog: tuple[Libro, Libro]
) -> None:
    response = _upload(client, catalog[0].id)

    assert response.status_code == 401


def test_socio_no_puede_administrar_portadas(
    client: TestClient,
    catalog: tuple[Libro, Libro],
    ana_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    response = _upload(client, catalog[0].id, ana_headers)

    assert response.status_code == 403
    assert cloudinary_mock["uploads"] == []


def test_portada_de_libro_inexistente_devuelve_404(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    cloudinary_mock: dict[str, Any],
) -> None:
    response = _upload(client, 999999, bibliotecario_headers)

    assert response.status_code == 404
    assert cloudinary_mock["uploads"] == []


def test_fallo_de_cloudinary_no_cambia_la_base(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog

    def fallar_subida(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("fallo del proveedor")

    monkeypatch.setattr(
        cloudinary_service.uploader,
        "upload",
        fallar_subida,
    )

    response = _upload(client, libro.id, bibliotecario_headers)

    assert response.status_code == 502
    db_session.refresh(libro)
    assert libro.portada_url is None
    assert libro.portada_public_id is None


def test_fallo_de_commit_limpia_la_imagen_subida(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog

    def fallar_commit(_session: Session) -> None:
        raise RuntimeError("fallo de base de datos")

    monkeypatch.setattr(Session, "commit", fallar_commit)

    response = _upload(client, libro.id, bibliotecario_headers)

    assert response.status_code == 500
    assert cloudinary_mock["deletions"] == [
        ("biblioteca/portadas/test-1", True)
    ]
    db_session.refresh(libro)
    assert libro.portada_url is None
    assert libro.portada_public_id is None


def test_fallo_al_eliminar_cloudinary_restaurar_datos(
    client: TestClient,
    db_session: Session,
    catalog: tuple[Libro, Libro],
    bibliotecario_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    cloudinary_mock: dict[str, Any],
) -> None:
    libro, _ = catalog
    libro.portada_url = "https://res.cloudinary.test/portada.jpg"
    libro.portada_public_id = "biblioteca/portadas/portada"
    db_session.commit()

    def fallar_eliminacion(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("fallo del proveedor")

    monkeypatch.setattr(
        cloudinary_service.uploader,
        "destroy",
        fallar_eliminacion,
    )

    response = client.delete(
        f"/api/v1/libros/{libro.id}/portada",
        headers=bibliotecario_headers,
    )

    assert response.status_code == 502
    db_session.refresh(libro)
    assert libro.portada_url == "https://res.cloudinary.test/portada.jpg"
    assert libro.portada_public_id == "biblioteca/portadas/portada"
