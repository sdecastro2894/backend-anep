"""fix_asignaciones

Revision ID: a479e9ca4537
Revises: 3441631b932e
Create Date: 2026-05-03 00:52:10.409446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a479e9ca4537'
down_revision: Union[str, None] = '3441631b932e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass

def downgrade() -> None:
    pass