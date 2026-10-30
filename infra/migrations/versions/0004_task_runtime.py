"""Durable task table for leased worker dispatch with idempotent enqueue."""
import sqlalchemy as sa
from alembic import op

revision = '0004_task_runtime'
down_revision = '0003_session_commerce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'durable_tasks',
        sa.Column('task_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('operation', sa.String(length=32), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('lease_worker_id', sa.String(length=64), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_error_code', sa.String(length=64), nullable=True),
        sa.Column('context_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_durable_tasks_tenant_id', 'durable_tasks', ['tenant_id'])
    op.create_index('ix_durable_tasks_operation', 'durable_tasks', ['operation'])
    op.create_index('ix_durable_tasks_status', 'durable_tasks', ['status'])


def downgrade() -> None:
    op.drop_table('durable_tasks')
