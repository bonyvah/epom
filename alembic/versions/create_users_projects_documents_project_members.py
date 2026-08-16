"""initial

Revision ID: d43955cfc032
Revises: 
Create Date: 2026-07-31 17:58:39.672938

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd43955cfc032'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column("project_size_limit_gb", sa.Integer(), nullable=False, server_default='1'),
    sa.Column("document_size_limit_mb", sa.Integer(), nullable=False, server_default='50'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('s3_key', sa.Text(), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('content_type', sa.Text(), nullable=False),
    sa.Column('uploaded_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('project_members',
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.Enum('owner', 'participant', name='role'), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('project_id', 'user_id')
    )

    # --- Trigger Function Creation ---
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # --- Attach Triggers to Tables ---
    op.execute("""
        CREATE TRIGGER update_projects_updated_at
            BEFORE UPDATE ON projects
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
            CREATE TRIGGER update_documents_updated_at
                BEFORE UPDATE ON documents
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)

    op.execute("""
            CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('project_members')
    op.drop_table('documents')
    op.drop_table('projects')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS role")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
