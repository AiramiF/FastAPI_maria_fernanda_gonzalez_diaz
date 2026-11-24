from fastapi import APIRouter, Query

from ..controllers import reportes
from ..core.dependencies import RepositoryDep, StaffUser
from ..schemas.reportes import (
    AutorReporteRead,
    CategoriaReporteRead,
    LibroMasPrestadoRead,
    PrestamoVencidoRead,
    ResumenRead,
    SocioMultasRead,
)

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/libros-mas-prestados", response_model=list[LibroMasPrestadoRead])
def libros_mas_prestados(
    db: RepositoryDep, _: StaffUser, limite: int = Query(default=5, ge=1, le=100)
) -> list[LibroMasPrestadoRead]:
    return reportes.libros_mas_prestados(db, limite)


@router.get("/categorias", response_model=list[CategoriaReporteRead])
def categorias(db: RepositoryDep, _: StaffUser) -> list[CategoriaReporteRead]:
    return reportes.categorias(db)


@router.get("/prestamos-vencidos", response_model=list[PrestamoVencidoRead])
def prestamos_vencidos(db: RepositoryDep, _: StaffUser) -> list[PrestamoVencidoRead]:
    return reportes.prestamos_vencidos(db)


@router.get("/socios-con-multas", response_model=list[SocioMultasRead])
def socios_con_multas(db: RepositoryDep, _: StaffUser) -> list[SocioMultasRead]:
    return reportes.socios_con_multas(db)


@router.get("/autores", response_model=list[AutorReporteRead])
def autores(db: RepositoryDep, _: StaffUser) -> list[AutorReporteRead]:
    return reportes.autores(db)


@router.get("/resumen", response_model=ResumenRead)
def resumen(db: RepositoryDep, _: StaffUser) -> ResumenRead:
    return reportes.resumen(db)
