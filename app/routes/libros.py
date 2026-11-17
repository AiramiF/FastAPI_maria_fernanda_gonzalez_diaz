from fastapi import APIRouter, File, Query, Response, UploadFile, status

from ..controllers import libros
from ..core.exceptions import ArchivoNoValido, PayloadDemasiadoGrande
from ..core.dependencies import AdminUser, PaginationDep, SessionDep, StaffUser
from ..schemas.libro import LibroCreate, LibroPatch, LibroRead, OrdenLibro
from ..schemas.pagina import Pagina

router = APIRouter(prefix="/libros", tags=["Libros"])
MAX_PORTADA_BYTES = 5 * 1024 * 1024
FIRMAS_IMAGEN = {
    "image/jpeg": lambda contenido: contenido.startswith(b"\xff\xd8\xff"),
    "image/png": lambda contenido: contenido.startswith(
        b"\x89PNG\r\n\x1a\n"
    ),
    "image/webp": lambda contenido: (
        len(contenido) >= 12
        and contenido.startswith(b"RIFF")
        and contenido[8:12] == b"WEBP"
    ),
}


def _leer_portada(archivo: UploadFile) -> bytes:
    tipo_contenido = archivo.content_type
    if tipo_contenido is None or tipo_contenido not in FIRMAS_IMAGEN:
        raise ArchivoNoValido("Tipo de imagen no permitido")
    contenido = archivo.file.read(MAX_PORTADA_BYTES + 1)
    if len(contenido) > MAX_PORTADA_BYTES:
        raise PayloadDemasiadoGrande("La portada no puede superar 5 MB")
    if not FIRMAS_IMAGEN[tipo_contenido](contenido):
        raise ArchivoNoValido("El contenido no coincide con un formato de imagen permitido")
    return contenido


@router.get("", response_model=Pagina[LibroRead])
def listar(
    db: SessionDep,
    paginacion: PaginationDep,
    buscar: str | None = None,
    autor: str | None = None,
    categoria_id: int | None = Query(default=None, ge=1),
    desde: int | None = Query(default=None, ge=1450),
    hasta: int | None = Query(default=None, ge=1450),
    orden: OrdenLibro = OrdenLibro.titulo,
) -> Pagina[LibroRead]:
    skip, limit = paginacion
    page = libros.listar_libros(
        db, skip, limit, buscar, autor, categoria_id, desde, hasta, orden.value
    )
    return Pagina[
        LibroRead
    ](
        items=page.items,
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get("/{libro_id}", response_model=LibroRead)
def obtener(libro_id: int, db: SessionDep) -> LibroRead:
    return libros.obtener_libro(db, libro_id)


@router.post("/{libro_id}/portada", response_model=LibroRead)
def subir_portada(
    libro_id: int,
    db: SessionDep,
    _: StaffUser,
    archivo: UploadFile = File(...),
) -> LibroRead:
    return libros.subir_portada(db, libro_id, _leer_portada(archivo))


@router.delete(
    "/{libro_id}/portada",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_portada(
    libro_id: int, db: SessionDep, _: StaffUser
) -> Response:
    libros.eliminar_portada(db, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=LibroRead, status_code=status.HTTP_201_CREATED)
def crear(datos: LibroCreate, db: SessionDep, _: StaffUser) -> LibroRead:
    return libros.crear_libro(db, datos)


@router.patch("/{libro_id}", response_model=LibroRead)
def actualizar(
    libro_id: int, datos: LibroPatch, db: SessionDep, _: StaffUser
) -> LibroRead:
    return libros.actualizar_libro(db, libro_id, datos)


@router.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(libro_id: int, db: SessionDep, _: AdminUser) -> Response:
    libros.eliminar_libro(db, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
