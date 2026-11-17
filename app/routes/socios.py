from fastapi import APIRouter, Depends, Response, status

from ..controllers import prestamos as prestamos_controller
from ..controllers import socios
from ..core.dependencies import (
    AdminUser,
    CurrentUser,
    PaginationDep,
    SessionDep,
    SocioUser,
    StaffUser,
)
from ..core.exceptions import NoEncontrado
from ..schemas.pagina import Pagina
from ..schemas.prestamo import EstadoPrestamo, PrestamoRead
from ..schemas.socio import SocioActualizarPropio, SocioCreate, SocioPatch, SocioRead

router = APIRouter(prefix="/socios", tags=["Socios"])


@router.get("/me", response_model=SocioRead)
def mi_perfil(
    db: SessionDep,
    usuario: SocioUser,
) -> SocioRead:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    return socios.obtener_socio(db, usuario.socio_id)


@router.patch("/me", response_model=SocioRead)
def actualizar_mi_perfil(
    db: SessionDep,
    datos: SocioActualizarPropio,
    usuario: SocioUser,
) -> SocioRead:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    socio = socios.obtener_socio(db, usuario.socio_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(socio, campo, valor)
    db.commit(); db.refresh(socio)
    return socio


@router.get("/me/prestamos", response_model=Pagina[PrestamoRead])
def mis_prestamos(
    db: SessionDep,
    paginacion: PaginationDep,
    usuario: SocioUser,
    estado: EstadoPrestamo | None = None,
) -> Pagina[PrestamoRead]:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    skip, limit = paginacion
    page = prestamos_controller.listar_prestamos(
        db,
        skip,
        limit,
        estado,
        usuario.socio_id,
        None,
    )
    return Pagina[
        PrestamoRead
    ](
        items=page.items,
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get("/me/multas", response_model=Pagina[PrestamoRead])
def mis_multas(
    db: SessionDep,
    paginacion: PaginationDep,
    usuario: SocioUser,
) -> Pagina[PrestamoRead]:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    skip, limit = paginacion
    prestamos = db.query(prestamos_controller.Prestamo).filter(
        prestamos_controller.Prestamo.socio_id == usuario.socio_id,
        prestamos_controller.Prestamo.multa > 0,
        prestamos_controller.Prestamo.multa_pagada.is_(False),
    ).order_by(prestamos_controller.Prestamo.id).offset(skip).limit(limit).all()
    total = db.query(prestamos_controller.Prestamo).filter(
        prestamos_controller.Prestamo.socio_id == usuario.socio_id,
        prestamos_controller.Prestamo.multa > 0,
        prestamos_controller.Prestamo.multa_pagada.is_(False),
    ).count()
    return Pagina[
        PrestamoRead
    ](
        items=[prestamos_controller._respuesta(item) for item in prestamos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("", response_model=Pagina[SocioRead])
def listar(
    db: SessionDep,
    paginacion: PaginationDep,
    _: StaffUser,
    activo: bool | None = None,
) -> Pagina[SocioRead]:
    skip, limit = paginacion
    page = socios.listar_socios(db, skip, limit, activo)
    return Pagina[
        SocioRead
    ](
        items=[SocioRead.model_validate(item) for item in page.items],
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get("/{socio_id}", response_model=SocioRead)
def obtener(
    socio_id: int,
    db: SessionDep,
    _: StaffUser,
) -> SocioRead:
    return socios.obtener_socio(db, socio_id)


@router.post("", response_model=SocioRead, status_code=status.HTTP_201_CREATED)
def crear(
    datos: SocioCreate,
    db: SessionDep,
    _: StaffUser,
) -> SocioRead:
    return socios.crear_socio(db, datos)


@router.patch("/{socio_id}", response_model=SocioRead)
def actualizar(
    socio_id: int,
    datos: SocioPatch,
    db: SessionDep,
    _: StaffUser,
) -> SocioRead:
    return socios.actualizar_socio(db, socio_id, datos)


@router.delete("/{socio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    socio_id: int,
    db: SessionDep,
    _: AdminUser,
) -> Response:
    socios.eliminar_socio(db, socio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{socio_id}/prestamos", response_model=Pagina[PrestamoRead])
def listar_prestamos(
    socio_id: int,
    db: SessionDep,
    paginacion: PaginationDep,
    _: StaffUser,
    estado: EstadoPrestamo | None = None,
) -> Pagina[PrestamoRead]:
    skip, limit = paginacion
    page = socios.listar_prestamos_socio(db, socio_id, skip, limit, estado)
    return Pagina[
        PrestamoRead
    ](
        items=page.items,
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )
