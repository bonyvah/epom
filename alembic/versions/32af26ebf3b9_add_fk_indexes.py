"""add_fk_indexes

Revision ID: 32af26ebf3b9
Revises: d43955cfc032
Create Date: 2026-08-15 08:48:11.526500

"""
from collections.abc import Sequence

from alembic import op

revision: str = '32af26ebf3b9'
down_revision: str | Sequence[str] | None = 'd43955cfc032'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('ix_documents_project_id', 'documents', ['project_id'])
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_active_username;")
    
    op.drop_index('ix_project_members_user_id', table_name='project_members')
    op.drop_index('ix_documents_uploaded_by', table_name='documents')
    op.drop_index('ix_documents_project_id', table_name='documents')