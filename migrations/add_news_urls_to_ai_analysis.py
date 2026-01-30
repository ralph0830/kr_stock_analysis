"""
Add news_urls field to AIAnalysis model

Revision ID: 001
Create Date: 2026-01-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    """Add news_urls column to ai_analyses table"""
    # JSONB 타입의 news_urls 컬럼 추가
    op.execute("""
        ALTER TABLE ai_analyses 
        ADD COLUMN IF NOT EXISTS news_urls JSONB DEFAULT '[]'::jsonb
    """)


def downgrade():
    """Remove news_urls column"""
    op.execute("""
        ALTER TABLE ai_analyses 
        DROP COLUMN IF EXISTS news_urls
    """)
