"""OTP codes bound to the requesting device, and a per-phone lock row
for atomic OTP throttling.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sha256 of the requesting browser's otp_device cookie. Codes issued
    # before this migration have none, so they can no longer be checked:
    # anyone mid-login at deploy time requests a new code.
    op.add_column('otp_logs', sa.Column('device_hash', sa.String(length=64), nullable=True))

    op.create_table(
        'otp_phone_locks',
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('phone'),
    )


def downgrade() -> None:
    op.drop_table('otp_phone_locks')
    op.drop_column('otp_logs', 'device_hash')
