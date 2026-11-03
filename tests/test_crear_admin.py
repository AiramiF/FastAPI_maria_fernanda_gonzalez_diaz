from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RolUsuario, Usuario
from app.scripts import crear_admin


def test_script_crea_admin_sin_exponer_password(
    monkeypatch,
    db_session: Session,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "bootstrap@example.com")
    answers = iter(("TallerAdmin123!", "TallerAdmin123!"))
    monkeypatch.setattr(crear_admin.getpass, "getpass", lambda _: next(answers))

    crear_admin.main()

    user = db_session.scalar(
        select(Usuario).where(func.lower(Usuario.email) == "bootstrap@example.com")
    )
    assert user is not None
    assert user.rol == RolUsuario.admin
    assert user.password_hash != "TallerAdmin123!"


def test_script_no_duplica_admin_existente(monkeypatch, db_session: Session) -> None:
    existing = Usuario(
        email="existing.admin@example.com",
        nombre="Admin",
        password_hash="argon2-test",
        rol=RolUsuario.admin,
        activo=True,
    )
    db_session.add(existing)
    db_session.commit()
    monkeypatch.setattr("builtins.input", lambda _: "EXISTING.ADMIN@example.com")
    monkeypatch.setattr(
        crear_admin.getpass,
        "getpass",
        lambda _: (_ for _ in ()).throw(AssertionError("No debe solicitar contraseña")),
    )

    crear_admin.main()

    users = db_session.scalars(
        select(Usuario).where(func.lower(Usuario.email) == "existing.admin@example.com")
    ).all()
    assert len(users) == 1
