"""
Profile and ProfilePhoto models.
Trace: @context_documents/MVP_BACKLOG.md Epic B + D,
       @context_documents/IDEA_PLANNER.md §2.2 + §2.4
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Enum, Text,
    Float, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class ProfileMode(str, enum.Enum):
    self_managed = "self"
    parent_managed = "parent"


class Visibility(str, enum.Enum):
    public = "public"
    verified_only = "verified_only"
    hidden = "hidden"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class MaritalStatus(str, enum.Enum):
    never_married = "never_married"
    divorced = "divorced"
    widowed = "widowed"
    awaiting_divorce = "awaiting_divorce"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # ── Mode ─────────────────────────────────────────────
    profile_mode = Column(Enum(ProfileMode), nullable=False)
    preference = relationship("Preference", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    horoscope = relationship("Horoscope", back_populates="profile", uselist=False, cascade="all, delete-orphan")
    guardian_relationship = Column(String(50), nullable=True, doc="e.g. father, mother, uncle")

    # ── Basic info ───────────────────────────────────────
    display_name = Column(String(100), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    bio = Column(Text, nullable=True)

    # ── Location (public: city + state ONLY) ─────────────
    city_village = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    # Private/internal (never displayed publicly)
    district_mandal = Column(String(100), nullable=True)

    # ── Taxonomy refs ────────────────────────────────────
    religion_id = Column(Integer, ForeignKey("religions.id"), nullable=True)
    community_id = Column(Integer, ForeignKey("communities.id"), nullable=True)
    subcaste_id = Column(Integer, ForeignKey("subcastes.id"), nullable=True)

    # ── Optional fields ──────────────────────────────────
    education_level = Column(String(100), nullable=True)
    occupation_category = Column(String(100), nullable=True)
    marital_status = Column(Enum(MaritalStatus), nullable=True)

    # ── Language intent (non-Telugu seeking Telugu) ───────
    identity_language_group = Column(String(50), default="Telugu")
    preferred_partner_language_group = Column(String(50), nullable=True)
    open_to_non_telugu_partner = Column(Boolean, default=False)

    # ── Completion & status ──────────────────────────────
    completion_pct = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)

    # ── Privacy controls ─────────────────────────────────
    visibility = Column(Enum(Visibility), default=Visibility.public)
    photo_blur_until_mutual = Column(Boolean, default=False)
    hide_from_search = Column(Boolean, default=False)

    # ── Family details ───────────────────────────────────
    family_details = Column(Text, nullable=True)

    # ── Partner preferences (JSON-like text for MVP) ─────
    partner_preferences = Column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    is_approved = Column(Boolean, nullable=True, doc="null=pending, True=approved, False=rejected")
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
