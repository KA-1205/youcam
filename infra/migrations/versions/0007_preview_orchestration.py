"""Preview orchestration tables: jobs, provider child tasks and visitor quotas."""
import sqlalchemy as sa
from alembic import op

revision = '0007_preview_orchestration'
down_revision = '0006_provider_costs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'preview_jobs',
        sa.Column('job_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('consent_revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('freshness', sa.String(length=16), nullable=False),
        sa.Column('execution_mode', sa.String(length=8), nullable=False),
        sa.Column('capability', sa.String(length=32), nullable=False),
        sa.Column('source_asset_id', sa.String(length=64), nullable=False),
        sa.Column('selections_json', sa.JSON(), nullable=False),
        sa.Column('effect_ids_json', sa.JSON(), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=False),
        sa.Column('error_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_preview_jobs_tenant_id', 'preview_jobs', ['tenant_id'])
    op.create_index('ix_preview_jobs_actor_id', 'preview_jobs', ['actor_id'])
    op.create_index('ix_preview_jobs_status', 'preview_jobs', ['status'])
    op.create_table(
        'preview_child_tasks',
        sa.Column('child_task_id', sa.String(length=64), primary_key=True),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('capability', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('source_asset_id', sa.String(length=64), nullable=False),
        sa.Column('result_asset_id', sa.String(length=64), nullable=True),
        sa.Column('applied_items_json', sa.JSON(), nullable=False),
        sa.Column('unknown_charge_reserved', sa.Boolean(), nullable=False),
        sa.Column('provider_task_id', sa.String(length=64), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_preview_child_tasks_job_id', 'preview_child_tasks', ['job_id'])
    op.create_table(
        'preview_quota_counters',
        sa.Column('counter_id', sa.String(length=64), primary_key=True),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('day', sa.String(length=10), nullable=False),
        sa.Column('paid_intents', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('actor_id', 'day', name='uq_quota_actor_day'),
    )
    op.create_table(
        'preview_active_jobs',
        sa.Column('actor_id', sa.String(length=64), primary_key=True),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('preview_active_jobs')
    op.drop_table('preview_quota_counters')
    op.drop_table('preview_child_tasks')
    op.drop_table('preview_jobs')
