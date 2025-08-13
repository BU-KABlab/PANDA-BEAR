"""tips: drop volume/dead_volume, ensure radius_mm, rebuild hx triggers

Revision ID: 86100ae61dd8
Revises: 426be0a221b0
Create Date: 2025-08-13 15:02:46.652193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86100ae61dd8'
down_revision: Union[str, Sequence[str], None] = '426be0a221b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # panda_tips: drop columns, rename radius->radius_mm if present
    if "panda_tips" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("panda_tips")}
        with op.batch_alter_table("panda_tips") as batch:
            if "radius" in cols and "radius_mm" not in cols:
                batch.alter_column("radius", new_column_name="radius_mm")
            if "volume" in cols:
                batch.drop_column("volume")
            if "dead_volume" in cols:
                batch.drop_column("dead_volume")

        # ensure unique (rack_id, tip_id)
        uqs = [u["name"] for u in insp.get_unique_constraints("panda_tips")]
        if "uq_tip_slot" not in uqs:
            op.create_unique_constraint("uq_tip_slot", "panda_tips", ["rack_id", "tip_id"])

    # Rebuild tip history to match new schema
    op.execute("DROP TRIGGER IF EXISTS trg_tip_insert_hx;")
    op.execute("DROP TRIGGER IF EXISTS trg_tip_update_hx;")
    op.execute("DROP TABLE IF EXISTS panda_tip_hx;")
    op.execute("""
        CREATE TABLE panda_tip_hx AS
        SELECT *, datetime('now') AS hx_ts
        FROM panda_tips WHERE 0;
    """)
    op.execute("""
        CREATE TRIGGER trg_tip_insert_hx
        AFTER INSERT ON panda_tips
        BEGIN
            INSERT INTO panda_tip_hx SELECT NEW.*, datetime('now');
        END;
    """)
    op.execute("""
        CREATE TRIGGER trg_tip_update_hx
        AFTER UPDATE ON panda_tips
        BEGIN
            INSERT INTO panda_tip_hx SELECT NEW.*, datetime('now');
        END;
    """)

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "panda_tips" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("panda_tips")}
        with op.batch_alter_table("panda_tips") as batch:
            if "volume" not in cols:
                batch.add_column(sa.Column("volume", sa.Float))
            if "dead_volume" not in cols:
                batch.add_column(sa.Column("dead_volume", sa.Float))
            cols = {c["name"] for c in insp.get_columns("panda_tips")}
            if "radius_mm" in cols and "radius" not in cols:
                batch.alter_column("radius_mm", new_column_name="radius")

    op.execute("DROP TRIGGER IF EXISTS trg_tip_insert_hx;")
    op.execute("DROP TRIGGER IF EXISTS trg_tip_update_hx;")
    op.execute("DROP TABLE IF EXISTS panda_tip_hx;")
