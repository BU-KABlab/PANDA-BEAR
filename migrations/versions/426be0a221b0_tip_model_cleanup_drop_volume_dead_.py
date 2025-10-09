"""Tip model cleanup: drop volume/dead_volume, ensure radius_mm, tip tables

Revision ID: 426be0a221b0
Revises: 
Create Date: 2025-08-13 14:47:56.935634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '426be0a221b0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
