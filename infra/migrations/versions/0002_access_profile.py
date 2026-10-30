"""Durable access and profile tables: tenants, accounts, actors, consent, wardrobe.

Portable column types keep the same migration valid on PostgreSQL and SQLite.
"""
import sqlalchemy as sa
from alembic import op

revision = '0002_access_profile'
down_revision = '0001_foundation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tenants',
        sa.Column('tenant_id', sa.String(length=64), primary_key=True),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'accounts',
        sa.Column('account_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64),
                  sa.ForeignKey('tenants.tenant_id', name='fk_account_tenant'), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferences_json', sa.JSON(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_account_email'),
    )
    op.create_index('ix_accounts_tenant_id', 'accounts', ['tenant_id'])
    op.create_table(
        'account_roles',
        sa.Column('account_id', sa.String(length=64),
                  sa.ForeignKey('accounts.account_id', name='fk_role_account',
                                ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(length=32), primary_key=True),
    )
    op.create_table(
        'actors',
        sa.Column('actor_id', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64),
                  sa.ForeignKey('tenants.tenant_id', name='fk_actor_tenant'), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('account_id', sa.String(length=64),
                  sa.ForeignKey('accounts.account_id', name='fk_actor_account'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_actors_tenant_id', 'actors', ['tenant_id'])
    op.create_index('ix_actors_account_id', 'actors', ['account_id'])
    op.create_table(
        'auth_sessions',
        sa.Column('token_hash', sa.String(length=64), primary_key=True),
        sa.Column('tenant_id', sa.String(length=64),
                  sa.ForeignKey('tenants.tenant_id', name='fk_auth_tenant'), nullable=False),
        sa.Column('actor_id', sa.String(length=64),
                  sa.ForeignKey('actors.actor_id', name='fk_auth_actor'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_auth_sessions_tenant_id', 'auth_sessions', ['tenant_id'])
    op.create_index('ix_auth_sessions_actor_id', 'auth_sessions', ['actor_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    op.create_table(
        'consent_revisions',
        sa.Column('actor_id', sa.String(length=64), primary_key=True),
        sa.Column('revision', sa.Integer(), primary_key=True),
        sa.Column('controls_json', sa.JSON(), nullable=False),
        sa.Column('processors_json', sa.JSON(), nullable=False),
        sa.Column('asset_ids_json', sa.JSON(), nullable=False),
        sa.Column('adult_attestation', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('actor_id', 'revision', name='uq_consent_revision'),
    )
    op.create_table(
        'wardrobe_items',
        sa.Column('wardrobe_id', sa.String(length=64), primary_key=True),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('ref_type', sa.String(length=16), nullable=False),
        sa.Column('ref_id', sa.String(length=128), nullable=False),
        sa.Column('slot', sa.String(length=16), nullable=False),
        sa.Column('saved', sa.Boolean(), nullable=False),
        sa.Column('manual_owned_quantity', sa.Integer(), nullable=False),
        sa.Column('attributes_confirmed', sa.Boolean(), nullable=False),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('account_id', 'ref_type', 'ref_id', name='uq_wardrobe_reference'),
    )
    op.create_index('ix_wardrobe_items_account_id', 'wardrobe_items', ['account_id'])
    op.create_table(
        'wardrobe_contributions',
        sa.Column('order_line_id', sa.String(length=64), primary_key=True),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.String(length=64), nullable=False),
        sa.Column('ref_type', sa.String(length=16), nullable=False),
        sa.Column('ref_id', sa.String(length=128), nullable=False),
        sa.Column('slot', sa.String(length=16), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=16), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_wardrobe_contributions_account_id', 'wardrobe_contributions',
                    ['account_id'])
    op.create_index('ix_wardrobe_contributions_order_id', 'wardrobe_contributions', ['order_id'])
    op.create_table(
        'commerce_events',
        sa.Column('event_id', sa.String(length=64), primary_key=True),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.String(length=64), nullable=False),
        sa.Column('order_version', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_commerce_events_account_id', 'commerce_events', ['account_id'])
    op.create_index('ix_commerce_events_order_id', 'commerce_events', ['order_id'])
    op.create_table(
        'order_progress',
        sa.Column('order_id', sa.String(length=64), primary_key=True),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('applied_version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_order_progress_account_id', 'order_progress', ['account_id'])
    op.execute("INSERT INTO tenants (tenant_id, display_name, created_at) "
               "VALUES ('demo-anchor-fit', 'Anchor Fit — simulated store', CURRENT_TIMESTAMP)")


def downgrade() -> None:
    for name in ('order_progress', 'commerce_events', 'wardrobe_contributions', 'wardrobe_items',
                 'consent_revisions', 'auth_sessions', 'actors', 'account_roles', 'accounts',
                 'tenants'):
        op.drop_table(name)
