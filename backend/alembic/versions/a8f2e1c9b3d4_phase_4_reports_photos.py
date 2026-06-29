"""Phase 4 Reports + Profile Photos

Revision ID: a8f2e1c9b3d4
Revises: fdf6ae469318
Create Date: 2026-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8f2e1c9b3d4'
down_revision: Union[str, None] = 'fdf6ae469318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Reports ──
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Enum(
            'fake_profile', 'harassment', 'inappropriate_photo',
            'spam', 'age_misrepresentation', 'other',
            name='reportreason',
        ), nullable=False),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum(
            'pending', 'investigating', 'resolved', 'dismissed',
            name='reportstatus',
        ), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_reports_target_user_id'), 'reports', ['target_user_id'], unique=False)

    # ── Profile Photos (was already in initial migration but ensure indexes) ──
    # Note: profile_photos table already exists from initial schema.
    # This migration is additive only for reports.


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_target_user_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_table('reports')
