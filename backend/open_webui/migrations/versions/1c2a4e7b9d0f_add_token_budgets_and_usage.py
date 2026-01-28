"""Add token budgets and usage tables

Revision ID: 1c2a4e7b9d0f
Revises: 8f0b9d7c2a1a
Create Date: 2026-01-27 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "1c2a4e7b9d0f"
down_revision = "8f0b9d7c2a1a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_budget",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("window_type", sa.String(length=32), nullable=False, server_default="monthly"),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("limit_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", name="token_budget_user_id_uq"),
    )
    op.create_index("token_budget_user_id_idx", "token_budget", ["user_id"])

    op.create_table(
        "token_usage_event",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("route", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="success"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.UniqueConstraint("request_id", name="token_usage_event_request_id_uq"),
    )
    op.create_index("token_usage_event_request_id_idx", "token_usage_event", ["request_id"])
    op.create_index("token_usage_event_user_id_idx", "token_usage_event", ["user_id"])
    op.create_index("token_usage_event_created_at_idx", "token_usage_event", ["created_at"])

    op.create_table(
        "token_window_aggregate",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("limit_tokens_snapshot", sa.Integer(), nullable=False),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "window_start", name="token_window_user_start_uq"),
    )
    op.create_index("token_window_aggregate_user_id_idx", "token_window_aggregate", ["user_id"])
    op.create_index(
        "token_window_aggregate_user_window_idx",
        "token_window_aggregate",
        ["user_id", "window_start"],
    )


def downgrade():
    op.drop_index("token_window_aggregate_user_window_idx", table_name="token_window_aggregate")
    op.drop_index("token_window_aggregate_user_id_idx", table_name="token_window_aggregate")
    op.drop_table("token_window_aggregate")

    op.drop_index("token_usage_event_created_at_idx", table_name="token_usage_event")
    op.drop_index("token_usage_event_user_id_idx", table_name="token_usage_event")
    op.drop_index("token_usage_event_request_id_idx", table_name="token_usage_event")
    op.drop_table("token_usage_event")

    op.drop_index("token_budget_user_id_idx", table_name="token_budget")
    op.drop_table("token_budget")
