"""Add payment events table

Revision ID: 8f0b9d7c2a1a
Revises: 5b4f2c7a9d11
Create Date: 2026-01-21 12:10:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "8f0b9d7c2a1a"
down_revision = "5b4f2c7a9d11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_event",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("payment_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("payment_event_payment_id_idx", "payment_event", ["payment_id"])


def downgrade():
    op.drop_index("payment_event_payment_id_idx", table_name="payment_event")
    op.drop_table("payment_event")
