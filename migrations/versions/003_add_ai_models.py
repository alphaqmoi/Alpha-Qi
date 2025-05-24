"""Add AI model tables

Revision ID: 003_add_ai_models
Revises: 002_add_voice_and_enhanced_models
Create Date: 2024-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_ai_models'
down_revision = '002_add_voice_and_enhanced_models'
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_models table for code and chat models
    op.create_table('ai_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),  # code, chat, embedding
        sa.Column('model_id', sa.String(length=255), nullable=False),
        sa.Column('tokenizer_id', sa.String(length=255), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('quantization_config', sa.JSON(), nullable=True),
        sa.Column('device_map', sa.String(length=50), nullable=True),
        sa.Column('max_memory', sa.JSON(), nullable=True),
        sa.Column('offload_folder', sa.String(length=255), nullable=True),
        sa.Column('is_cloud_enabled', sa.Boolean(), nullable=True),
        sa.Column('cloud_config', sa.JSON(), nullable=True),
        sa.Column('optimization_level', sa.String(length=20), nullable=True),
        sa.Column('cache_dir', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create ai_sessions table to track model interactions
    op.create_table('ai_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )

    # Create ai_interactions table for model inputs/outputs
    op.create_table('ai_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),  # input, output
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['ai_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create model_metrics table for detailed performance tracking
    op.create_table('ai_model_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create model_routing table for dynamic model selection
    op.create_table('ai_model_routing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern', sa.String(length=255), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Drop new tables
    op.drop_table('ai_model_routing')
    op.drop_table('ai_model_metrics')
    op.drop_table('ai_interactions')
    op.drop_table('ai_sessions')
    op.drop_table('ai_models') 