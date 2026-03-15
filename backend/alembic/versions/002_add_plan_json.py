"""Add plan_json column

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add plan_json column to store LLM-generated animation plans
    op.add_column("jobs", sa.Column("plan_json", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    # Remove plan_json column
    op.drop_column("jobs", "plan_json")
