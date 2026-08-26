"""fix missing role column in sessions

Revision ID: 20260826_0004
Revises: 20260825_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0004"
down_revision = "20260825_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("sessions")]

    if "role" not in columns:
        op.add_column(
            "sessions",
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=True
            )
        )

    op.execute("""
        UPDATE sessions
        SET role = users.role
        FROM users
        WHERE sessions.user_id = users.id
          AND sessions.role IS NULL
    """)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("sessions")]

    if "role" in columns:
        op.drop_column("sessions", "role")