"""fix nullable defaults

Revision ID: 3a2b9c4d5e6f
Revises: 2f1e8b853e7b
Create Date: 2026-02-10 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a2b9c4d5e6f'
down_revision = '2f1e8b853e7b'
branch_labels = None
depends_on = None


def upgrade():
    # Update existing NULL values to defaults before adding NOT NULL constraint
    # Users table
    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
    
    # Charities table
    op.execute("UPDATE charities SET is_active = TRUE WHERE is_active IS NULL")
    
    # Donations table
    op.execute("UPDATE donations SET is_anonymous = FALSE WHERE is_anonymous IS NULL")
    op.execute("UPDATE donations SET is_recurring = FALSE WHERE is_recurring IS NULL")
    
    # Charity applications table
    op.execute("UPDATE charity_applications SET status = 'draft' WHERE status IS NULL")
    op.execute("UPDATE charity_applications SET step = 1 WHERE step IS NULL")
    
    # Charity documents table
    op.execute("UPDATE charity_documents SET is_verified = FALSE WHERE is_verified IS NULL")
    
    # Now alter columns to NOT NULL with server defaults
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('is_active',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('TRUE'))
    
    with op.batch_alter_table('charities', schema=None) as batch_op:
        batch_op.alter_column('is_active',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('TRUE'))
    
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.alter_column('is_anonymous',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('FALSE'))
        batch_op.alter_column('is_recurring',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('FALSE'))
    
    with op.batch_alter_table('charity_applications', schema=None) as batch_op:
        batch_op.alter_column('status',
                              existing_type=sa.String(length=20),
                              nullable=False,
                              server_default='draft')
        batch_op.alter_column('step',
                              existing_type=sa.Integer(),
                              nullable=False,
                              server_default=sa.text('1'))
    
    with op.batch_alter_table('charity_documents', schema=None) as batch_op:
        batch_op.alter_column('is_verified',
                              existing_type=sa.Boolean(),
                              nullable=False,
                              server_default=sa.text('FALSE'))


def downgrade():
    # Revert to nullable (no data loss)
    with op.batch_alter_table('charity_documents', schema=None) as batch_op:
        batch_op.alter_column('is_verified',
                              existing_type=sa.Boolean(),
                              nullable=True,
                              server_default=None)
    
    with op.batch_alter_table('charity_applications', schema=None) as batch_op:
        batch_op.alter_column('step',
                              existing_type=sa.Integer(),
                              nullable=True,
                              server_default=None)
        batch_op.alter_column('status',
                              existing_type=sa.String(length=20),
                              nullable=True,
                              server_default=None)
    
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.alter_column('is_recurring',
                              existing_type=sa.Boolean(),
                              nullable=True,
                              server_default=None)
        batch_op.alter_column('is_anonymous',
                              existing_type=sa.Boolean(),
                              nullable=True,
                              server_default=None)
    
    with op.batch_alter_table('charities', schema=None) as batch_op:
        batch_op.alter_column('is_active',
                              existing_type=sa.Boolean(),
                              nullable=True,
                              server_default=None)
    
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('is_active',
                              existing_type=sa.Boolean(),
                              nullable=True,
                              server_default=None)
