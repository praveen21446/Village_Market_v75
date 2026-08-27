"""One-time fresh start: clear marketplace user data while preserving admins.

Revision ID: 20260827_0006
Revises: 20260827_0005

This migration is intentionally destructive for marketplace data. It preserves
admin_accounts and their linked superadmin users so the admin console remains
accessible after the reset.
"""
from alembic import op

revision = "20260827_0006"
down_revision = "20260827_0005"
branch_labels = None
depends_on = None


def upgrade():
    # Delete child rows before parents to respect foreign keys.
    op.execute("DELETE FROM reviews")
    op.execute("DELETE FROM support_messages")
    op.execute("DELETE FROM support_tickets")
    op.execute("DELETE FROM notifications")
    op.execute("DELETE FROM saved_addresses")
    op.execute("DELETE FROM bookings")
    op.execute("DELETE FROM crops")
    op.execute("DELETE FROM otp_codes")
    op.execute("DELETE FROM sessions")

    # Keep admins and the users attached to admin_accounts; remove buyers/farmers.
    op.execute("""
        DELETE FROM users
        WHERE role <> 'superadmin'
          AND id NOT IN (SELECT user_id FROM admin_accounts)
    """)


def downgrade():
    # Deleted production/user data cannot be reconstructed by a downgrade.
    pass
