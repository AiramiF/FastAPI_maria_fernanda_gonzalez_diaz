from datetime import date
from decimal import Decimal

from ..core.mongodb import Repository
from ..schemas.reportes import (
    AutorReporteRead,
    CategoriaReporteRead,
    LibroMasPrestadoRead,
    PrestamoVencidoRead,
    ResumenRead,
    SocioMultasRead,
)


def _all(db: Repository, collection: str) -> list[dict]:
    return list(db.collection(collection).find({}, {"_id": 0}))


def _date(value: date | str) -> date:
    return date.fromisoformat(value) if isinstance(value, str) else value


def libros_mas_prestados(db: Repository, limite: int) -> list[LibroMasPrestadoRead]:
    counts: dict[int, int] = {}
    for loan in _all(db, "prestamos"):
        counts[loan["libro_id"]] = counts.get(loan["libro_id"], 0) + 1
    results = []
    for book_id, count in counts.items():
        book = db.get("libros", book_id)
        author = db.get("autores", book["autor_id"]) if book else None
        if book and author:
            results.append(
                LibroMasPrestadoRead(
                    libro=book["titulo"],
                    autor=author["nombre"],
                    total_prestamos=count,
                )
            )
    return sorted(results, key=lambda row: (-row.total_prestamos, row.libro))[:limite]


def categorias(db: Repository) -> list[CategoriaReporteRead]:
    books = _all(db, "libros")
    return [
        CategoriaReporteRead(
            nombre=category["nombre"],
            total_libros=sum(
                category["id"] in book.get("categoria_ids", []) for book in books
            ),
        )
        for category in sorted(_all(db, "categorias"), key=lambda item: item["nombre"])
    ]


def prestamos_vencidos(db: Repository) -> list[PrestamoVencidoRead]:
    today = date.today()
    result = []
    for loan in _all(db, "prestamos"):
        due_date = _date(loan["fecha_limite"])
        if loan.get("fecha_devolucion") is not None or due_date >= today:
            continue
        book = db.get("libros", loan["libro_id"])
        member = db.get("socios", loan["socio_id"])
        if book and member:
            result.append(
                PrestamoVencidoRead(
                    prestamo_id=loan["id"],
                    titulo=book["titulo"],
                    socio=member["nombre"],
                    email=member["email"],
                    fecha_limite=due_date,
                    dias_retraso=(today - due_date).days,
                )
            )
    return sorted(result, key=lambda row: (row.fecha_limite, row.prestamo_id))


def socios_con_multas(db: Repository) -> list[SocioMultasRead]:
    totals: dict[int, tuple[Decimal, int]] = {}
    for loan in _all(db, "prestamos"):
        amount = Decimal(str(loan.get("multa", "0")))
        if amount <= 0:
            continue
        total, count = totals.get(loan["socio_id"], (Decimal("0"), 0))
        totals[loan["socio_id"]] = (total + amount, count + 1)
    rows = []
    for member_id, (total, count) in totals.items():
        member = db.get("socios", member_id)
        if member:
            rows.append(
                SocioMultasRead(
                    socio=member["nombre"],
                    total_multas=total,
                    prestamos_con_multa=count,
                )
            )
    return sorted(rows, key=lambda row: row.socio)


def autores(db: Repository) -> list[AutorReporteRead]:
    books = _all(db, "libros")
    loans = _all(db, "prestamos")
    results = []
    for author in _all(db, "autores"):
        author_books = [book for book in books if book["autor_id"] == author["id"]]
        book_ids = {book["id"] for book in author_books}
        results.append(
            AutorReporteRead(
                autor=author["nombre"],
                total_libros=len(author_books),
                total_ejemplares=sum(book["ejemplares"] for book in author_books),
                total_prestamos=sum(loan["libro_id"] in book_ids for loan in loans),
            )
        )
    return sorted(results, key=lambda row: row.autor)


def resumen(db: Repository) -> ResumenRead:
    books = _all(db, "libros")
    loans = _all(db, "prestamos")
    active_loans = [loan for loan in loans if loan.get("fecha_devolucion") is None]
    return ResumenRead(
        total_libros=len(books),
        total_ejemplares=sum(book["ejemplares"] for book in books),
        prestados=len(active_loans),
        socios_activos=db.collection("socios").count_documents({"activo": True}),
        vencidos=sum(_date(loan["fecha_limite"]) < date.today() for loan in active_loans),
        multas=sum(
            (Decimal(str(loan.get("multa", "0"))) for loan in loans),
            Decimal("0"),
        ),
    )
