from fastapi import APIRouter, Response, status

from ..controllers import autores
from ..controllers import libros as libros_controller
from ..core.dependencies import AdminUser, PaginationDep, SessionDep, StaffUser
from ..schemas.autor import AutorCreate, AutorPatch, AutorRead
from ..schemas.libro import LibroRead
from ..schemas.pagina import Pagina

router = APIRouter(prefix="/autores", tags=["Autores"])


@router.get("", response_model=Pagina[AutorRead])
def listar(
    db: SessionDep,
    paginacion: PaginationDep,
    nacionalidad: str | None = None,
) -> Pagina[AutorRead]:
    skip, limit = paginacion
    page = autores.listar_autores(db, skip, limit, nacionalidad)
    return Pagina[
        AutorRead
    ](
        items=[AutorRead.model_validate(item) for item in page.items],
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get("/{autor_id}", response_model=AutorRead)
def obtener(autor_id: int, db: SessionDep) -> AutorRead:
    return autores.obtener_autor(db, autor_id)


@router.post("", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
def crear(datos: AutorCreate, db: SessionDep, _: StaffUser) -> AutorRead:
    return autores.crear_autor(db, datos)


@router.patch("/{autor_id}", response_model=AutorRead)
def actualizar(
    autor_id: int, datos: AutorPatch, db: SessionDep, _: StaffUser
) -> AutorRead:
    return autores.actualizar_autor(db, autor_id, datos)


@router.delete("/{autor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(autor_id: int, db: SessionDep, _: AdminUser) -> Response:
    autores.eliminar_autor(db, autor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{autor_id}/libros", response_model=Pagina[LibroRead])
def libros_del_autor(
    autor_id: int, db: SessionDep, paginacion: PaginationDep
) -> Pagina[LibroRead]:
    skip, limit = paginacion
    page = libros_controller.listar_libros_autor(db, autor_id, skip, limit)
    return Pagina[
        LibroRead
    ](
        items=page.items,
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )
