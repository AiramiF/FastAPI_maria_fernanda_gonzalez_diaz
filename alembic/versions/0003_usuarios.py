"""usuarios

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-02 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    rolusuario = sa.Enum("admin", "bibliotecario", "socio", name="rolusuario")
    rolusuario.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("admin", "bibliotecario", "socio", name="rolusuario", create_type=False),
            nullable=False,
            server_default="socio",
        ),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("intentos_fallidos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("socio_id", sa.Integer(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["socio_id"], ["socios.id"], name=op.f("fk_usuarios_socio_id_socios")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuarios")),
        sa.UniqueConstraint("socio_id", name=op.f("uq_usuarios_socio_id")),
    )
    op.execute("CREATE UNIQUE INDEX ix_usuarios_email_lower ON usuarios (LOWER(email));")


def downgrade() -> None:
    op.drop_index("ix_usuarios_email_lower", table_name="usuarios")
    op.drop_table("usuarios")
    sa.Enum(name="rolusuario").drop(op.get_bind())
