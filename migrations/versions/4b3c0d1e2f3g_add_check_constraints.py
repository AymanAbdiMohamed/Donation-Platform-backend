"""add check constraints

Revision ID: 4b3c0d1e2f3g
Revises: 3a2b9c4d5e6f
Create Date: 2026-02-10 14:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b3c0d1e2f3g'
down_revision = '3a2b9c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    # Add CHECK constraint for donation.amount > 0
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'donation_amount_positive',
            'amount > 0'
        )
    
    # Add CHECK constraint for user.role IN (donor, charity, admin)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'user_role_valid',
            "role IN ('donor', 'charity', 'admin')"
        )


def downgrade():
    # Remove CHECK constraints
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('user_role_valid', type_='check')
    
    with op.batch_alter_table('donations', schema=None) as batch_op:
        batch_op.drop_constraint('donation_amount_positive', type_='check')
