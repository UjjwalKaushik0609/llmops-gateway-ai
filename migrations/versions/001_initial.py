"""Initial migration: create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('daily_token_limit', sa.Integer(), nullable=False, server_default='1000000'),
        sa.Column('monthly_budget_usd', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('key_name', sa.String(255), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('monthly_quota_usd', sa.Float(), server_default='500.0'),
        sa.Column('current_month_spend', sa.Float(), server_default='0.0'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('last_rotated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])

    # ── requests ─────────────────────────────────────────────────────────────
    op.create_table(
        'requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('tokens_input', sa.Integer(), server_default='0'),
        sa.Column('tokens_output', sa.Integer(), server_default='0'),
        sa.Column('cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('latency_ms', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(50), server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('prompt_injection_detected', sa.Boolean(), server_default='false'),
        sa.Column('pii_detected', sa.Boolean(), server_default='false'),
        sa.Column('routed_by', sa.String(50), server_default='manual'),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_requests_session_id', 'requests', ['session_id'])
    op.create_index('ix_requests_timestamp', 'requests', ['timestamp'])
    op.create_index('ix_requests_user_id', 'requests', ['user_id'])

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('request_id', sa.String(36), sa.ForeignKey('requests.id'), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_conversations_session_id', 'conversations', ['session_id'])

    # ── system_metrics ────────────────────────────────────────────────────────
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('metric_name', sa.String(255), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_system_metrics_name', 'system_metrics', ['metric_name'])
    op.create_index('ix_system_metrics_recorded_at', 'system_metrics', ['recorded_at'])

    # ── alert_rules ───────────────────────────────────────────────────────────
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('metric', sa.String(100), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('operator', sa.String(10), nullable=False),
        sa.Column('notification_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('alert_rules')
    op.drop_table('system_metrics')
    op.drop_table('conversations')
    op.drop_table('requests')
    op.drop_table('api_keys')
    op.drop_table('users')
