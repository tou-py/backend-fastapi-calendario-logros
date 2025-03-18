"""Corrige la relacion entre Activity y ActivityType

Revision ID: 5a38b9a78306
Revises: bcdd01d51442
Create Date: 2025-03-18 08:35:04.631054

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a38b9a78306"
down_revision: Union[str, None] = "bcdd01d51442"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Modificación para usar el modo "batch" en SQLite ###
    with op.batch_alter_table("activities") as batch_op:
        # Agregar la columna type_id
        batch_op.add_column(sa.Column("type_id", sa.String(), nullable=False))
        # Crear la clave foránea
        batch_op.create_foreign_key(
            op.f("fk_activities_type_id"),  # Nombre de la restricción
            "activity_types",  # Tabla de referencia
            ["type_id"],  # Columna en la tabla actual
            ["id"],  # Columna en la tabla de referencia
        )

    with op.batch_alter_table("activity_types") as batch_op:
        # Eliminar la clave foránea antigua
        batch_op.drop_constraint("fk_activity_types_activity_id", type_="foreignkey")
        # Eliminar la columna activity_id
        batch_op.drop_column("activity_id")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### Modificación para usar el modo "batch" en SQLite ###
    with op.batch_alter_table("activity_types") as batch_op:
        # Agregar la columna activity_id
        batch_op.add_column(sa.Column("activity_id", sa.String(), nullable=False))
        # Crear la clave foránea antigua
        batch_op.create_foreign_key(
            "fk_activity_types_activity_id",  # Nombre de la restricción
            "activities",  # Tabla de referencia
            ["activity_id"],  # Columna en la tabla actual
            ["id"],  # Columna en la tabla de referencia
        )

    with op.batch_alter_table("activities") as batch_op:
        # Eliminar la clave foránea nueva
        batch_op.drop_constraint(op.f("fk_activities_type_id"), type_="foreignkey")
        # Eliminar la columna type_id
        batch_op.drop_column("type_id")
    # ### end Alembic commands ###
