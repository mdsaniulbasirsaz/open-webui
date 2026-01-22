"""Add payment transactions table

Revision ID: 5b4f2c7a9d11
Revises: c9f0c2b1d5a7
Create Date: 2026-01-21 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "5b4f2c7a9d11"
down_revision = "c9f0c2b1d5a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_transaction",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("payment_id", sa.Text(), nullable=True),
        sa.Column("trx_id", sa.Text(), nullable=True),
        sa.Column("merchant_invoice_number", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("payment_transaction_user_id_idx", "payment_transaction", ["user_id"])
    op.create_index(
        "payment_transaction_payment_id_idx", "payment_transaction", ["payment_id"]
    )
    op.create_index(
        "payment_transaction_invoice_idx",
        "payment_transaction",
        ["merchant_invoice_number"],
    )


def downgrade():
    op.drop_index("payment_transaction_invoice_idx", table_name="payment_transaction")
    op.drop_index(
        "payment_transaction_payment_id_idx", table_name="payment_transaction"
    )
    op.drop_index("payment_transaction_user_id_idx", table_name="payment_transaction")
    op.drop_table("payment_transaction")
