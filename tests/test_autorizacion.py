from fastapi.testclient import TestClient

from app.models import Libro, Socio


def new_book(first: Libro, isbn: str) -> dict[str, object]:
    return {
        "titulo": "Libro Nuevo",
        "isbn": isbn,
        "anio_publicacion": 2022,
        "ejemplares": 1,
        "autor_id": first.autor_id,
        "categoria_ids": [first.categorias[0].id],
    }


def test_catalogo_lectura_publica_y_escritura_staff_solo(
    client: TestClient,
    catalog: tuple[Libro, Libro],
    ana_headers: dict[str, str],
    bibliotecario_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    first, _ = catalog
    for path in ("/libros", "/autores", "/categorias"):
        response = client.get(f"/api/v1{path}")
        assert response.status_code == 200
        assert set(("items", "total", "skip", "limit")) <= response.json().keys()

    payload = new_book(first, "3333333333333")
    assert (
        client.post("/api/v1/libros", headers=ana_headers, json=payload).status_code
        == 403
    )
    created = client.post(
        "/api/v1/libros", headers=bibliotecario_headers, json=payload
    )
    assert created.status_code == 201
    book_id = created.json()["id"]
    assert (
        client.delete(
            f"/api/v1/libros/{book_id}", headers=bibliotecario_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/libros/{book_id}", headers=admin_headers).status_code
        == 204
    )


def test_autores_y_categorias_escritura_staff_borrado_admin(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    author = client.post(
        "/api/v1/autores",
        headers=bibliotecario_headers,
        json={"nombre": "Autora Endpoint", "nacionalidad": "Colombia"},
    )
    category = client.post(
        "/api/v1/categorias",
        headers=bibliotecario_headers,
        json={"nombre": "Endpoint", "descripcion": "Categoría de test"},
    )
    assert author.status_code == category.status_code == 201
    author_id = author.json()["id"]
    category_id = category.json()["id"]

    assert (
        client.patch(
            f"/api/v1/autores/{author_id}",
            headers=bibliotecario_headers,
            json={"nacionalidad": "Chile"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/categorias/{category_id}",
            headers=bibliotecario_headers,
            json={"descripcion": "Actualizada"},
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/v1/autores/{author_id}", headers=bibliotecario_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/categorias/{category_id}", headers=bibliotecario_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/autores/{author_id}", headers=admin_headers).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/categorias/{category_id}", headers=admin_headers
        ).status_code
        == 204
    )


def test_reportes_staff_y_usuario_solo_admin(
    client: TestClient,
    ana_headers: dict[str, str],
    bibliotecario_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    report_paths = (
        "libros-mas-prestados",
        "categorias",
        "prestamos-vencidos",
        "socios-con-multas",
        "autores",
        "resumen",
    )
    assert client.get("/api/v1/reportes/resumen").status_code == 401
    assert (
        client.get(
            "/api/v1/reportes/resumen", headers=ana_headers
        ).status_code
        == 403
    )
    for path in report_paths:
        assert (
            client.get(
                f"/api/v1/reportes/{path}", headers=bibliotecario_headers
            ).status_code
            == 200
        )

    assert (
        client.get("/api/v1/usuarios", headers=bibliotecario_headers).status_code
        == 403
    )
    assert client.get("/api/v1/usuarios", headers=admin_headers).status_code == 200


def test_post_prestamos_no_permite_socio(
    client: TestClient,
    ana_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    first, _ = catalog
    response = client.post(
        "/api/v1/prestamos",
        headers=ana_headers,
        json={
            "libro_id": first.id,
            "socio_id": ana.id,
            "dias": 14,
        },
    )
    assert response.status_code == 403
