"""add in_review status and migrate submitted pending cases

Revision ID: e91a3c2d4f80
Revises: d74166550db2
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'e91a3c2d4f80'
down_revision = 'd74166550db2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite stores Enum as VARCHAR so we can recreate the column using batch mode
    # to update the CHECK constraint to include the new 'in_review' value.
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('pending', 'approved', name='casestatus'),
            type_=sa.Enum('pending', 'in_review', 'approved', name='casestatus'),
            existing_nullable=False,
        )

    # Migrate existing submitted-but-pending rows to in_review
    op.execute("UPDATE cases SET status = 'in_review' WHERE submitted = 1 AND status = 'pending'")


def downgrade() -> None:
    # Revert in_review back to pending before removing the value
    op.execute("UPDATE cases SET status = 'pending' WHERE status = 'in_review'")

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('pending', 'in_review', 'approved', name='casestatus'),
            type_=sa.Enum('pending', 'approved', name='casestatus'),
            existing_nullable=False,
        )
