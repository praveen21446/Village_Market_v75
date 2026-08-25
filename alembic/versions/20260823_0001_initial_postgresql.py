"""Initial Village Market production schema.

Revision ID: 20260823_0001
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "20260823_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(180)),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("phone"))
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    op.create_table("admin_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("admin_id"), sa.UniqueConstraint("user_id"))
    op.create_index("ix_admin_accounts_admin_id", "admin_accounts", ["admin_id"], unique=True)

    op.create_table("otp_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])

    op.create_table("sessions",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))

    op.create_table("crops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("available_kg", sa.Float(), nullable=False),
        sa.Column("location", sa.String(240), nullable=False),
        sa.Column("address_line", sa.String(240)), sa.Column("village", sa.String(100)),
        sa.Column("mandal", sa.String(100)), sa.Column("district", sa.String(100)),
        sa.Column("state", sa.String(100)), sa.Column("pincode", sa.String(10)),
        sa.Column("landmark", sa.String(180)), sa.Column("latitude", sa.String(30)),
        sa.Column("longitude", sa.String(30)), sa.Column("expected_price", sa.Float(), nullable=False),
        sa.Column("quality", sa.String(50), nullable=False), sa.Column("harvest_date", sa.String(20), nullable=False),
        sa.Column("details", sa.Text()), sa.Column("photo", sa.String(255)),
        sa.Column("status", sa.String(20)), sa.Column("market_price", sa.Float()),
        sa.Column("admin_note", sa.Text()), sa.Column("low_stock_threshold", sa.Float()),
        sa.Column("created_at", sa.DateTime()))

    op.create_table("bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False), sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("final_price", sa.Float()), sa.Column("farmer_note", sa.Text()),
        sa.Column("status", sa.String(25)), sa.Column("payment_status", sa.String(20)),
        sa.Column("delivery_method", sa.String(20)), sa.Column("delivery_address", sa.Text()),
        sa.Column("delivery_latitude", sa.String(30)), sa.Column("delivery_longitude", sa.String(30)),
        sa.Column("payment_reference", sa.String(120)), sa.Column("delivery_otp", sa.String(6)),
        sa.Column("delivered_at", sa.DateTime()), sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()))

    op.create_table("reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("crop_id", sa.Integer(), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False), sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime()), sa.UniqueConstraint("booking_id"))

    op.create_table("notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False), sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean()), sa.Column("created_at", sa.DateTime()))

    op.create_table("saved_addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False), sa.Column("label", sa.String(100)),
        sa.Column("data_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime()))
    op.create_index("ix_saved_addresses_user_id", "saved_addresses", ["user_id"])
    op.create_index("ix_saved_addresses_kind", "saved_addresses", ["kind"])


def downgrade():
    op.drop_index("ix_saved_addresses_kind", table_name="saved_addresses")
    op.drop_index("ix_saved_addresses_user_id", table_name="saved_addresses")
    op.drop_table("saved_addresses")
    op.drop_table("notifications")
    op.drop_table("reviews")
    op.drop_table("bookings")
    op.drop_table("crops")
    op.drop_table("sessions")
    op.drop_index("ix_otp_codes_phone", table_name="otp_codes")
    op.drop_table("otp_codes")
    op.drop_index("ix_admin_accounts_admin_id", table_name="admin_accounts")
    op.drop_table("admin_accounts")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
