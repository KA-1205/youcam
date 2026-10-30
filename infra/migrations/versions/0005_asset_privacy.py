"""Asset and retention-audit tables for the privacy lifecycle."""
import sqlalchemy as sa
from alembic import op

revision = '0005_asset_privacy'
down_revision = '0004_task_runtime'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assets',
        sa.Column('asset_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('account_id', sa.String(length=64), nullable=True),
        sa.Column('capability', sa.String(length=32), nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=False),
        sa.Column('byte_length', sa.Integer(), nullable=False),
        sa.Column('digest', sa.String(length=64), nullable=False),
        sa.Column('storage_key', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('saved', sa.Boolean(), nullable=False),
        sa.Column('last_saved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_assets_tenant_id', 'assets', ['tenant_id'])
    op.create_index('ix_assets_actor_id', 'assets', ['actor_id'])
    op.create_table(
        'retention_events',
        sa.Column('event_id', sa.String(length=64), primary_key=True),
        sa.Column('asset_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_retention_events_asset_id', 'retention_events', ['asset_id'])


def downgrade() -> None:
    op.drop_table('retention_events')
    op.drop_table('assets')
