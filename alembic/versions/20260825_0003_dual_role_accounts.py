"""Allow the same phone number to have buyer and farmer accounts.

Revision ID: 20260825_0003
Revises: 20260824_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20260825_0003"
down_revision = "20260824_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_index('ix_users_phone', table_name='users')
        op.drop_constraint('users_phone_key', 'users', type_='unique')
        op.create_index('ix_users_phone', 'users', ['phone'], unique=False)
        op.create_unique_constraint('uq_users_phone_role', 'users', ['phone','role'])
    else:
        with op.batch_alter_table('users', recreate='always') as batch:
            try:
                batch.drop_index('ix_users_phone')
            except Exception:
                pass
            batch.create_index('ix_users_phone', ['phone'], unique=False)
            batch.create_unique_constraint('uq_users_phone_role', ['phone','role'])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_constraint('uq_users_phone_role', 'users', type_='unique')
        op.drop_index('ix_users_phone', table_name='users')
        op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
        op.create_unique_constraint('users_phone_key', 'users', ['phone'])
    else:
        with op.batch_alter_table('users', recreate='always') as batch:
            batch.drop_constraint('uq_users_phone_role', type_='unique')
            batch.drop_index('ix_users_phone')
            batch.create_index('ix_users_phone', ['phone'], unique=True)
