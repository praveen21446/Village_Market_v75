"""session selected role for buyer/farmer dual login

Revision ID: 20260825_0003
Revises: 20260824_0002
"""
from alembic import op
import sqlalchemy as sa
revision='20260825_0003'
down_revision='20260824_0002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('sessions',sa.Column('role',sa.String(length=20),nullable=True))
    op.execute("UPDATE sessions SET role=(SELECT role FROM users WHERE users.id=sessions.user_id) WHERE role IS NULL")

def downgrade():
    op.drop_column('sessions','role')
