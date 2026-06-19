from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apps",
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("license", sa.String(length=128), nullable=True),
        sa.Column("web_url", sa.String(length=1024), nullable=True),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("issue_url", sa.String(length=1024), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("icon_ref", sa.String(length=1024), nullable=True),
        sa.Column("added", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("suggested_version_code", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("package_name"),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hashed_secret", sa.String(length=512), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("allowed_package_globs", sa.JSON(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashed_secret"),
    )
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=512), nullable=True),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=True),
        sa.Column("version_code", sa.Integer(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_package_name"), "audit_logs", ["package_name"])
    op.create_table(
        "allowed_signing_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("sha256_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("added_by", sa.String(length=255), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["package_name"], ["apps.package_name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_name", "sha256_fingerprint"),
    )
    op.create_index(op.f("ix_allowed_signing_keys_sha256_fingerprint"), "allowed_signing_keys", ["sha256_fingerprint"])
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.ForeignKeyConstraint(["package_name"], ["apps.package_name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("version_name", sa.String(length=255), nullable=True),
        sa.Column("version_code", sa.Integer(), nullable=False),
        sa.Column("apk_name", sa.String(length=512), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("min_sdk", sa.Integer(), nullable=True),
        sa.Column("target_sdk", sa.Integer(), nullable=True),
        sa.Column("max_sdk", sa.Integer(), nullable=True),
        sa.Column("nativecode", sa.JSON(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("signer_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("release_channel", sa.String(length=64), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["package_name"], ["apps.package_name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_name", "version_code", "signer_fingerprint", name="uq_version_signer"),
    )


def downgrade() -> None:
    op.drop_table("versions")
    op.drop_table("assets")
    op.drop_index(op.f("ix_allowed_signing_keys_sha256_fingerprint"), table_name="allowed_signing_keys")
    op.drop_table("allowed_signing_keys")
    op.drop_index(op.f("ix_audit_logs_package_name"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("admin_users")
    op.drop_table("api_keys")
    op.drop_table("apps")
