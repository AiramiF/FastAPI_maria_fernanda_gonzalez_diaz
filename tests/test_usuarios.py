from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken, Usuario

PASSWORD = "TallerTest123!"


def test_admin_crea_usuarios_y_cambia_rol_revocando_refresh(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session: Session,
) -> None:
    created = client.post(
        "/api/v1/usuarios",
        headers=admin_headers,
        json={
            "email": "nuevo.staff@example.com",
            "nombre": "Nuevo Staff",
            "password": PASSWORD,
            "rol": "bibliotecario",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    user = db_session.get(Usuario, user_id)
    assert user is not None
    login = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": PASSWORD},
    )
    refresh = login.json()["refresh_token"]

    changed = client.patch(
        f"/api/v1/usuarios/{user_id}/rol",
        headers=admin_headers,
        json={"rol": "admin"},
    )
    assert changed.status_code == 200
    assert db_session.scalar(
        select(RefreshToken.id).where(
            RefreshToken.usuario_id == user_id,
            RefreshToken.revocado.is_(False),
        )
    ) is None
    assert (
        client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh}"},
        ).status_code
        == 401
    )


def test_admin_puede_crear_otro_admin(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/usuarios",
        headers=admin_headers,
        json={
            "email": "segundo.admin@example.com",
            "nombre": "Segundo Admin",
            "password": PASSWORD,
            "rol": "admin",
        },
    )
    assert created.status_code == 201
    assert created.json()["rol"] == "admin"


def test_admin_no_se_puede_deshabilitar_ni_quitar_rol(
    client: TestClient,
    admin: Usuario,
    admin_headers: dict[str, str],
) -> None:
    role = client.patch(
        f"/api/v1/usuarios/{admin.id}/rol",
        headers=admin_headers,
        json={"rol": "socio"},
    )
    inactive = client.patch(
        f"/api/v1/usuarios/{admin.id}/activo",
        headers=admin_headers,
        json={"activo": False},
    )
    assert role.status_code == inactive.status_code == 422
    assert role.json()["detail"] == "Debe mantenerse al menos un administrador activo"


def test_admin_desactiva_usuario_y_access_vigente_recibe_403(
    client: TestClient,
    admin_headers: dict[str, str],
    luis_user: Usuario,
    luis_headers: dict[str, str],
    db_session: Session,
) -> None:
    disabled = client.patch(
        f"/api/v1/usuarios/{luis_user.id}/activo",
        headers=admin_headers,
        json={"activo": False},
    )
    assert disabled.status_code == 200
    me = client.get("/api/v1/auth/me", headers=luis_headers)
    assert me.status_code == 403
    assert me.json()["detail"] == "Usuario inactivo"
    assert db_session.scalar(
        select(RefreshToken.id).where(
            RefreshToken.usuario_id == luis_user.id,
            RefreshToken.revocado.is_(False),
        )
    ) is None
