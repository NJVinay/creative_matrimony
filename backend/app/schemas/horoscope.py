from typing import List, Optional
from pydantic import BaseModel
from app.models.horoscope import Rasi, Star

class HoroscopeBase(BaseModel):
    rasi: Optional[Rasi] = None
    star: Optional[Star] = None
    dosham: Optional[bool] = False
    dosham_details: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    # chart_images handled separately or just as list of strings

class HoroscopeUpdate(HoroscopeBase):
    pass

class HoroscopeOut(HoroscopeBase):
    id: int
    profile_id: int
    chart_images: List[str] = []

    class Config:
        from_attributes = True

class HoroscopeCreate(HoroscopeBase):
    pass
