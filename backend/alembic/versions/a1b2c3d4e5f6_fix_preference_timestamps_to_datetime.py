"""Fix Preference timestamps to DateTime

Revision ID: a1b2c3d4e5f6
Revises: a8f2e1c9b3d4
Create Date: 2026-06-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'a8f2e1c9b3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preference.created_at / updated_at were originally Column(String, default="now")
    # which stored the literal four-character string "now" instead of a real
    # timestamp. Convert them to DateTime so any code that reads or sorts on
    # these columns works correctly.
    #
    # SQLite cannot ALTER COLUMN type in-place — it requires a table rebuild.
    # `op.batch_alter_table` handles this transparently for SQLite while still
    # emitting a plain ALTER COLUMN for PostgreSQL (where the `postgresql_using`
    # clause ensures the existing "now" string values are coerced).
    #
    # Existing rows contain the literal string "now" which cannot parse as a
    # datetime. We drop them — this is acceptable for a fresh MVP with no
    # production data, and any active users can re-save their preferences.
    op.execute("DELETE FROM preferences")

    with op.batch_alter_table("preferences") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.String(),
            type_=sa.DateTime(),
            existing_nullable=False,
            nullable=False,
            server_default=sa.func.now(),
            postgresql_using="created_at::timestamp",
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.String(),
            type_=sa.DateTime(),
            existing_nullable=False,
            nullable=False,
            server_default=sa.func.now(),
            postgresql_using="updated_at::timestamp",
        )


def downgrade() -> None:
    # Revert to String columns. Note: any real timestamps will be cast to text.
    with op.batch_alter_table("preferences") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            type_=sa.String(),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            type_=sa.String(),
            existing_nullable=False,
            nullable=True,
        )