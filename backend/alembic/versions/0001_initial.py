"""Initial schema — todas las tablas de vigi.ai

Revision ID: 0001
Revises:
Create Date: 2026-06-03

Crea la extensión vector y las 9 tablas del MVP spec con sus columnas,
FKs, unique constraints, check constraints e índices.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Extensión pgvector ───────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ─── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clerk_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "plan",
            sa.String(),
            server_default="free",
            nullable=False,
        ),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notif_email_instant",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "notif_email_digest",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "notif_whatsapp",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("whatsapp_number", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "plan IN ('free', 'starter', 'growth', 'business')", name="ck_users_plan"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)

    # ─── companies ────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("country", sa.String(), server_default="AR", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "industry IN ('food', 'tech', 'construction', 'other')",
            name="ck_companies_industry",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_companies_user_id"),
    )

    # ─── competitors ──────────────────────────────────────────────────────────
    op.create_table(
        "competitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("website_url", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitors_company_id", "competitors", ["company_id"])

    # ─── competitor_sources ───────────────────────────────────────────────────
    op.create_table(
        "competitor_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('website', 'mercadolibre', 'jobs', 'pdf')",
            name="ck_competitor_sources_source_type",
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitor_sources_competitor_id", "competitor_sources", ["competitor_id"])

    # ─── snapshots ────────────────────────────────────────────────────────────
    op.create_table(
        "snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_url", sa.String(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('website', 'mercadolibre', 'jobs', 'pdf')",
            name="ck_snapshots_source_type",
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["competitor_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_snapshots_competitor_source",
        "snapshots",
        ["competitor_id", "source_id"],
    )
    op.create_index("ix_snapshots_captured_at", "snapshots", ["captured_at"])

    # ─── changes ──────────────────────────────────────────────────────────────
    op.create_table(
        "changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("section", sa.String(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("diff_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("snapshot_before_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_after_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(),
            server_default="pending",
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('website', 'mercadolibre', 'jobs', 'pdf')",
            name="ck_changes_source_type",
        ),
        sa.CheckConstraint(
            "section IN ('pricing', 'home', 'features', 'jobs', 'pdf', 'general')",
            name="ck_changes_section",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'analyzing', 'done', 'failed', 'ignored')",
            name="ck_changes_status",
        ),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["competitor_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_before_id"], ["snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_after_id"], ["snapshots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_changes_competitor_id", "changes", ["competitor_id"])
    op.create_index("ix_changes_status", "changes", ["status"])
    op.create_index("ix_changes_detected_at", "changes", ["detected_at"])

    # ─── insights ─────────────────────────────────────────────────────────────
    # La columna embedding usa el tipo vector(1536) de pgvector.
    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("what_changed", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("what_to_do", sa.Text(), nullable=False),
        sa.Column("urgency", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("langfuse_trace_id", sa.String(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            sa.Text(),  # placeholder; op.execute abajo lo convierte a vector(1536)
            nullable=True,
        ),
        sa.CheckConstraint("urgency IN ('alta', 'media', 'baja')", name="ck_insights_urgency"),
        sa.ForeignKeyConstraint(["change_id"], ["changes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("change_id", name="uq_insights_change_id"),
    )
    # Convertir la columna embedding a tipo vector(1536) nativo de pgvector
    op.execute("ALTER TABLE insights ALTER COLUMN embedding TYPE vector(1536) USING NULL")
    op.create_index("ix_insights_change_id", "insights", ["change_id"])
    op.create_index("ix_insights_urgency", "insights", ["urgency"])
    op.create_index("ix_insights_generated_at", "insights", ["generated_at"])

    # ─── notifications ────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("insight_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "channel IN ('email_instant', 'email_digest', 'whatsapp')",
            name="ck_notifications_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_notifications_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_insight_id", "notifications", ["insight_id"])

    # ─── digests ──────────────────────────────────────────────────────────────
    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "insight_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=False)),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_digests_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_digests_user_id", "digests", ["user_id"])


def downgrade() -> None:
    # Eliminar en orden inverso respetando FK constraints
    op.drop_table("digests")
    op.drop_table("notifications")
    op.drop_table("insights")
    op.drop_table("changes")
    op.drop_table("snapshots")
    op.drop_table("competitor_sources")
    op.drop_table("competitors")
    op.drop_table("companies")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
