"""Add AI models

Revision ID: add_ai_models
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_ai_models'
down_revision = 'previous_revision'  # Update this to your previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_models table
    op.create_table(
        'ai_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='inactive'),
        sa.Column('model_id', sa.String(length=200), nullable=False),
        sa.Column('tokenizer_id', sa.String(length=200)),
        sa.Column('cache_dir', sa.String(length=200)),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_used', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create ai_sessions table
    op.create_table(
        'ai_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer()),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime()),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create ai_interactions table
    op.create_table(
        'ai_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['session_id'], ['ai_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create ai_model_metrics table
    op.create_table(
        'ai_model_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_ai_models_name', 'ai_models', ['name'])
    op.create_index('ix_ai_models_status', 'ai_models', ['status'])
    op.create_index('ix_ai_sessions_session_id', 'ai_sessions', ['session_id'])
    op.create_index('ix_ai_sessions_user_id', 'ai_sessions', ['user_id'])
    op.create_index('ix_ai_sessions_status', 'ai_sessions', ['status'])
    op.create_index('ix_ai_interactions_session_id', 'ai_interactions', ['session_id'])
    op.create_index('ix_ai_interactions_type', 'ai_interactions', ['type'])
    op.create_index('ix_ai_model_metrics_model_id', 'ai_model_metrics', ['model_id'])
    op.create_index('ix_ai_model_metrics_metric_type', 'ai_model_metrics', ['metric_type'])
    op.create_index('ix_ai_model_metrics_created_at', 'ai_model_metrics', ['created_at'])

def downgrade():
    # Drop indexes
    op.drop_index('ix_ai_model_metrics_created_at')
    op.drop_index('ix_ai_model_metrics_metric_type')
    op.drop_index('ix_ai_model_metrics_model_id')
    op.drop_index('ix_ai_interactions_type')
    op.drop_index('ix_ai_interactions_session_id')
    op.drop_index('ix_ai_sessions_status')
    op.drop_index('ix_ai_sessions_user_id')
    op.drop_index('ix_ai_sessions_session_id')
    op.drop_index('ix_ai_models_status')
    op.drop_index('ix_ai_models_name')
    
    # Drop tables
    op.drop_table('ai_model_metrics')
    op.drop_table('ai_interactions')
    op.drop_table('ai_sessions')
    op.drop_table('ai_models') 