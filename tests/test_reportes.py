from fastapi.testclient import TestClient


def test_reportes_todos_requieren_staff(
    client: TestClient,
    ana_headers: dict[str, str],
    bibliotecario_headers: dict[str, str],
) -> None:
    paths = (
        "libros-mas-prestados",
        "categorias",
        "prestamos-vencidos",
        "socios-con-multas",
        "autores",
        "resumen",
    )
    for path in paths:
        assert client.get(f"/api/v1/reportes/{path}").status_code == 401
        assert (
            client.get(
                f"/api/v1/reportes/{path}", headers=ana_headers
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/v1/reportes/{path}", headers=bibliotecario_headers
            ).status_code
            == 200
        )
