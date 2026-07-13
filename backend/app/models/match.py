"""
Match Models — Partner Preferences.
Trace: @context_documents/MVP_BACKLOG.md Epic F
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class Preference(Base):
    """
    User's partner preferences for matching.
    One-to-One with Profile.
    """
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), unique=True, nullable=False)
    
    # Age Range
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=35)
    
    # Height Range (cm)
    min_height = Column(Integer, nullable=True)
    max_height = Column(Integer, nullable=True)
    
    # Marital Status (JSON list of allowed statuses or null for any)
    marital_status = Column(JSON, nullable=True)
    
    # Religion & Community (JSON lists of IDs)
    religion_id = Column(JSON, nullable=True)
    community_id = Column(JSON, nullable=True)
    
    # Location
    country = Column(String, default="India")
    state = Column(String, nullable=True) # If null, any state
    
    # Education & Job
    education_level = Column(JSON, nullable=True)
    occupation_category = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    profile = relationship("Profile", back_populates="preference")
