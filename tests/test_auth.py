from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken, Usuario

PASSWORD = "TallerTest123!"


def registration(email: str | None = None) -> dict[str, str]:
    return {
        "email": email or f"ana_{uuid4().hex[:8]}@example.com",
        "nombre": "Ana Aprendiz",
        "password": PASSWORD,
        "confirmar_password": PASSWORD,
    }


def test_registro_password_debil_y_confirmacion_distinta(client: TestClient) -> None:
    payload = registration()
    payload["password"] = "abcdefgh"
    payload["confirmar_password"] = "abcdefgh"
    assert client.post("/api/v1/auth/registro", json=payload).status_code == 422

    payload = registration()
    payload["confirmar_password"] = "OtraClave123"
    assert client.post("/api/v1/auth/registro", json=payload).status_code == 422


def test_registro_valido_y_email_duplicado_case_insensitive(
    client: TestClient,
) -> None:
    payload = registration("ana@example.com")
    response = client.post("/api/v1/auth/registro", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["rol"] == "socio"
    assert data["socio_id"] is not None
    assert "password_hash" not in data

    duplicate = registration("ANA@EXAMPLE.COM")
    assert client.post("/api/v1/auth/registro", json=duplicate).status_code == 409


def test_login_credenciales_invalidas_mismo_mensaje(
    client: TestClient, ana_user: Usuario
) -> None:
    wrong_password = client.post(
        "/api/v1/auth/login",
        data={"username": ana_user.email, "password": "Incorrecta123"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        data={"username": "nadie@example.com", "password": "Incorrecta123"},
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]
    assert wrong_password.json()["detail"] == "Credenciales inválidas"


def test_login_correcto_me_sin_token_y_token_alterado(
    client: TestClient, ana_user: Usuario
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": ana_user.email, "password": PASSWORD},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"

    token = tokens["access_token"]
    head, signature = token.rsplit(".", 1)
    changed = ("A" if signature[0] != "A" else "B") + signature[1:]
    invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {head}.{changed}"},
    )
    assert invalid.status_code == 401
    wrong_type = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wrong_type.status_code == 401


def test_refresh_rotacion_y_reuso_revoca_todos(
    client: TestClient, ana_user: Usuario, db_session: Session
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": ana_user.email, "password": PASSWORD},
    )
    old_refresh = login.json()["refresh_token"]
    rotated = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != old_refresh

    reused = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert reused.status_code == 401
    tokens = db_session.scalars(
        select(RefreshToken).where(RefreshToken.usuario_id == ana_user.id)
    ).all()
    assert tokens and all(token.revocado for token in tokens)


def test_logout_invalida_refresh_y_cambio_password_revoca_tokens(
    client: TestClient, ana_user: Usuario, db_session: Session
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": ana_user.email, "password": PASSWORD},
    ).json()
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert logout.status_code == 204
    after_logout = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {login['refresh_token']}"},
    )
    assert after_logout.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        data={"username": ana_user.email, "password": PASSWORD},
    ).json()
    changed = client.patch(
        "/api/v1/auth/me/password",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={
            "current_password": PASSWORD,
            "new_password": "OtraClaveSegura123!",
            "confirm_password": "OtraClaveSegura123!",
        },
    )
    assert changed.status_code == 204
    assert db_session.scalar(
        select(RefreshToken.id).where(
            RefreshToken.usuario_id == ana_user.id,
            RefreshToken.revocado.is_(False),
        )
    ) is None


def test_bloqueo_login_despues_de_cinco_fallos(
    client: TestClient, luis_user: Usuario
) -> None:
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": luis_user.email, "password": "Incorrecta123"},
        )
        assert response.status_code == 401
    correct = client.post(
        "/api/v1/auth/login",
        data={"username": luis_user.email, "password": PASSWORD},
    )
    assert correct.status_code == 423
    assert correct.json()["detail"] == "Cuenta bloqueada temporalmente"


def test_rate_limit_login_responde_429_al_decimo_primer_intento(
    client: TestClient,
) -> None:
    responses = [
        client.post(
            "/api/v1/auth/login",
            data={"username": "desconocido@example.com", "password": PASSWORD},
        )
        for _ in range(11)
    ]
    assert all(response.status_code == 401 for response in responses[:10])
    assert responses[10].status_code == 429
