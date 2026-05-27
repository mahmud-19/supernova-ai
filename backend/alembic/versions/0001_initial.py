"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("sonologist", "expert_reviewer", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_code", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Enum("pending", "approved", name="casestatus"), nullable=False),
        sa.Column("original_image_path", sa.String(length=500), nullable=False),
        sa.Column("preprocessed_image_path", sa.String(length=500), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("bit_depth", sa.Integer(), nullable=False),
        sa.Column("contrast_adjusted", sa.Boolean(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cases_display_code", "cases", ["display_code"], unique=True)

    op.create_table(
        "inference_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("ai", "expert", name="resultsource"), nullable=False),
        sa.Column("mask_path", sa.String(length=500), nullable=False),
        sa.Column("contour_json", sa.JSON(), nullable=False),
        sa.Column("uncertainty_map_path", sa.String(length=500), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("total_lesions", sa.Integer(), nullable=False),
        sa.Column("total_pixels", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inference_results_case_id", "inference_results", ["case_id"])

    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("editor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mask_path", sa.String(length=500), nullable=False),
        sa.Column("contour_json", sa.JSON(), nullable=False),
        sa.Column("confidence_map_path", sa.String(length=500), nullable=True),
        sa.Column("is_finalized", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotations_case_id", "annotations", ["case_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_annotations_case_id", table_name="annotations")
    op.drop_table("annotations")
    op.drop_index("ix_inference_results_case_id", table_name="inference_results")
    op.drop_table("inference_results")
    op.drop_index("ix_cases_display_code", table_name="cases")
    op.drop_table("cases")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
