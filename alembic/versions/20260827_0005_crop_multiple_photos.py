"""add multiple crop photos

Revision ID: 20260827_0005
Revises: 20260826_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_0005"
down_revision = "20260826_0004"
branch_labels = None
depends_on = None

def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    columns=[c["name"] for c in inspector.get_columns("crops")]
    if "photos_json" not in columns:
        op.add_column("crops",sa.Column("photos_json",sa.Text(),nullable=True))
    op.execute("UPDATE crops SET photos_json = '[]' WHERE photos_json IS NULL OR photos_json = ''")

def downgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    columns=[c["name"] for c in inspector.get_columns("crops")]
    if "photos_json" in columns:
        op.drop_column("crops","photos_json")
