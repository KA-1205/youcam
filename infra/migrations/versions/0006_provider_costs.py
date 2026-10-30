"""Provider feature cost cache for gated paid submissions."""
import sqlalchemy as sa
from alembic import op

revision = '0006_provider_costs'
down_revision = '0005_asset_privacy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'provider_feature_costs',
        sa.Column('capability', sa.String(length=32), primary_key=True),
        sa.Column('cost_units', sa.Integer(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_version', sa.String(length=64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('provider_feature_costs')
