"""
Taxonomy models — scalable hierarchy with canonical IDs, synonyms, and moderation queue.
Trace: @context_documents/DATA_TAXONOMY_SPEC.md, @context_documents/MVP_BACKLOG.md Epic C
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Text,
    ForeignKey, func
)
from app.database import Base


class RegionGroup(Base):
    __tablename__ = "region_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String(100), unique=True, nullable=False, doc="e.g. south_india")
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=True)
    is_enabled = Column(Boolean, default=False, doc="Feature flag — locked in MVP except South India")
    sort_order = Column(Integer, default=0)


class LanguageGroup(Base):
    __tablename__ = "language_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String(100), unique=True, nullable=False, doc="e.g. telugu")
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=True)
    is_enabled = Column(Boolean, default=True, doc="Telugu enabled in MVP")


class Religion(Base):
    __tablename__ = "religions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String(100), unique=True, nullable=False, doc="e.g. hindu")
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=True)


class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String(100), unique=True, nullable=False)
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=True)
    religion_id = Column(Integer, ForeignKey("religions.id"), nullable=False, index=True)
    language_group_id = Column(Integer, ForeignKey("language_groups.id"), nullable=False, index=True)


class SubCaste(Base):
    __tablename__ = "subcastes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_id = Column(String(100), unique=True, nullable=False)
    name_en = Column(String(200), nullable=False)
    name_te = Column(String(200), nullable=True)
    community_id = Column(Integer, ForeignKey("communities.id"), nullable=False, index=True)


class TaxonomySynonym(Base):
    """Maps spelling variants / transliterations to canonical taxonomy entries."""
    __tablename__ = "taxonomy_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(200), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, doc="religion | community | subcaste")
    target_id = Column(Integer, nullable=False)
    is_approved = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ModerationStatus(str, enum.Enum):
    pending = "pending"
    mapped = "mapped"
    rejected = "rejected"


class TaxonomyModerationQueue(Base):
    """User-submitted unknown taxonomy values awaiting admin mapping."""
    __tablename__ = "taxonomy_moderation_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_submitted_value = Column(String(200), nullable=False)
    field_name = Column(String(50), nullable=False, doc="community | subcaste | religion")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ModerationStatus), default=ModerationStatus.pending)
    mapped_to_id = Column(Integer, nullable=True, doc="ID of the canonical entry it was mapped to")
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
