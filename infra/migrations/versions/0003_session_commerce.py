"""Styling sessions, commerce authority, outbox and idempotency tables."""
import sqlalchemy as sa
from alembic import op

revision = '0003_session_commerce'
down_revision = '0002_access_profile'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'styling_sessions',
        sa.Column('session_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('owner_actor_id', sa.String(length=64), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('brief_json', sa.JSON(), nullable=False),
        sa.Column('anchors_json', sa.JSON(), nullable=False),
        sa.Column('locks_json', sa.JSON(), nullable=False),
        sa.Column('rejected_ids_json', sa.JSON(), nullable=False),
        sa.Column('selections_json', sa.JSON(), nullable=False),
        sa.Column('claimed_by_account', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_styling_sessions_tenant_id', 'styling_sessions', ['tenant_id'])
    op.create_index('ix_styling_sessions_owner_actor_id', 'styling_sessions', ['owner_actor_id'])
    op.create_table(
        'cart_quotes',
        sa.Column('quote_id', sa.String(length=64), primary_key=True),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('quote_version', sa.Integer(), nullable=False),
        sa.Column('lines_json', sa.JSON(), nullable=False),
        sa.Column('merchandise_minor', sa.Integer(), nullable=False),
        sa.Column('shipping_minor', sa.Integer(), nullable=False),
        sa.Column('tax_minor', sa.Integer(), nullable=False),
        sa.Column('total_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('mode', sa.String(length=8), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_cart_quotes_actor_id', 'cart_quotes', ['actor_id'])
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('order_version', sa.Integer(), nullable=False),
        sa.Column('event_sequence', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('lines_json', sa.JSON(), nullable=False),
        sa.Column('total_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('mode', sa.String(length=8), nullable=False),
        sa.Column('return_status', sa.String(length=16), nullable=False),
        sa.Column('quote_id', sa.String(length=64), nullable=False),
        sa.Column('reservation_id', sa.String(length=64), nullable=True),
        sa.Column('payment_reference', sa.String(length=128), nullable=False),
        sa.Column('address_reference', sa.String(length=128), nullable=False),
        sa.Column('payment_attempt_id', sa.String(length=64), nullable=True),
        sa.Column('stock_restored', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_orders_tenant_id', 'orders', ['tenant_id'])
    op.create_index('ix_orders_actor_id', 'orders', ['actor_id'])
    op.create_index('ix_orders_account_id', 'orders', ['account_id'])
    op.create_table(
        'payment_attempts',
        sa.Column('attempt_id', sa.String(length=64), primary_key=True),
        sa.Column('order_id', sa.String(length=64), nullable=False),
        sa.Column('intent_id', sa.String(length=64), nullable=False),
        sa.Column('reference', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('mode', sa.String(length=8), nullable=False),
        sa.Column('scripted_outcome', sa.String(length=24), nullable=False),
        sa.Column('action_text', sa.String(length=200), nullable=True),
        sa.Column('error_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_payment_attempts_order_id', 'payment_attempts', ['order_id'])
    op.create_table(
        'warehouse_stock',
        sa.Column('variant_id', sa.String(length=128), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('available', sa.Integer(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_version', sa.String(length=64), nullable=False),
    )
    op.create_table(
        'warehouse_reservations',
        sa.Column('reservation_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('lines_json', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('mode', sa.String(length=8), nullable=False),
        sa.Column('consumed', sa.Boolean(), nullable=False),
        sa.Column('released', sa.Boolean(), nullable=False),
        sa.Column('restored', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'outbox_events',
        sa.Column('event_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.String(length=64), nullable=False),
        sa.Column('event_sequence', sa.Integer(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_outbox_events_order_id', 'outbox_events', ['order_id'])
    op.create_table(
        'idempotency_keys',
        sa.Column('idempotency_key', sa.String(length=64), primary_key=True),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('operation', sa.String(length=64), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('response_json', sa.JSON(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for name in ('idempotency_keys', 'outbox_events', 'warehouse_reservations', 'warehouse_stock',
                 'payment_attempts', 'orders', 'cart_quotes', 'styling_sessions'):
        op.drop_table(name)
