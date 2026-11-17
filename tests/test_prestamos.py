from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Libro, Prestamo, RefreshToken, Socio, Usuario


def create_loan(
    client: TestClient,
    headers: dict[str, str],
    book: Libro,
    socio: Socio,
    *,
    loan_date: date | None = None,
    days: int = 14,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/prestamos",
        headers=headers,
        json={
            "libro_id": book.id,
            "socio_id": socio.id,
            "fecha_prestamo": (loan_date or date.today()).isoformat(),
            "dias": days,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_bibliotecario_crea_prestamos_y_socio_solo_ve_los_suyos(
    client: TestClient,
    bibliotecario: Usuario,
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    luis: Socio,
    ana_headers: dict[str, str],
    catalog: tuple[Libro, Libro],
) -> None:
    first, second = catalog
    ana_loan = create_loan(client, bibliotecario_headers, first, ana)
    luis_loan = create_loan(client, bibliotecario_headers, second, luis)
    assert ana_loan["registrado_por_id"] == bibliotecario.id
    assert luis_loan["socio_id"] == luis.id

    own = client.get("/api/v1/prestamos", headers=ana_headers)
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert [item["socio_id"] for item in own.json()["items"]] == [ana.id]

    ignored_filter = client.get(
        f"/api/v1/prestamos?socio_id={luis.id}", headers=ana_headers
    )
    assert ignored_filter.status_code == 200
    assert ignored_filter.json()["total"] == 1
    assert ignored_filter.json()["items"][0]["socio_id"] == ana.id
    assert (
        client.get(
            f"/api/v1/prestamos/{luis_loan['id']}", headers=ana_headers
        ).status_code
        == 404
    )


def test_multa_pendiente_bloquea_prestamo_hasta_pago(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    first, second = catalog
    old_date = date.today() - timedelta(days=20)
    overdue = create_loan(
        client,
        bibliotecario_headers,
        first,
        ana,
        loan_date=old_date,
        days=7,
    )
    returned = client.post(
        f"/api/v1/prestamos/{overdue['id']}/devolucion",
        headers=bibliotecario_headers,
    )
    assert returned.status_code == 200
    assert returned.json()["multa"] == "6.50"
    assert returned.json()["multa_pagada"] is False

    blocked = client.post(
        "/api/v1/prestamos",
        headers=bibliotecario_headers,
        json={
            "libro_id": second.id,
            "socio_id": ana.id,
            "dias": 14,
        },
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"] == "El socio tiene multas pendientes"

    payment_path = f"/api/v1/prestamos/{overdue['id']}/pago-multa"
    paid = client.post(payment_path, headers=bibliotecario_headers)
    assert paid.status_code == 200
    assert paid.json()["multa"] == "6.50"
    assert paid.json()["multa_pagada"] is True
    assert client.post(payment_path, headers=bibliotecario_headers).status_code == 409
    allowed = client.post(
        "/api/v1/prestamos",
        headers=bibliotecario_headers,
        json={
            "libro_id": second.id,
            "socio_id": ana.id,
            "dias": 14,
        },
    )
    assert allowed.status_code == 201


def test_devolucion_a_tiempo_marca_multa_como_pagada(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    loan = create_loan(client, bibliotecario_headers, catalog[0], ana)
    returned = client.post(
        f"/api/v1/prestamos/{loan['id']}/devolucion",
        headers=bibliotecario_headers,
    )
    assert returned.status_code == 200
    assert Decimal(returned.json()["multa"]) == Decimal("0.00")
    assert returned.json()["multa_pagada"] is True


def test_socio_multas_pendientes_y_paginacion(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    ana_headers: dict[str, str],
    catalog: tuple[Libro, Libro],
    db_session: Session,
) -> None:
    loan = create_loan(
        client,
        bibliotecario_headers,
        catalog[0],
        ana,
        loan_date=date.today() - timedelta(days=20),
        days=7,
    )
    client.post(
        f"/api/v1/prestamos/{loan['id']}/devolucion",
        headers=bibliotecario_headers,
    )
    fines = client.get("/api/v1/socios/me/multas", headers=ana_headers)
    assert fines.status_code == 200
    assert fines.json()["total"] == 1
    assert fines.json()["items"][0]["multa_pagada"] is False

    assert db_session.scalar(
        select(Prestamo.id).where(
            Prestamo.socio_id == ana.id,
            Prestamo.multa > 0,
            Prestamo.multa_pagada.is_(False),
        )
    ) == loan["id"]


def test_pago_sin_multa_devuelve_conflicto(
    client: TestClient,
    bibliotecario_headers: dict[str, str],
    ana: Socio,
    catalog: tuple[Libro, Libro],
) -> None:
    loan = create_loan(client, bibliotecario_headers, catalog[0], ana)
    response = client.post(
        f"/api/v1/prestamos/{loan['id']}/pago-multa",
        headers=bibliotecario_headers,
    )
    assert response.status_code == 409
