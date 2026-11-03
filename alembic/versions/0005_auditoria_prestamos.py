"""auditoria prestamos

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-02 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columnas = {col["name"] for col in inspector.get_columns("prestamos")}

    if "multa_pagada" not in columnas:
        op.add_column(
            "prestamos",
            sa.Column(
                "multa_pagada",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        op.execute("UPDATE prestamos SET multa_pagada = true WHERE multa = 0")
        op.alter_column("prestamos", "multa_pagada", server_default=None)

    if "registrado_por_id" not in columnas:
        op.add_column(
            "prestamos",
            sa.Column("registrado_por_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            op.f("fk_prestamos_registrado_por_id_usuarios"),
            "prestamos",
            "usuarios",
            ["registrado_por_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columnas = {col["name"] for col in inspector.get_columns("prestamos")}

    if "registrado_por_id" in columnas:
        op.drop_constraint(
            op.f("fk_prestamos_registrado_por_id_usuarios"),
            "prestamos",
            type_="foreignkey",
        )
        op.drop_column("prestamos", "registrado_por_id")

    if "multa_pagada" in columnas:
        op.drop_column("prestamos", "multa_pagada")
