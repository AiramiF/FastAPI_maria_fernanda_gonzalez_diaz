from fastapi import APIRouter, Depends, status

from ..controllers import prestamos
from ..core.dependencies import (
    AdminUser,
    CurrentUser,
    PaginationDep,
    SessionDep,
    SocioUser,
    StaffUser,
)
from ..schemas.pagina import Pagina
from ..schemas.prestamo import EstadoPrestamo, PrestamoCreate, PrestamoRead

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


@router.get("", response_model=Pagina[PrestamoRead])
def listar(
    db: SessionDep,
    paginacion: PaginationDep,
    usuario: CurrentUser,
    estado: EstadoPrestamo | None = None,
    socio_id: int | None = None,
    libro_id: int | None = None,
) -> Pagina[PrestamoRead]:
    skip, limit = paginacion
    page = prestamos.listar_prestamos(
        db, skip, limit, estado, socio_id, libro_id, usuario
    )
    return Pagina[
        PrestamoRead
    ](
        items=page.items,
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get("/{prestamo_id}", response_model=PrestamoRead)
def obtener(
    prestamo_id: int,
    db: SessionDep,
    usuario: CurrentUser,
) -> PrestamoRead:
    return prestamos.obtener_prestamo(db, prestamo_id, usuario)


@router.post(
    "",
    response_model=PrestamoRead,
    status_code=status.HTTP_201_CREATED,
)
def crear(
    datos: PrestamoCreate,
    db: SessionDep,
    usuario: StaffUser,
) -> PrestamoRead:
    return prestamos.crear_prestamo(db, datos, usuario)


@router.post("/{prestamo_id}/devolucion", response_model=PrestamoRead)
def devolver(
    prestamo_id: int,
    db: SessionDep,
    _: StaffUser,
) -> PrestamoRead:
    return prestamos.devolver_prestamo(db, prestamo_id)


@router.post("/{prestamo_id}/pago-multa", response_model=PrestamoRead)
def pago_multa(
    prestamo_id: int,
    db: SessionDep,
    _: StaffUser,
) -> PrestamoRead:
    prestamo = db.get(prestamos.Prestamo, prestamo_id)
    if prestamo is None:
        raise prestamos.NoEncontrado("Préstamo no encontrado")
    if prestamo.multa <= 0:
        raise prestamos.Conflicto("No hay multa pendiente")
    if prestamo.multa_pagada:
        raise prestamos.Conflicto("La multa ya está pagada")
    prestamo.multa_pagada = True
    db.commit()
    db.refresh(prestamo)
    return prestamos._respuesta(prestamo)
