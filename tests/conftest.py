from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.dependencies import get_db
from app.core.rate_limit import limiter
from app.core.security import SecurityService
from app.main import app
from app.models import Autor, Categoria, Libro, RolUsuario, Socio, Usuario

PASSWORD = "TallerTest123!"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[None, None, None]:
    settings = get_settings()
    if settings.ENVIRONMENT != "test":
        raise RuntimeError("Las pruebas requieren ENVIRONMENT=test")
    if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL debe ser distinta de DATABASE_URL")

    alembic_cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    try:
        yield
    finally:
        command.downgrade(alembic_cfg, "base")
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_test_state(migrated_database: None) -> Generator[None, None, None]:
    limiter.reset()
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE refresh_tokens, prestamos, libro_categoria, "
                "libros, categorias, autores, usuarios, socios "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def create_user(
    db_session: Session,
    role: RolUsuario,
    *,
    name: str,
    email: str | None = None,
) -> Usuario:
    email = email or f"{role.value}_{uuid4().hex[:8]}@example.com"
    socio = None
    if role == RolUsuario.socio:
        socio = Socio(
            nombre=name,
            email=email,
            telefono="5551234",
        )
    user = Usuario(
        email=email,
        nombre=name,
        password_hash=SecurityService.hash_password(PASSWORD),
        rol=role,
        activo=True,
        socio=socio,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin(db_session: Session) -> Usuario:
    return create_user(db_session, RolUsuario.admin, name="Admin")


@pytest.fixture()
def bibliotecario(db_session: Session) -> Usuario:
    return create_user(db_session, RolUsuario.bibliotecario, name="Bibliotecario")


@pytest.fixture()
def ana_user(db_session: Session) -> Usuario:
    return create_user(
        db_session,
        RolUsuario.socio,
        name="Ana",
        email="ana@example.com",
    )


@pytest.fixture()
def luis_user(db_session: Session) -> Usuario:
    return create_user(
        db_session,
        RolUsuario.socio,
        name="Luis",
        email="luis@example.com",
    )


@pytest.fixture()
def ana(ana_user: Usuario) -> Socio:
    assert ana_user.socio is not None
    return ana_user.socio


@pytest.fixture()
def luis(luis_user: Usuario) -> Socio:
    assert luis_user.socio is not None
    return luis_user.socio


@pytest.fixture()
def admin_headers(client: TestClient, admin: Usuario) -> dict[str, str]:
    return login_headers(client, admin.email)


@pytest.fixture()
def bibliotecario_headers(
    client: TestClient, bibliotecario: Usuario
) -> dict[str, str]:
    return login_headers(client, bibliotecario.email)


@pytest.fixture()
def ana_headers(client: TestClient, ana_user: Usuario) -> dict[str, str]:
    return login_headers(client, ana_user.email)


@pytest.fixture()
def luis_headers(client: TestClient, luis_user: Usuario) -> dict[str, str]:
    return login_headers(client, luis_user.email)


@pytest.fixture()
def catalog(db_session: Session) -> tuple[Libro, Libro]:
    author = Autor(nombre="Autora de Prueba")
    category = Categoria(nombre="Pruebas")
    first = Libro(
        titulo="Libro Uno",
        isbn="1111111111111",
        anio_publicacion=2020,
        ejemplares=3,
        autor=author,
        categorias=[category],
    )
    second = Libro(
        titulo="Libro Dos",
        isbn="2222222222222",
        anio_publicacion=2021,
        ejemplares=3,
        autor=author,
        categorias=[category],
    )
    db_session.add_all([first, second])
    db_session.commit()
    db_session.refresh(first)
    db_session.refresh(second)
    return first, second
