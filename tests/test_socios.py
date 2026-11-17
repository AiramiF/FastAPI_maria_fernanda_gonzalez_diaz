from fastapi.testclient import TestClient

from app.models import Libro, Socio


def test_socio_perfil_propio_y_patch_restringido(
    client: TestClient,
    ana: Socio,
    ana_headers: dict[str, str],
) -> None:
    profile = client.get("/api/v1/socios/me", headers=ana_headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == ana.id
    assert (
        client.patch(
            "/api/v1/socios/me",
            headers=ana_headers,
            json={"activo": False},
        ).status_code
        == 422
    )
    updated = client.patch(
        "/api/v1/socios/me",
        headers=ana_headers,
        json={"nombre": "Ana Actualizada", "telefono": "5559876"},
    )
    assert updated.status_code == 200
    assert updated.json()["nombre"] == "Ana Actualizada"


def test_staff_lista_crea_y_actualiza_socios(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/socios",
        headers=bibliotecario_headers,
        json={
            "nombre": "Socio Manual",
            "email": "manual@example.com",
            "telefono": "5551111",
        },
    )
    assert created.status_code == 201
    socio_id = created.json()["id"]
    assert client.get("/api/v1/socios", headers=bibliotecario_headers).status_code == 200
    updated = client.patch(
        f"/api/v1/socios/{socio_id}",
        headers=bibliotecario_headers,
        json={"nombre": "Socio Modificado"},
    )
    assert updated.status_code == 200
    assert updated.json()["nombre"] == "Socio Modificado"


def test_staff_consulta_prestamos_y_admin_no_borra_socio_con_prestamo_activo(
    client: TestClient,
    admin_headers: dict[str, str],
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    book = catalog[0]
    loan = client.post(
        "/api/v1/prestamos",
        headers=bibliotecario_headers,
        json={"libro_id": book.id, "socio_id": ana.id, "dias": 14},
    )
    assert loan.status_code == 201
    listing = client.get(
        f"/api/v1/socios/{ana.id}/prestamos",
        headers=bibliotecario_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    deleted = client.delete(
        f"/api/v1/socios/{ana.id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 409


def test_socio_con_historial_se_desactiva_en_lugar_de_borrarse(
    client: TestClient,
    db_session,
    admin_headers: dict[str, str],
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    loan = client.post(
        "/api/v1/prestamos",
        headers=bibliotecario_headers,
        json={"libro_id": catalog[0].id, "socio_id": ana.id, "dias": 14},
    )
    assert loan.status_code == 201
    returned = client.post(
        f"/api/v1/prestamos/{loan.json()['id']}/devolucion",
        headers=bibliotecario_headers,
    )
    assert returned.status_code == 200
    deleted = client.delete(
        f"/api/v1/socios/{ana.id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 204
    db_session.refresh(ana)
    assert ana.activo is False
