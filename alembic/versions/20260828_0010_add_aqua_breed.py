from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260828_0010"
down_revision = "20260827_0009"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("crops")]
    if "breed" not in columns:
        op.add_column("crops", sa.Column("breed", sa.String(length=120), nullable=True, server_default=""))

def downgrade():
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns("crops")]
    if "breed" in columns:
        op.drop_column("crops", "breed")
