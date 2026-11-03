"""multa pagada

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columnas = {col["name"] for col in inspector.get_columns("prestamos")}

    if "multa_pagada" in columnas:
        op.drop_column("prestamos", "multa_pagada")
