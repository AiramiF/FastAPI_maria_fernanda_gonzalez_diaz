import getpass

from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.security import SecurityService
from app.models.usuario import RolUsuario, Usuario


def main() -> None:
    email = input("Correo del administrador: ").strip().lower()
    if not email:
        print("El correo es obligatorio.")
        return

    with SessionLocal() as db:
        existe = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()
        if existe is not None:
            print(f"El usuario {email} ya existe. No se crea un administrador nuevo.")
            return

        password = getpass.getpass("Contraseña: ")
        confirmar = getpass.getpass("Confirmar contraseña: ")
        if password != confirmar:
            print("Las contraseñas no coinciden.")
            return

        administrador = Usuario(
            email=email,
            nombre="Administrador",
            password_hash=SecurityService.hash_password(password),
            rol=RolUsuario.admin,
            activo=True,
        )
        db.add(administrador)
        db.commit()
        print(f"Administrador creado: {email}")


if __name__ == "__main__":
    main()
