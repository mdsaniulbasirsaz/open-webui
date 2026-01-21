"""Add email verification link token fields

Revision ID: c9f0c2b1d5a7
Revises: 7f2b1a4c9f4d
Create Date: 2026-01-20 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "c9f0c2b1d5a7"
down_revision = "7f2b1a4c9f4d"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "email_verification" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("email_verification")}
    with op.batch_alter_table("email_verification") as batch_op:
        if "verification_token_hash" not in columns:
            batch_op.add_column(
                sa.Column("verification_token_hash", sa.String(), nullable=True)
            )
        if "verification_token_expires_at" not in columns:
            batch_op.add_column(
                sa.Column("verification_token_expires_at", sa.Integer(), nullable=True)
            )
        if "verification_token_used_at" not in columns:
            batch_op.add_column(
                sa.Column("verification_token_used_at", sa.Integer(), nullable=True)
            )

    index_names = {
        index["name"]
        for index in inspector.get_indexes("email_verification")
        if index.get("name")
    }
    if "email_verification_token_hash_idx" not in index_names:
        op.create_index(
            "email_verification_token_hash_idx",
            "email_verification",
            ["verification_token_hash"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "email_verification" not in inspector.get_table_names():
        return

    index_names = {
        index["name"]
        for index in inspector.get_indexes("email_verification")
        if index.get("name")
    }
    if "email_verification_token_hash_idx" in index_names:
        op.drop_index(
            "email_verification_token_hash_idx", table_name="email_verification"
        )

    columns = {col["name"] for col in inspector.get_columns("email_verification")}
    with op.batch_alter_table("email_verification") as batch_op:
        if "verification_token_hash" in columns:
            batch_op.drop_column("verification_token_hash")
        if "verification_token_expires_at" in columns:
            batch_op.drop_column("verification_token_expires_at")
        if "verification_token_used_at" in columns:
            batch_op.drop_column("verification_token_used_at")
