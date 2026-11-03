from fastapi.testclient import TestClient

from app.controllers import reportes


def test_health_y_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers.get("x-request-id")


def test_docs_y_cors_preflight(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_handler_500_no_expone_detalles(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    monkeypatch,
) -> None:
    def fail(_db) -> None:
        raise RuntimeError("detalle interno que no debe exponerse")

    monkeypatch.setattr(reportes, "resumen", fail)
    response = client.get(
        "/api/v1/reportes/resumen",
        headers=bibliotecario_headers,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno del servidor"}
