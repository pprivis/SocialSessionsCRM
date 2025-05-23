"""Final full schema

Revision ID: aa1c86db7067
Revises: 
Create Date: 2025-04-16 17:23:51.281254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa1c86db7067'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('contact',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('tags', sa.String(length=250), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('rep', sa.String(length=100), nullable=True),
    sa.Column('archived', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rep_note',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rep_name', sa.String(length=100), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rep_name')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=True),
    sa.Column('password', sa.String(length=120), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('follow_up_task',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('contact_id', sa.Integer(), nullable=True),
    sa.Column('task', sa.String(length=250), nullable=True),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('completed', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('interaction_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('contact_id', sa.Integer(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('order_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('contact_id', sa.Integer(), nullable=True),
    sa.Column('order_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pop_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('contact_id', sa.Integer(), nullable=True),
    sa.Column('material', sa.String(length=100), nullable=True),
    sa.Column('sent_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['contact_id'], ['contact.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('pop_log')
    op.drop_table('order_log')
    op.drop_table('interaction_log')
    op.drop_table('follow_up_task')
    op.drop_table('user')
    op.drop_table('rep_note')
    op.drop_table('contact')
    # ### end Alembic commands ###
