"""Durable live-provider receipts and atomic conservative credit budget."""
import sqlalchemy as sa
from alembic import op

revision = '0009_live_delivery'
down_revision = '0008_provider_activations'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('provider_live_steps',
                    sa.Column('child_id', sa.String(64), primary_key=True),
                    sa.Column('payload', sa.JSON(), nullable=False),
                    sa.Column('reserved_units', sa.Integer(), nullable=False),
                    sa.Column('submit_started', sa.Boolean(), nullable=False),
                    sa.Column('next_poll_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('deleted', sa.Boolean(), nullable=False))
    op.create_table('provider_credit_budget',
                    sa.Column('budget_id', sa.String(32), primary_key=True),
                    sa.Column('reserved_units', sa.Integer(), nullable=False))
    op.execute("INSERT INTO provider_credit_budget (budget_id, reserved_units) VALUES ('youcam', 0)")


def downgrade():
    op.drop_table('provider_live_steps')
    op.drop_table('provider_credit_budget')
