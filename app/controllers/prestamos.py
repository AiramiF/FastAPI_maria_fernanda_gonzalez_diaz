from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from ..core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from ..core.mongodb import Repository
from ..schemas.pagina import Pagina
from ..schemas.prestamo import EstadoPrestamo, PrestamoCreate, PrestamoRead


def _as_date(value: date | str | None) -> date | None:
    return date.fromisoformat(value) if isinstance(value, str) else value


def _estado(loan: dict[str, Any]) -> EstadoPrestamo:
    if loan.get("fecha_devolucion") is not None:
        return EstadoPrestamo.devuelto
    if _as_date(loan["fecha_limite"]) < date.today():
        return EstadoPrestamo.vencido
    return EstadoPrestamo.activo


def _respuesta(db: Repository, loan: dict[str, Any]) -> PrestamoRead:
    book = db.get("libros", loan["libro_id"])
    member = db.get("socios", loan["socio_id"])
    if book is None or member is None:
        raise NoEncontrado("No se encontró el libro o socio del préstamo")
    return PrestamoRead(
        id=loan["id"],
        libro_id=loan["libro_id"],
        socio_id=loan["socio_id"],
        fecha_prestamo=_as_date(loan["fecha_prestamo"]),
        fecha_limite=_as_date(loan["fecha_limite"]),
        fecha_devolucion=_as_date(loan.get("fecha_devolucion")),
        multa=Decimal(str(loan.get("multa", "0"))),
        multa_pagada=loan.get("multa_pagada", False),
        registrado_por_id=loan.get("registrado_por_id"),
        estado=_estado(loan),
        libro={"id": book["id"], "titulo": book["titulo"]},
        socio={
            "id": member["id"],
            "nombre": member["nombre"],
            "email": member["email"],
        },
    )


def listar_prestamos(
    db: Repository,
    skip: int,
    limit: int,
    estado: EstadoPrestamo | None,
    socio_id: int | None,
    libro_id: int | None,
    usuario_actual: Any | None = None,
) -> Pagina:
    if usuario_actual is not None and getattr(usuario_actual, "rol", None) == "socio":
        socio_id = usuario_actual.socio_id
    query = {}
    if socio_id is not None:
        query["socio_id"] = socio_id
    if libro_id is not None:
        query["libro_id"] = libro_id
    loans = list(db.collection("prestamos").find(query, {"_id": 0}))
    if estado is not None:
        loans = [loan for loan in loans if _estado(loan) == estado]
    loans.sort(key=lambda loan: loan["id"])
    return Pagina(
        items=[_respuesta(db, loan) for loan in loans[skip : skip + limit]],
        total=len(loans),
        skip=skip,
        limit=limit,
    )


def obtener_prestamo(
    db: Repository, prestamo_id: int, usuario_actual: Any | None = None
) -> PrestamoRead:
    loan = db.get("prestamos", prestamo_id)
    if loan is None:
        raise NoEncontrado("Préstamo no encontrado")
    if (
        usuario_actual is not None
        and getattr(usuario_actual, "rol", None) == "socio"
        and loan["socio_id"] != usuario_actual.socio_id
    ):
        raise NoEncontrado("Préstamo no encontrado")
    return _respuesta(db, loan)


def crear_prestamo(
    db: Repository, datos: PrestamoCreate, usuario_registra: Any | None = None
) -> PrestamoRead:
    member = db.get("socios", datos.socio_id)
    book = db.get("libros", datos.libro_id)
    if member is None:
        raise NoEncontrado("Socio no encontrado")
    if book is None:
        raise NoEncontrado("Libro no encontrado")
    if not member["activo"]:
        raise ReglaNegocio("El socio no está activo")
    user_id = member.get("usuario_id")
    user = db.get("usuarios", user_id) if user_id else None
    if user is not None and not user["activo"]:
        raise ReglaNegocio("El socio no tiene usuario activo")

    loans = list(
        db.collection("prestamos").find({"socio_id": member["id"]}, {"_id": 0})
    )
    if any(
        Decimal(str(loan.get("multa", "0"))) > 0 and not loan.get("multa_pagada", False)
        for loan in loans
    ):
        raise ReglaNegocio("El socio tiene multas pendientes")
    if any(
        _estado(loan) == EstadoPrestamo.vencido
        for loan in loans
    ):
        raise ReglaNegocio("El socio tiene préstamos vencidos")
    active_for_member = [
        loan for loan in loans if loan.get("fecha_devolucion") is None
    ]
    if len(active_for_member) >= 3:
        raise ReglaNegocio("Máximo de 3 préstamos")
    if any(
        loan["libro_id"] == book["id"] and loan.get("fecha_devolucion") is None
        for loan in loans
    ):
        raise Conflicto("El socio ya tiene este libro sin devolver")
    active_for_book = db.collection("prestamos").count_documents(
        {"libro_id": book["id"], "fecha_devolucion": None}
    )
    if book["ejemplares"] - active_for_book <= 0:
        raise ReglaNegocio("No hay ejemplares disponibles")

    started = datos.fecha_prestamo
    loan = db.insert(
        "prestamos",
        {
            "libro_id": book["id"],
            "socio_id": member["id"],
            "fecha_prestamo": started,
            "fecha_limite": started + timedelta(days=datos.dias),
            "fecha_devolucion": None,
            "multa": "0.00",
            "multa_pagada": False,
            "registrado_por_id": getattr(usuario_registra, "id", None),
        },
    )
    return _respuesta(db, loan)


def devolver_prestamo(db: Repository, prestamo_id: int) -> PrestamoRead:
    loan = db.get("prestamos", prestamo_id)
    if loan is None:
        raise NoEncontrado("Préstamo no encontrado")
    if loan.get("fecha_devolucion") is not None:
        raise Conflicto("El préstamo ya fue devuelto")
    today = date.today()
    if today < _as_date(loan["fecha_prestamo"]):
        raise ReglaNegocio("La fecha de devolución no puede ser anterior al préstamo")
    delay = (today - _as_date(loan["fecha_limite"])).days
    amount = Decimal(max(delay, 0)) * Decimal("0.50")
    changes = {
        "fecha_devolucion": today,
        "multa": str(amount),
        "multa_pagada": amount == 0,
    }
    updated = db.update("prestamos", prestamo_id, changes)
    existing_fine = db.collection("multas").find_one({"prestamo_id": prestamo_id})
    if amount > 0:
        fine = {
            "prestamo_id": prestamo_id,
            "socio_id": loan["socio_id"],
            "monto": str(amount),
            "pagada": False,
            "fecha_creada": today,
            "fecha_pago": None,
        }
        if existing_fine:
            db.collection("multas").update_one(
                {"id": existing_fine["id"]}, {"$set": fine}
            )
        else:
            db.insert("multas", fine)
    return _respuesta(db, updated or loan)


def pagar_multa(db: Repository, prestamo_id: int) -> PrestamoRead:
    loan = db.get("prestamos", prestamo_id)
    if loan is None:
        raise NoEncontrado("Préstamo no encontrado")
    if Decimal(str(loan.get("multa", "0"))) <= 0:
        raise Conflicto("No hay multa pendiente")
    if loan.get("multa_pagada", False):
        raise Conflicto("La multa ya está pagada")
    updated = db.update("prestamos", prestamo_id, {"multa_pagada": True})
    db.collection("multas").update_many(
        {"prestamo_id": prestamo_id},
        {"$set": {"pagada": True, "fecha_pago": date.today().isoformat()}},
    )
    return _respuesta(db, updated or loan)
