import os
from collections.abc import Generator
from datetime import datetime, timezone

import mongomock
import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-chars"

from app.core.dependencies import get_repository
from app.core.mongodb import Repository
from app.core.rate_limit import limiter
from app.core.security import SecurityService
from app.main import app

TEST_PASSWORD = "TallerTest123!"


@pytest.fixture(scope="session")
def repository() -> Generator[Repository, None, None]:
    client = mongomock.MongoClient()
    repo = Repository(client, client["biblioteca_test"], "simulada")
    yield repo
    repo.close()


@pytest.fixture(autouse=True)
def reset_repository(repository: Repository) -> None:
    repository.reset()
    limiter.reset()


@pytest.fixture()
def client(repository: Repository) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def create_user(
    repository: Repository,
    role: str,
    *,
    name: str,
    email: str | None = None,
) -> dict:
    email = email or f"{role}@example.com"
    member = None
    if role == "socio":
        member = repository.insert(
            "socios",
            {
                "nombre": name,
                "email": email,
                "telefono": "5551234",
                "activo": True,
                "fecha_alta": datetime.now(timezone.utc),
                "usuario_id": None,
            },
        )
    user = repository.insert(
        "usuarios",
        {
            "email": email,
            "nombre": name,
            "password_hash": SecurityService.hash_password(TEST_PASSWORD),
            "rol": role,
            "activo": True,
            "intentos_fallidos": 0,
            "bloqueado_hasta": None,
            "socio_id": member["id"] if member else None,
            "creado_en": datetime.now(timezone.utc),
        },
    )
    if member:
        repository.update("socios", member["id"], {"usuario_id": user["id"]})
    return user


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin(repository: Repository) -> dict:
    return create_user(repository, "admin", name="Admin")


@pytest.fixture()
def bibliotecario(repository: Repository) -> dict:
    return create_user(repository, "bibliotecario", name="Bibliotecario")


@pytest.fixture()
def socio(repository: Repository) -> dict:
    return create_user(
        repository, "socio", name="Ana", email="ana@example.com"
    )


@pytest.fixture()
def catalog(repository: Repository) -> tuple[dict, dict, dict]:
    author = repository.insert(
        "autores",
        {"nombre": "Autora De Prueba", "nacionalidad": None, "anio_nacimiento": None},
    )
    category = repository.insert(
        "categorias", {"nombre": "pruebas", "descripcion": None}
    )
    book = repository.insert(
        "libros",
        {
            "titulo": "Libro Uno",
            "isbn": "1111111111111",
            "anio_publicacion": 2020,
            "ejemplares": 3,
            "autor_id": author["id"],
            "categoria_ids": [category["id"]],
            "portada_url": None,
            "portada_public_id": None,
        },
    )
    return author, category, book
