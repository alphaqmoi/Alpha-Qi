"""Add voice processing and enhanced model management tables

Revision ID: 002_add_voice_and_enhanced_models
Revises: 001_initial_migration
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_voice_and_enhanced_models'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None

def upgrade():
    # Create voice_models table for speech-to-text and text-to-speech models
    op.create_table('voice_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),  # stt or tts
        sa.Column('model_id', sa.String(length=255), nullable=False),
        sa.Column('processor_id', sa.String(length=255), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create voice_sessions table to track voice interactions
    op.create_table('voice_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('stt_model_id', sa.Integer(), nullable=True),
        sa.Column('tts_model_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['stt_model_id'], ['voice_models.id'], ),
        sa.ForeignKeyConstraint(['tts_model_id'], ['voice_models.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )

    # Create voice_audio table to store audio files
    op.create_table('voice_audio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),  # input or output
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('channels', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['voice_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add columns to models table for enhanced model management
    op.add_column('models', sa.Column('quantization_config', sa.JSON(), nullable=True))
    op.add_column('models', sa.Column('device_map', sa.String(length=50), nullable=True))
    op.add_column('models', sa.Column('max_memory', sa.JSON(), nullable=True))
    op.add_column('models', sa.Column('offload_folder', sa.String(length=255), nullable=True))
    op.add_column('models', sa.Column('is_cloud_enabled', sa.Boolean(), nullable=True))
    op.add_column('models', sa.Column('cloud_config', sa.JSON(), nullable=True))
    op.add_column('models', sa.Column('optimization_level', sa.String(length=20), nullable=True))
    op.add_column('models', sa.Column('cache_dir', sa.String(length=255), nullable=True))

    # Create model_metrics table for detailed performance tracking
    op.create_table('model_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create model_routing table for dynamic model selection
    op.create_table('model_routing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern', sa.String(length=255), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    # Drop new tables
    op.drop_table('model_routing')
    op.drop_table('model_metrics')
    op.drop_table('voice_audio')
    op.drop_table('voice_sessions')
    op.drop_table('voice_models')

    # Remove added columns from models table
    op.drop_column('models', 'cache_dir')
    op.drop_column('models', 'optimization_level')
    op.drop_column('models', 'cloud_config')
    op.drop_column('models', 'is_cloud_enabled')
    op.drop_column('models', 'offload_folder')
    op.drop_column('models', 'max_memory')
    op.drop_column('models', 'device_map')
    op.drop_column('models', 'quantization_config') 