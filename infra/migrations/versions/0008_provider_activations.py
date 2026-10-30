"""Provider activation evidence register for operator review."""
import sqlalchemy as sa
from alembic import op

revision = '0008_provider_activations'
down_revision = '0007_preview_orchestration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'provider_activations',
        sa.Column('capability', sa.String(length=32), primary_key=True),
        sa.Column('region', sa.String(length=64), nullable=False),
        sa.Column('base_url', sa.String(length=200), nullable=False),
        sa.Column('auth_method', sa.String(length=64), nullable=False),
        sa.Column('feature_version', sa.String(length=64), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('verified_by', sa.String(length=128), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('provider_activations')
