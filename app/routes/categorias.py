from fastapi import APIRouter, Response, status

from ..controllers import categorias
from ..core.dependencies import AdminUser, PaginationDep, RepositoryDep, StaffUser
from ..schemas.categoria import CategoriaCreate, CategoriaPatch, CategoriaRead
from ..schemas.pagina import Pagina

router = APIRouter(prefix="/categorias", tags=["Categorías"])


@router.get("", response_model=Pagina[CategoriaRead])
def listar(db: RepositoryDep, paginacion: PaginationDep) -> Pagina[CategoriaRead]:
    skip, limit = paginacion
    page = categorias.listar_categorias(db, skip, limit)
    return Pagina[
        CategoriaRead
    ](
        items=[CategoriaRead.model_validate(item) for item in page.items],
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.post("", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
def crear(datos: CategoriaCreate, db: RepositoryDep, _: StaffUser) -> CategoriaRead:
    return categorias.crear_categoria(db, datos)


@router.patch("/{categoria_id}", response_model=CategoriaRead)
def actualizar(
    categoria_id: int, datos: CategoriaPatch, db: RepositoryDep, _: StaffUser
) -> CategoriaRead:
    return categorias.actualizar_categoria(db, categoria_id, datos)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(categoria_id: int, db: RepositoryDep, _: AdminUser) -> Response:
    categorias.eliminar_categoria(db, categoria_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
