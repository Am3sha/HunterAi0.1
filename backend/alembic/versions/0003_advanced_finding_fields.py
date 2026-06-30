"""add cvss, cwe, owasp, remediation to findings (Sprint 2 M2)

Revision ID: 0003_advanced_finding_fields
Revises: 0002_findings
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_advanced_finding_fields"
down_revision: str | None = "0002_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("cvss_version", sa.String(length=16), nullable=True))
    op.add_column("findings", sa.Column("cvss_vector", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("cvss_base_score", sa.Float(), nullable=True))
    op.add_column("findings", sa.Column("cwe_ids", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("owasp_categories", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("remediation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "remediation")
    op.drop_column("findings", "owasp_categories")
    op.drop_column("findings", "cwe_ids")
    op.drop_column("findings", "cvss_base_score")
    op.drop_column("findings", "cvss_vector")
    op.drop_column("findings", "cvss_version")