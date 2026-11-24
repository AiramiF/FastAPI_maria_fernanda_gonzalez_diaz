from datetime import date, timedelta

from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import Settings
from app.core import mongodb
from app.core.mongodb import Repository, connect_repository
from app.scripts.seed_demo import seed_demo_users
from conftest import TEST_PASSWORD, login_headers


def test_health_reports_memory_mode(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "simulada"}
    assert response.headers["X-Request-ID"]


def test_test_environment_never_connects_to_atlas() -> None:
    settings = Settings(
        ENVIRONMENT="test",
        MONGODB_URI="mongodb://127.0.0.1:1",
        MONGODB_DATABASE="isolated_test",
        SECRET_KEY="test-only-secret-key-with-at-least-32-chars",
    )
    repository = connect_repository(settings)
    try:
        assert repository.mode == "simulada"
        repository.insert("usuarios", {"email": "only@test.invalid"})
        assert repository.collection("usuarios").count_documents({}) == 1
    finally:
        repository.close()


def test_atlas_connection_failure_falls_back_to_memory(monkeypatch) -> None:
    class UnavailableClient:
        admin = None
        closed = False

        def __init__(self) -> None:
            self.admin = self

        def command(self, _: str) -> None:
            raise ServerSelectionTimeoutError("simulated connection failure")

        def close(self) -> None:
            self.closed = True

    client = UnavailableClient()
    options = {}

    def create_client(_uri: str, *, serverSelectionTimeoutMS: int):
        options["uri"] = _uri
        options["timeout"] = serverSelectionTimeoutMS
        return client

    monkeypatch.setattr(mongodb, "MongoClient", create_client)
    settings = Settings(
        ENVIRONMENT="dev",
        MONGODB_URI="mongodb://unavailable.invalid",
        MONGODB_DATABASE="fallback_test",
        SECRET_KEY="test-only-secret-key-with-at-least-32-chars",
    )
    repository = connect_repository(settings)
    try:
        assert repository.mode == "simulada"
        assert options["timeout"] == 3000
        assert client.closed
    finally:
        repository.close()


def test_demo_users_can_login_in_the_simulated_repository(
    client: TestClient, repository: Repository
) -> None:
    seed_demo_users(repository)
    for email in ("admin@biblioteca.com", "socio@biblioteca.com"):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "Biblioteca2026"},
        )
        assert response.status_code == 200


def test_registration_login_profile_and_refresh_rotation(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/registro",
        json={
            "email": "Ana@Example.com",
            "nombre": "ana ejemplo",
            "telefono": "5551234",
            "password": TEST_PASSWORD,
            "confirmar_password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "ana@example.com"
    assert response.json()["rol"] == "socio"
    assert client.post(
        "/api/v1/auth/registro",
        json={
            "email": "ana@example.com",
            "nombre": "Ana Ejemplo",
            "password": TEST_PASSWORD,
            "confirmar_password": TEST_PASSWORD,
        },
    ).status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == "ana@example.com"

    refresh_headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    rotated = client.post("/api/v1/auth/refresh", headers=refresh_headers)
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert client.post("/api/v1/auth/refresh", headers=refresh_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {rotated.json()['refresh_token']}"},
    ).status_code == 401


def test_logout_revokes_refresh_token(
    client: TestClient, socio: dict
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": socio["email"], "password": TEST_PASSWORD},
    ).json()
    assert client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    ).status_code == 204
    assert client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {login['refresh_token']}"},
    ).status_code == 401


def test_catalog_is_public_and_mutations_are_staff_only(
    client: TestClient,
    repository: Repository,
    admin: dict,
    socio: dict,
) -> None:
    assert client.get("/api/v1/libros").status_code == 200
    payload = {"nombre": "Nuevo Autor", "nacionalidad": "Colombia"}
    assert client.post("/api/v1/autores", json=payload).status_code == 401
    socio_headers = login_headers(client, socio["email"])
    assert client.post(
        "/api/v1/autores", json=payload, headers=socio_headers
    ).status_code == 403

    admin_headers = login_headers(client, admin["email"])
    response = client.post("/api/v1/autores", json=payload, headers=admin_headers)
    assert response.status_code == 201
    assert client.get("/api/v1/autores").json()["total"] == 1
    assert repository.collection("autores").count_documents({}) == 1


def test_loans_fines_and_reports(
    client: TestClient,
    repository: Repository,
    bibliotecario: dict,
    socio: dict,
    catalog: tuple[dict, dict, dict],
) -> None:
    _, _, book = catalog
    staff_headers = login_headers(client, bibliotecario["email"])
    member_headers = login_headers(client, socio["email"])
    start = date.today() - timedelta(days=20)
    created = client.post(
        "/api/v1/prestamos",
        json={
            "libro_id": book["id"],
            "socio_id": socio["socio_id"],
            "fecha_prestamo": start.isoformat(),
            "dias": 14,
        },
        headers=staff_headers,
    )
    assert created.status_code == 201
    loan_id = created.json()["id"]

    returned = client.post(
        f"/api/v1/prestamos/{loan_id}/devolucion", headers=staff_headers
    )
    assert returned.status_code == 200
    assert returned.json()["multa"] == "3.00"
    fines = client.get("/api/v1/socios/me/multas", headers=member_headers)
    assert fines.status_code == 200
    assert fines.json()["total"] == 1
    another_book = repository.insert(
        "libros",
        {
            "titulo": "Libro Dos",
            "isbn": "2222222222222",
            "anio_publicacion": 2021,
            "ejemplares": 1,
            "autor_id": catalog[0]["id"],
            "categoria_ids": [catalog[1]["id"]],
            "portada_url": None,
            "portada_public_id": None,
        },
    )
    blocked_loan = client.post(
        "/api/v1/prestamos",
        json={"libro_id": another_book["id"], "socio_id": socio["socio_id"]},
        headers=staff_headers,
    )
    assert blocked_loan.status_code == 422

    paid = client.post(
        f"/api/v1/prestamos/{loan_id}/pago-multa", headers=staff_headers
    )
    assert paid.status_code == 200
    assert paid.json()["multa_pagada"] is True
    assert repository.collection("multas").find_one({"prestamo_id": loan_id})[
        "pagada"
    ]

    summary = client.get("/api/v1/reportes/resumen", headers=staff_headers)
    assert summary.status_code == 200
    assert summary.json()["total_libros"] == 2


def test_admin_cannot_remove_the_last_active_admin(
    client: TestClient, admin: dict
) -> None:
    headers = login_headers(client, admin["email"])
    response = client.patch(
        f"/api/v1/usuarios/{admin['id']}/activo",
        json={"activo": False},
        headers=headers,
    )
    assert response.status_code == 422


def test_five_failed_logins_temporarily_lock_account(
    client: TestClient, socio: dict
) -> None:
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": socio["email"], "password": "Incorrecta123"},
        )
        assert response.status_code == 401
    locked = client.post(
        "/api/v1/auth/login",
        data={"username": socio["email"], "password": TEST_PASSWORD},
    )
    assert locked.status_code == 423
