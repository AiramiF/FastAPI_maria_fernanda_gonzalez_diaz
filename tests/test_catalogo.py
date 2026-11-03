from fastapi.testclient import TestClient

from app.models import Libro


def test_catalogo_detalle_paginacion_y_libros_por_autor(
    client: TestClient, catalog: tuple[Libro, Libro]
) -> None:
    first, second = catalog
    authors = client.get("/api/v1/autores?skip=0&limit=1")
    categories = client.get("/api/v1/categorias")
    books = client.get("/api/v1/libros?skip=0&limit=1")
    assert authors.status_code == categories.status_code == books.status_code == 200
    assert authors.json()["total"] == categories.json()["total"] == 1
    assert books.json()["total"] == 2
    assert books.json()["skip"] == 0
    assert books.json()["limit"] == 1
    assert len(books.json()["items"]) == 1

    assert client.get(f"/api/v1/libros/{first.id}").status_code == 200
    author = client.get(f"/api/v1/autores/{first.autor_id}")
    assert author.status_code == 200
    author_books = client.get(f"/api/v1/autores/{first.autor_id}/libros")
    assert author_books.status_code == 200
    assert {item["id"] for item in author_books.json()["items"]} == {
        first.id,
        second.id,
    }


def test_catalogo_rechaza_paginacion_fuera_de_rango(client: TestClient) -> None:
    assert client.get("/api/v1/libros?skip=-1").status_code == 422
    assert client.get("/api/v1/libros?limit=101").status_code == 422
