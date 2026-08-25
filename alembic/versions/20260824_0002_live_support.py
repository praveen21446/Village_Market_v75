"""Add live support tickets and messages.

Revision ID: 20260824_0002
Revises: 20260823_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20260824_0002"
down_revision = "20260823_0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("support_tickets",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("subject",sa.String(120),nullable=False),
        sa.Column("category",sa.String(40),nullable=False),
        sa.Column("status",sa.String(20),nullable=False),
        sa.Column("created_at",sa.DateTime()),
        sa.Column("updated_at",sa.DateTime()))
    op.create_index("ix_support_tickets_user_id","support_tickets",["user_id"])
    op.create_index("ix_support_tickets_status","support_tickets",["status"])
    op.create_table("support_messages",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("ticket_id",sa.Integer(),sa.ForeignKey("support_tickets.id"),nullable=False),
        sa.Column("sender_user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("sender_role",sa.String(20),nullable=False),
        sa.Column("message",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime()))
    op.create_index("ix_support_messages_ticket_id","support_messages",["ticket_id"])

def downgrade():
    op.drop_index("ix_support_messages_ticket_id",table_name="support_messages")
    op.drop_table("support_messages")
    op.drop_index("ix_support_tickets_status",table_name="support_tickets")
    op.drop_index("ix_support_tickets_user_id",table_name="support_tickets")
    op.drop_table("support_tickets")
