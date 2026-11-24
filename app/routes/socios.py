from fastapi import APIRouter, Response, status

from ..controllers import prestamos as prestamos_controller
from ..controllers import socios
from ..core.dependencies import (
    AdminUser,
    PaginationDep,
    RepositoryDep,
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
    db: RepositoryDep,
    usuario: SocioUser,
) -> SocioRead:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    return socios.obtener_socio(db, usuario.socio_id)


@router.patch("/me", response_model=SocioRead)
def actualizar_mi_perfil(
    db: RepositoryDep,
    datos: SocioActualizarPropio,
    usuario: SocioUser,
) -> SocioRead:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    return socios.actualizar_perfil_propio(
        db, usuario.socio_id, datos.model_dump(exclude_unset=True)
    )


@router.get("/me/prestamos", response_model=Pagina[PrestamoRead])
def mis_prestamos(
    db: RepositoryDep,
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
    db: RepositoryDep,
    paginacion: PaginationDep,
    usuario: SocioUser,
) -> Pagina[PrestamoRead]:
    if usuario.socio_id is None:
        raise NoEncontrado("Socio no encontrado")
    skip, limit = paginacion
    return socios.listar_multas_socio(db, usuario.socio_id, skip, limit)


@router.get("", response_model=Pagina[SocioRead])
def listar(
    db: RepositoryDep,
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
    db: RepositoryDep,
    _: StaffUser,
) -> SocioRead:
    return socios.obtener_socio(db, socio_id)


@router.post("", response_model=SocioRead, status_code=status.HTTP_201_CREATED)
def crear(
    datos: SocioCreate,
    db: RepositoryDep,
    _: StaffUser,
) -> SocioRead:
    return socios.crear_socio(db, datos)


@router.patch("/{socio_id}", response_model=SocioRead)
def actualizar(
    socio_id: int,
    datos: SocioPatch,
    db: RepositoryDep,
    _: StaffUser,
) -> SocioRead:
    return socios.actualizar_socio(db, socio_id, datos)


@router.delete("/{socio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    socio_id: int,
    db: RepositoryDep,
    _: AdminUser,
) -> Response:
    socios.eliminar_socio(db, socio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{socio_id}/prestamos", response_model=Pagina[PrestamoRead])
def listar_prestamos(
    socio_id: int,
    db: RepositoryDep,
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
