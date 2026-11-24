from datetime import datetime, timezone

from ..core.exceptions import Conflicto, NoEncontrado
from ..core.mongodb import Repository
from ..schemas.pagina import Pagina
from ..schemas.prestamo import EstadoPrestamo
from ..schemas.socio import SocioCreate, SocioPatch
from . import prestamos


def listar_socios(
    db: Repository, skip: int, limit: int, activo: bool | None = None
) -> Pagina:
    query = {} if activo is None else {"activo": activo}
    items = list(db.collection("socios").find(query, {"_id": 0}).sort("id", 1))
    total = db.collection("socios").count_documents(query)
    return Pagina(items=items[skip : skip + limit], total=total, skip=skip, limit=limit)


def obtener_socio(db: Repository, socio_id: int) -> dict:
    member = db.get("socios", socio_id)
    if member is None:
        raise NoEncontrado("Socio no encontrado")
    return member


def crear_socio(db: Repository, datos: SocioCreate) -> dict:
    if db.collection("socios").find_one({"email": datos.email}):
        raise Conflicto("El email ya existe")
    return db.insert(
        "socios",
        {
            **datos.model_dump(),
            "activo": True,
            "fecha_alta": datetime.now(timezone.utc),
            "usuario_id": None,
        },
    )


def actualizar_socio(db: Repository, socio_id: int, datos: SocioPatch) -> dict:
    obtener_socio(db, socio_id)
    changes = datos.model_dump(exclude_unset=True)
    if "email" in changes and db.collection("socios").find_one(
        {"email": changes["email"], "id": {"$ne": socio_id}}
    ):
        raise Conflicto("El email ya existe")
    return db.update("socios", socio_id, changes) or obtener_socio(db, socio_id)


def actualizar_perfil_propio(
    db: Repository, socio_id: int, cambios: dict
) -> dict:
    obtener_socio(db, socio_id)
    return db.update("socios", socio_id, cambios) or obtener_socio(db, socio_id)


def eliminar_socio(db: Repository, socio_id: int) -> None:
    member = obtener_socio(db, socio_id)
    loans = list(db.collection("prestamos").find({"socio_id": socio_id}, {"_id": 0}))
    if any(loan.get("fecha_devolucion") is None for loan in loans):
        raise Conflicto("No se puede eliminar un socio con préstamos sin devolver")
    if loans:
        db.update("socios", socio_id, {"activo": False})
        return
    if member.get("usuario_id") is not None:
        db.update("usuarios", member["usuario_id"], {"socio_id": None})
    db.delete("socios", socio_id)


def listar_prestamos_socio(
    db: Repository,
    socio_id: int,
    skip: int,
    limit: int,
    estado: EstadoPrestamo | None,
) -> Pagina:
    obtener_socio(db, socio_id)
    return prestamos.listar_prestamos(
        db, skip, limit, estado, socio_id=socio_id, libro_id=None
    )


def listar_multas_socio(db: Repository, socio_id: int, skip: int, limit: int) -> Pagina:
    loans = [
        loan
        for loan in db.collection("prestamos").find(
            {"socio_id": socio_id, "multa_pagada": False}, {"_id": 0}
        )
        if float(loan.get("multa", "0")) > 0
    ]
    loans.sort(key=lambda loan: loan["id"])
    items = [prestamos._respuesta(db, loan) for loan in loans[skip : skip + limit]]
    return Pagina(items=items, total=len(loans), skip=skip, limit=limit)
