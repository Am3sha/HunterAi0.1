"""SQLAlchemy ORM models.

DB-agnostic column types (``Uuid``, ``JSON``) so the same models run on
PostgreSQL (production) and SQLite (tests). Results are stored in child tables
with cascade delete, keeping the schema queryable for the frontend.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TargetModel(Base):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    domain: Mapped[str] = mapped_column(String(253), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScanModel(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("targets.id"), index=True)
    target_domain: Mapped[str] = mapped_column(String(253))
    status: Mapped[str] = mapped_column(String(20), index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subdomains: Mapped[list["SubdomainModel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="SubdomainModel.id"
    )
    services: Mapped[list["HttpServiceModel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="HttpServiceModel.id"
    )
    endpoints: Mapped[list["EndpointModel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="EndpointModel.id"
    )
    findings: Mapped[list["FindingModel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="FindingModel.id"
    )


class SubdomainModel(Base):
    __tablename__ = "subdomains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id"), index=True)
    host: Mapped[str] = mapped_column(String(253))
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class HttpServiceModel(Base):
    __tablename__ = "http_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    input: Mapped[str | None] = mapped_column(String(253), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    webserver: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSON, default=list)


class EndpointModel(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id"), index=True)
    uid: Mapped[uuid.UUID] = mapped_column(Uuid)
    plugin: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    target: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(16))
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list[str]] = mapped_column(JSON, default=list)
    meta: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
