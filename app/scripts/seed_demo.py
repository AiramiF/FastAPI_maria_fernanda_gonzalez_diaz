from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.security import SecurityService
from app.models.autor import Autor
from app.models.categoria import Categoria
from app.models.libro import Libro
from app.models.prestamo import Prestamo
from app.models.socio import Socio
from app.models.usuario import RolUsuario, Usuario

ADMIN_EMAIL = "admin@biblioteca.com"
SOCIO_EMAIL = "socio@biblioteca.com"
DEMO_PASSWORD = "Biblioteca2026"
SOCIO_TELEFONO = "+57 3000000000"

DEMO_AUTHORS = (
    ("Gabriel García Márquez", "Colombia", 1927),
    ("Isabel Allende", "Chile", 1942),
    ("Jorge Luis Borges", "Argentina", 1899),
    ("Laura Esquivel", "México", 1950),
    ("Mario Vargas Llosa", "Perú", 1936),
)

DEMO_CATEGORIES = {
    "novela": "Narraciones extensas de ficción.",
    "realismo mágico": "Ficción que integra elementos mágicos en la vida cotidiana.",
    "cuentos": "Relatos breves de ficción.",
    "literatura latinoamericana": "Obras de autores de América Latina.",
    "ficción histórica": "Narraciones ficticias ambientadas en otras épocas.",
}

DEMO_BOOKS = (
    (
        "Cien años de soledad",
        "9780307474728",
        1967,
        "Gabriel García Márquez",
        ("novela", "realismo mágico", "literatura latinoamericana"),
    ),
    (
        "El amor en los tiempos del cólera",
        "9780307389732",
        1985,
        "Gabriel García Márquez",
        ("novela", "realismo mágico", "literatura latinoamericana"),
    ),
    (
        "Crónica de una muerte anunciada",
        "9788439711117",
        1981,
        "Gabriel García Márquez",
        ("novela", "literatura latinoamericana"),
    ),
    (
        "La casa de los espíritus",
        "9780553383805",
        1982,
        "Isabel Allende",
        ("novela", "realismo mágico", "literatura latinoamericana"),
    ),
    (
        "Ficciones",
        "9780802130303",
        1944,
        "Jorge Luis Borges",
        ("cuentos", "literatura latinoamericana"),
    ),
    (
        "Como agua para chocolate",
        "9780385420174",
        1989,
        "Laura Esquivel",
        ("novela", "realismo mágico", "ficción histórica"),
    ),
    (
        "La ciudad y los perros",
        "9788432221026",
        1963,
        "Mario Vargas Llosa",
        ("novela", "literatura latinoamericana"),
    ),
)


def _is_valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    weighted_sum = sum(
        int(digit) * (1 if index % 2 == 0 else 3)
        for index, digit in enumerate(isbn[:12])
    )
    return (10 - weighted_sum % 10) % 10 == int(isbn[-1])


def _ensure_user(
    db: Session,
    email: str,
    nombre: str,
    rol: RolUsuario,
) -> Usuario:
    user = (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == email.lower())
        .one_or_none()
    )
    if user is None:
        user = Usuario(
            email=email,
            nombre=nombre,
            password_hash=SecurityService.hash_password(DEMO_PASSWORD),
            rol=rol,
            activo=True,
        )
        db.add(user)
    else:
        user.nombre = nombre
        user.rol = rol
        user.activo = True
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        if not SecurityService.verify_password(DEMO_PASSWORD, user.password_hash):
            user.password_hash = SecurityService.hash_password(DEMO_PASSWORD)
    return user


def _ensure_member(db: Session) -> tuple[Usuario, Socio]:
    user = _ensure_user(db, SOCIO_EMAIL, "Socio de demostración", RolUsuario.socio)
    member_by_email = (
        db.query(Socio)
        .filter(func.lower(Socio.email) == SOCIO_EMAIL.lower())
        .one_or_none()
    )
    if user.socio is not None and member_by_email is not None:
        if user.socio.id != member_by_email.id:
            raise RuntimeError(
                f"El usuario {SOCIO_EMAIL} y el socio con ese correo ya están "
                "vinculados a registros distintos."
            )

    member = user.socio or member_by_email
    if member is None:
        member = Socio(
            nombre="Socio de demostración",
            email=SOCIO_EMAIL,
            telefono=SOCIO_TELEFONO,
            activo=True,
        )
        db.add(member)
        db.flush()
    elif member.usuario is not None and member.usuario.id != user.id:
        raise RuntimeError(
            f"El socio {SOCIO_EMAIL} ya está vinculado a otro usuario."
        )

    member.nombre = "Socio de demostración"
    member.email = SOCIO_EMAIL
    member.telefono = SOCIO_TELEFONO
    member.activo = True
    user.socio = member
    return user, member


def _seed_catalog_if_empty(db: Session) -> None:
    if db.query(Libro.id).first() is not None:
        return

    if not all(_is_valid_isbn13(book[1]) for book in DEMO_BOOKS):
        raise ValueError("El catálogo demo contiene un ISBN-13 inválido.")

    authors: dict[str, Autor] = {}
    for nombre, nacionalidad, anio_nacimiento in DEMO_AUTHORS:
        author = db.query(Autor).filter(Autor.nombre == nombre).one_or_none()
        if author is None:
            author = Autor(
                nombre=nombre,
                nacionalidad=nacionalidad,
                anio_nacimiento=anio_nacimiento,
            )
            db.add(author)
        authors[nombre] = author

    categories: dict[str, Categoria] = {}
    for nombre, descripcion in DEMO_CATEGORIES.items():
        category = (
            db.query(Categoria)
            .filter(func.lower(Categoria.nombre) == nombre)
            .one_or_none()
        )
        if category is None:
            category = Categoria(nombre=nombre, descripcion=descripcion)
            db.add(category)
        categories[nombre] = category

    db.flush()
    for titulo, isbn, anio, author_name, category_names in DEMO_BOOKS:
        db.add(
            Libro(
                titulo=titulo,
                isbn=isbn,
                anio_publicacion=anio,
                ejemplares=3,
                autor=authors[author_name],
                categorias=[categories[name] for name in category_names],
            )
        )
    db.flush()


def _ensure_active_demo_loan(db: Session, member: Socio, admin: Usuario) -> None:
    today = date.today()
    active_loan = (
        db.query(Prestamo)
        .filter(
            Prestamo.socio_id == member.id,
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite >= today,
        )
        .order_by(Prestamo.id)
        .first()
    )
    if active_loan is not None:
        active_loan.registrado_por_id = admin.id
        return

    for book in db.query(Libro).order_by(Libro.id):
        active_loans = (
            db.query(Prestamo)
            .filter(
                Prestamo.libro_id == book.id,
                Prestamo.fecha_devolucion.is_(None),
            )
            .count()
        )
        if book.ejemplares > active_loans:
            db.add(
                Prestamo(
                    libro_id=book.id,
                    socio_id=member.id,
                    fecha_prestamo=today,
                    fecha_limite=today + timedelta(days=14),
                    multa=Decimal("0.00"),
                    multa_pagada=False,
                    registrado_por_id=admin.id,
                )
            )
            return

    raise RuntimeError(
        "No hay ejemplares disponibles para crear el préstamo demo activo."
    )


def _upload_missing_covers(db: Session, settings: Settings) -> None:
    if not all(
        (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    ):
        print("Cloudinary no está configurado; se omiten las portadas remotas.")
        return

    try:
        import cloudinary
        from cloudinary import uploader

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
    except Exception as exc:
        print(f"No se pudieron preparar las portadas de Cloudinary: {type(exc).__name__}.")
        return

    books = (
        db.query(Libro)
        .filter(Libro.portada_url.is_(None))
        .order_by(Libro.id)
        .all()
    )
    for book in books:
        source_url = (
            f"https://covers.openlibrary.org/b/isbn/{book.isbn}-L.jpg?default=false"
        )
        try:
            result = uploader.upload(
                source_url,
                folder="biblioteca/portadas",
            )
        except Exception as exc:
            print(
                f"Portada opcional omitida para ISBN {book.isbn}: "
                f"{type(exc).__name__}."
            )
            continue

        secure_url = result.get("secure_url")
        public_id = result.get("public_id")
        if not isinstance(secure_url, str) or not isinstance(public_id, str):
            print(f"Portada opcional omitida para ISBN {book.isbn}: respuesta incompleta.")
            continue

        book.portada_url = secure_url
        book.portada_public_id = public_id
        db.commit()


def main() -> None:
    settings = get_settings()
    if settings.ENVIRONMENT == "prod":
        raise SystemExit(
            "El seed de demostración está deshabilitado con ENVIRONMENT=prod."
        )

    with SessionLocal() as db:
        admin = _ensure_user(db, ADMIN_EMAIL, "Administrador", RolUsuario.admin)
        member_user, member = _ensure_member(db)
        db.flush()
        _seed_catalog_if_empty(db)
        db.flush()
        _ensure_active_demo_loan(db, member, admin)
        db.commit()
        _upload_missing_covers(db, settings)

    print("Seed de demostración completado.")
    print(f"Administrador: {ADMIN_EMAIL}")
    print(f"Socio: {SOCIO_EMAIL}")


if __name__ == "__main__":
    main()
