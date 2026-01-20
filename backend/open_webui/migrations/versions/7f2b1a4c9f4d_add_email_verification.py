"""Add email verification table

Revision ID: 7f2b1a4c9f4d
Revises: 018012973d35
Create Date: 2026-01-20 11:05:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "7f2b1a4c9f4d"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "email_verification" not in inspector.get_table_names():
        op.create_table(
            "email_verification",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("code_hash", sa.String(), nullable=False),
            sa.Column("attempts_remaining", sa.Integer(), nullable=False),
            sa.Column("expires_at", sa.Integer(), nullable=False),
            sa.Column("last_sent_at", sa.Integer(), nullable=False),
            sa.Column("intended_role", sa.String(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("verified_at", sa.Integer(), nullable=True),
            sa.Column(
                "disable_signup_after_verify",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        op.create_index(
            "email_verification_email_idx", "email_verification", ["email"]
        )
        op.create_index(
            "email_verification_user_id_idx", "email_verification", ["user_id"]
        )
        return

    columns = {col["name"] for col in inspector.get_columns("email_verification")}
    with op.batch_alter_table("email_verification") as batch_op:
        if "code_hash" not in columns:
            if "otp_hash" in columns:
                batch_op.alter_column(
                    "otp_hash", new_column_name="code_hash", existing_type=sa.String()
                )
            else:
                batch_op.add_column(
                    sa.Column(
                        "code_hash", sa.String(), nullable=False, server_default=""
                    )
                )

        if "attempts_remaining" not in columns:
            if "attempts" in columns:
                batch_op.alter_column(
                    "attempts",
                    new_column_name="attempts_remaining",
                    existing_type=sa.Integer(),
                )
            else:
                batch_op.add_column(
                    sa.Column(
                        "attempts_remaining",
                        sa.Integer(),
                        nullable=False,
                        server_default="5",
                    )
                )

        if "last_sent_at" not in columns:
            if "sent_at" in columns:
                batch_op.alter_column(
                    "sent_at",
                    new_column_name="last_sent_at",
                    existing_type=sa.Integer(),
                )
            else:
                batch_op.add_column(
                    sa.Column(
                        "last_sent_at",
                        sa.Integer(),
                        nullable=False,
                        server_default="0",
                    )
                )

        if "verified_at" not in columns:
            if "used_at" in columns:
                batch_op.alter_column(
                    "used_at", new_column_name="verified_at", existing_type=sa.Integer()
                )
            else:
                batch_op.add_column(
                    sa.Column("verified_at", sa.Integer(), nullable=True)
                )

        if "intended_role" not in columns:
            batch_op.add_column(
                sa.Column(
                    "intended_role",
                    sa.String(),
                    nullable=False,
                    server_default="user",
                )
            )

        if "disable_signup_after_verify" not in columns:
            batch_op.add_column(
                sa.Column(
                    "disable_signup_after_verify",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                )
            )

    index_names = {
        index["name"]
        for index in inspector.get_indexes("email_verification")
        if index.get("name")
    }
    if "email_verification_email_idx" not in index_names:
        op.create_index(
            "email_verification_email_idx", "email_verification", ["email"]
        )
    if "email_verification_user_id_idx" not in index_names:
        op.create_index(
            "email_verification_user_id_idx", "email_verification", ["user_id"]
        )


def downgrade():
    op.drop_index("email_verification_email_idx", table_name="email_verification")
    op.drop_index("email_verification_user_id_idx", table_name="email_verification")
    op.drop_table("email_verification")
