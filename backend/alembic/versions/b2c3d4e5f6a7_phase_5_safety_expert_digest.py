"""Phase 5 — safety (blocks, banned phones), expert sessions,
Personal Care mode, digest consent, profile height.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: weekly digest consent (Epic G2) ─────────────
    op.add_column(
        'users',
        sa.Column('email_digest_opt_in', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # ── profiles: height (used by preference matching) ─────
    op.add_column('profiles', sa.Column('height_cm', sa.Integer(), nullable=True))

    # ── safety: panic block ─────────────────────────────────
    op.create_table(
        'user_blocks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('blocker_user_id', sa.Integer(), nullable=False),
        sa.Column('blocked_user_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['blocker_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['blocked_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_user_id', 'blocked_user_id', name='uq_user_block_pair'),
    )
    op.create_index('ix_user_blocks_blocker_user_id', 'user_blocks', ['blocker_user_id'])
    op.create_index('ix_user_blocks_blocked_user_id', 'user_blocks', ['blocked_user_id'])

    # ── safety: banned phone blocklist (Epic J2) ────────────
    op.create_table(
        'banned_phones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('banned_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['banned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_banned_phones_phone', 'banned_phones', ['phone'], unique=True)

    # ── expert sessions (Epic I1) ───────────────────────────
    op.create_table(
        'expert_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expert_user_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.Enum('matchmaking', 'astrology', 'profile_writing', 'other', name='expertcategory'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('requested', 'confirmed', 'completed', 'cancelled', name='sessionstatus'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['expert_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_expert_sessions_user_id', 'expert_sessions', ['user_id'])
    op.create_index('ix_expert_sessions_scheduled_at', 'expert_sessions', ['scheduled_at'])

    # ── Personal Care mode (Epic I2) ────────────────────────
    op.create_table(
        'care_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expert_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', 'closed', name='carestatus'), nullable=False),
        sa.Column('service_fee', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['expert_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_care_assignments_user_id', 'care_assignments', ['user_id'])

    op.create_table(
        'care_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('is_done', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['care_assignments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_care_tasks_assignment_id', 'care_tasks', ['assignment_id'])

    op.create_table(
        'care_call_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('called_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['care_assignments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_care_call_logs_assignment_id', 'care_call_logs', ['assignment_id'])


def downgrade() -> None:
    op.drop_table('care_call_logs')
    op.drop_table('care_tasks')
    op.drop_table('care_assignments')
    op.drop_table('expert_sessions')
    op.drop_table('banned_phones')
    op.drop_table('user_blocks')
    op.drop_column('profiles', 'height_cm')
    op.drop_column('users', 'email_digest_opt_in')
