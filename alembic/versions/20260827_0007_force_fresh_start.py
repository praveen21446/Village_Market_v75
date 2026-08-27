"""Force a clean marketplace start while preserving admin accounts.

Revision ID: 20260827_0007
Revises: 20260827_0006
"""
from alembic import op

revision = "20260827_0007"
down_revision = "20260827_0006"
branch_labels = None
depends_on = None


def upgrade():
    # Clear every user-generated marketplace record in FK-safe order.
    op.execute("DELETE FROM reviews")
    op.execute("DELETE FROM support_messages")
    op.execute("DELETE FROM support_tickets")
    op.execute("DELETE FROM notifications")
    op.execute("DELETE FROM saved_addresses")
    op.execute("DELETE FROM bookings")
    op.execute("DELETE FROM crops")
    op.execute("DELETE FROM otp_codes")
    op.execute("DELETE FROM sessions")

    # Preserve only users that own an admin account. Remove stale creator links first.
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

    # Reset IDs for emptied tables; keep users above existing admin IDs.
    for table in [
        "reviews", "support_messages", "support_tickets", "notifications",
        "saved_addresses", "bookings", "crops", "otp_codes"
    ]:
        op.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)")
    op.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1), true)")


def downgrade():
    # Deleted marketplace data cannot be reconstructed.
    pass
