"""create user and agent tables

Revision ID: create_user_agent_tables
Revises: ad58d88f08ed
Create Date: 2025-12-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'create_user_agent_tables'
down_revision: Union[str, None] = 'ad58d88f08ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def type_exists(connection, type_name: str) -> bool:
    """Check if a PostgreSQL type exists"""
    result = connection.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :type_name)"
    ), {"type_name": type_name})
    return result.scalar()


def table_exists(connection, table_name: str) -> bool:
    """Check if a table exists"""
    result = connection.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
    ), {"table_name": table_name})
    return result.scalar()


def column_exists(connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    result = connection.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name)"
    ), {"table_name": table_name, "column_name": column_name})
    return result.scalar()


def upgrade() -> None:
    connection = op.get_bind()
    
    # Create enum types if they don't exist
    if not type_exists(connection, 'kycstatus'):
        kycstatus = ENUM('not_started', 'pending', 'verified', 'rejected', name='kycstatus', create_type=False)
        kycstatus.create(connection, checkfirst=True)
    
    if not type_exists(connection, 'userrole'):
        userrole = ENUM('customer', 'employee', 'admin', name='userrole', create_type=False)
        userrole.create(connection, checkfirst=True)
    
    # Create users table if it doesn't exist
    if not table_exists(connection, 'users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('phone', sa.String(15), nullable=False),
            sa.Column('hashed_password', sa.String(255), nullable=False),
            sa.Column('full_name', sa.String(100), nullable=False),
            sa.Column('aadhaar', sa.String(12), nullable=True),
            sa.Column('pan', sa.String(10), nullable=True),
            sa.Column('monthly_income', sa.Integer(), nullable=True),
            sa.Column('kyc_status', sa.Enum('not_started', 'pending', 'verified', 'rejected', name='kycstatus', create_type=False), nullable=True),
            sa.Column('kyc_verified_at', sa.DateTime(), nullable=True),
            sa.Column('verification_result', sa.String(500), nullable=True),
            sa.Column('role', sa.Enum('customer', 'employee', 'admin', name='userrole', create_type=False), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('last_login', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
    
    # Add columns to applications table (check each column)
    if not column_exists(connection, 'applications', 'user_id'):
        op.add_column('applications', sa.Column('user_id', sa.Integer(), nullable=True))
    if not column_exists(connection, 'applications', 'kyc_details'):
        op.add_column('applications', sa.Column('kyc_details', sa.JSON(), nullable=True))
    if not column_exists(connection, 'applications', 'current_agent'):
        op.add_column('applications', sa.Column('current_agent', sa.String(50), nullable=True))
    if not column_exists(connection, 'applications', 'final_decision'):
        op.add_column('applications', sa.Column('final_decision', sa.String(20), nullable=True))
    if not column_exists(connection, 'applications', 'decision_reason'):
        op.add_column('applications', sa.Column('decision_reason', sa.String(500), nullable=True))
    if not column_exists(connection, 'applications', 'assigned_employee_id'):
        op.add_column('applications', sa.Column('assigned_employee_id', sa.Integer(), nullable=True))
    if not column_exists(connection, 'applications', 'human_override'):
        op.add_column('applications', sa.Column('human_override', sa.Boolean(), nullable=True))
    if not column_exists(connection, 'applications', 'override_reason'):
        op.add_column('applications', sa.Column('override_reason', sa.String(500), nullable=True))
    if not column_exists(connection, 'applications', 'processed_at'):
        op.add_column('applications', sa.Column('processed_at', sa.DateTime(), nullable=True))
    
    # Create foreign keys (ignore if already exist)
    try:
        op.create_foreign_key('fk_applications_user_id', 'applications', 'users', ['user_id'], ['id'])
    except Exception:
        pass
    try:
        op.create_foreign_key('fk_applications_assigned_employee_id', 'applications', 'users', ['assigned_employee_id'], ['id'])
    except Exception:
        pass
    
    # Create agent_evaluations table if it doesn't exist
    if not table_exists(connection, 'agent_evaluations'):
        op.create_table(
            'agent_evaluations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('application_id', sa.Integer(), nullable=False),
            sa.Column('agent_name', sa.String(50), nullable=False),
            sa.Column('agent_type', sa.String(50), nullable=False),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('decision', sa.String(20), nullable=False),
            sa.Column('confidence', sa.Integer(), nullable=True),
            sa.Column('explanation_summary', sa.String(500), nullable=False),
            sa.Column('detailed_analysis', sa.JSON(), nullable=True),
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),
            sa.Column('processed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_agent_evaluations_id'), 'agent_evaluations', ['id'], unique=False)
    
    # Create status_history table if it doesn't exist
    if not table_exists(connection, 'status_history'):
        op.create_table(
            'status_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('application_id', sa.Integer(), nullable=False),
            sa.Column('old_status', sa.String(20), nullable=False),
            sa.Column('new_status', sa.String(20), nullable=False),
            sa.Column('changed_by_id', sa.Integer(), nullable=True),
            sa.Column('reason', sa.String(500), nullable=True),
            sa.Column('changed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
            sa.ForeignKeyConstraint(['changed_by_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_status_history_id'), 'status_history', ['id'], unique=False)
    
    # Add user_id to conversation_sessions if it doesn't exist
    if not column_exists(connection, 'conversation_sessions', 'user_id'):
        op.add_column('conversation_sessions', sa.Column('user_id', sa.Integer(), nullable=True))
        try:
            op.create_foreign_key('fk_conversation_sessions_user_id', 'conversation_sessions', 'users', ['user_id'], ['id'])
        except Exception:
            pass


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint('fk_conversation_sessions_user_id', 'conversation_sessions', type_='foreignkey')
    op.drop_column('conversation_sessions', 'user_id')
    
    # Drop status_history
    op.drop_index(op.f('ix_status_history_id'), table_name='status_history')
    op.drop_table('status_history')
    
    # Drop agent_evaluations
    op.drop_index(op.f('ix_agent_evaluations_id'), table_name='agent_evaluations')
    op.drop_table('agent_evaluations')
    
    # Drop application columns
    op.drop_constraint('fk_applications_assigned_employee_id', 'applications', type_='foreignkey')
    op.drop_constraint('fk_applications_user_id', 'applications', type_='foreignkey')
    op.drop_column('applications', 'processed_at')
    op.drop_column('applications', 'override_reason')
    op.drop_column('applications', 'human_override')
    op.drop_column('applications', 'assigned_employee_id')
    op.drop_column('applications', 'decision_reason')
    op.drop_column('applications', 'final_decision')
    op.drop_column('applications', 'current_agent')
    op.drop_column('applications', 'kyc_details')
    op.drop_column('applications', 'user_id')
    
    # Drop users
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    sa.Enum(name='userrole').drop(op.get_bind())
    sa.Enum(name='kycstatus').drop(op.get_bind())

