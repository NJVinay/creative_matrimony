"""
Horoscope Model.
Trace: @context_documents/MVP_BACKLOG.md Epic F
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Rasi(str, enum.Enum):
    mesha = "Mesha (Aries)"
    vrishabha = "Vrishabha (Taurus)"
    mithuna = "Mithuna (Gemini)"
    karkataka = "Karkataka (Cancer)"
    simha = "Simha (Leo)"
    kanya = "Kanya (Virgo)"
    tula = "Tula (Libra)"
    vrischika = "Vrischika (Scorpio)"
    dhanu = "Dhanu (Sagittarius)"
    makara = "Makara (Capricorn)"
    kumbha = "Kumbha (Aquarius)"
    meena = "Meena (Pisces)"

class Star(str, enum.Enum):
    ashwini = "Ashwini"
    bharani = "Bharani"
    krittika = "Krittika"
    rohini = "Rohini"
    mrigashira = "Mrigashira"
    arudra = "Arudra"
    punarvasu = "Punarvasu"
    pushya = "Pushya"
    ashlesha = "Ashlesha"
    magha = "Magha"
    purva_phalguni = "Purva Phalguni"
    uttara_phalguni = "Uttara Phalguni"
    hasta = "Hasta"
    chitra = "Chitra"
    swati = "Swati"
    vishakha = "Vishakha"
    anuradha = "Anuradha"
    jyeshta = "Jyeshta"
    moola = "Moola"
    purva_ashadha = "Purva Ashadha"
    uttara_ashadha = "Uttara Ashadha"
    shravana = "Shravana"
    dhanishta = "Dhanishta"
    shatabhisha = "Shatabhisha"
    purva_bhadrapada = "Purva Bhadrapada"
    uttara_bhadrapada = "Uttara Bhadrapada"
    revati = "Revati"

class Horoscope(Base):
    __tablename__ = "horoscopes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), unique=True, nullable=False, index=True)

    # Basic Details (Enums)
    rasi = Column(Enum(Rasi), nullable=True)
    star = Column(Enum(Star), nullable=True)
    
    dosham = Column(Boolean, default=False)
    dosham_details = Column(Text, nullable=True)
    
    # Time of Birth
    time_of_birth = Column(String(50), nullable=True) # "10:30 AM"
    place_of_birth = Column(String(100), nullable=True)
    
    # Chart Images (JSON list of URLs)
    chart_images = Column(JSON, default=list)

    profile = relationship("Profile", back_populates="horoscope")
