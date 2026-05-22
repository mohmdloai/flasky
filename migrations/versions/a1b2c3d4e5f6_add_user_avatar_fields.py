"""add user avatar fields

Revision ID: a1b2c3d4e5f6
Revises: 5e78f2913e3c
Create Date: 2026-05-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '5e78f2913e3c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avatar_bucket', sa.String(length=63), nullable=True))
        batch_op.add_column(sa.Column('avatar_object_key', sa.String(length=512), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('avatar_object_key')
        batch_op.drop_column('avatar_bucket')
