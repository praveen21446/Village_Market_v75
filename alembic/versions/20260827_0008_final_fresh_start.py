"""Final clean marketplace reset while preserving admin accounts.

Revision ID: 20260827_0008
Revises: 20260827_0007
"""
from alembic import op

revision = "20260827_0008"
down_revision = "20260827_0007"
branch_labels = None
depends_on = None


def upgrade():
    # Final requested clean start: remove every buyer/farmer marketplace record.
    op.execute("DELETE FROM reviews")
    op.execute("DELETE FROM support_messages")
    op.execute("DELETE FROM support_tickets")
    op.execute("DELETE FROM notifications")
    op.execute("DELETE FROM saved_addresses")
    op.execute("DELETE FROM bookings")
    op.execute("DELETE FROM crops")
    op.execute("DELETE FROM otp_codes")
    op.execute("DELETE FROM sessions")
    op.execute("""
        UPDATE admin_accounts
        SET created_by_user_id = NULL
        WHERE created_by_user_id IS NOT NULL
          AND created_by_user_id NOT IN (SELECT user_id FROM admin_accounts)
    """)
    op.execute("""
        DELETE FROM users
        WHERE id NOT IN (SELECT user_id FROM admin_accounts)
    """)
    for table in [
        "reviews", "support_messages", "support_tickets", "notifications",
        "saved_addresses", "bookings", "crops", "otp_codes"
    ]:
        op.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)")
    op.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1), true)")


def downgrade():
    pass
