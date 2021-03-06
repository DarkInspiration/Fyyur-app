"""empty message

Revision ID: 3bfccba5aa17
Revises: f07ff6815266
Create Date: 2020-04-01 17:57:59.174736

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3bfccba5aa17'
down_revision = 'f07ff6815266'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('Artist', sa.Column('seeking', sa.Boolean(), nullable=True))
    op.add_column('Artist', sa.Column('seeking_description', sa.String(), nullable=True))
    op.add_column('Artist', sa.Column('website_link', sa.String(length=120), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('Artist', 'website_link')
    op.drop_column('Artist', 'seeking_description')
    op.drop_column('Artist', 'seeking')
    # ### end Alembic commands ###
