"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(20), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('workspace_id', sa.String(20), primary_key=True),
        sa.Column('user_id', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_workspaces_user_id', 'workspaces', ['user_id'])
    
    # Create sandboxes table
    op.create_table(
        'sandboxes',
        sa.Column('sandbox_id', sa.String(20), primary_key=True),
        sa.Column('workspace_id', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), default='provisioning', nullable=False),
        sa.Column('agent_config_json', sa.Text(), nullable=True),
        sa.Column('connection_details_json', sa.Text(), nullable=True),
        sa.Column('container_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_sandboxes_workspace_id', 'sandboxes', ['workspace_id'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('message_id', sa.String(20), primary_key=True),
        sa.Column('from_sandbox_id', sa.String(20), nullable=False),
        sa.Column('to_sandbox_id', sa.String(20), nullable=True),
        sa.Column('workspace_id', sa.String(20), nullable=False),
        sa.Column('content_json', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(20), default='request', nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_messages_from_sandbox_id', 'messages', ['from_sandbox_id'])
    op.create_index('ix_messages_to_sandbox_id', 'messages', ['to_sandbox_id'])
    op.create_index('ix_messages_workspace_id', 'messages', ['workspace_id'])


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('sandboxes')
    op.drop_table('workspaces')
    op.drop_table('users')
