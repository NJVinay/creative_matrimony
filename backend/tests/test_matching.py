"""Match scoring — horoscope contribution + confidence (Epic F2)."""

from datetime import date

import pytest

from app.models.profile import Profile, Gender
from app.models.match import Preference
from app.models.horoscope import Horoscope, Rasi, Star
from app.services.matching_service import MatchingService


def _preference(**overrides) -> Preference:
    pref = Preference(
        min_age=18, max_age=35,
        min_height=None, max_height=None,
        marital_status=None, religion_id=None, community_id=None,
        state=None, education_level=None, occupation_category=None,
    )
    for key, value in overrides.items():
        setattr(pref, key, value)
    return pref


def _candidate(**overrides) -> Profile:
    profile = Profile(
        display_name="Candidate",
        gender=Gender.female,
        date_of_birth=date(1998, 1, 1),
        state="Telangana",
    )
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


def test_score_without_horoscope_has_lower_confidence():
    candidate = _candidate()
    candidate.horoscope = None
    score, reasons, confidence = MatchingService.calculate_score(candidate, _preference())
    assert 0 < score <= 100
    assert confidence == round(4 * 100 / 6)  # only base criteria evaluable


def test_horoscope_contribution_raises_confidence_and_blends_score():
    seeker_h = Horoscope(rasi=Rasi.mesha, star=Star.ashwini, dosham=False)
    candidate = _candidate()
    # Same rasi (distance 1) and same star (dina count 1 % 9 == 1 → unfavourable),
    # matched dosham → 60/100 horoscope component
    candidate.horoscope = Horoscope(rasi=Rasi.mesha, star=Star.ashwini, dosham=False)

    base_score, _, base_conf = MatchingService.calculate_score(candidate, _preference())
    score, reasons, confidence = MatchingService.calculate_score(
        candidate, _preference(), seeker_horoscope=seeker_h
    )

    assert confidence > base_conf
    assert any("Horoscope compatibility" in r for r in reasons)
    # Blended: 80% base + 20% horoscope(60)
    assert score == round(base_score * 0.8 + 60 * 0.2)


def test_horoscope_compatibility_favourable_pair_scores_high():
    # Ashwini → Mrigashira: count 5, 5 % 9 = 5 (unfavourable dina)
    # Ashwini → Punarvasu: count 7 → unfavourable; pick one that lands on an even remainder:
    # Ashwini → Rohini: count 4 → favourable
    seeker = Horoscope(rasi=Rasi.mesha, star=Star.ashwini, dosham=False)
    candidate = Horoscope(rasi=Rasi.simha, star=Star.rohini, dosham=False)  # rasi distance 5 → unfavourable
    score, reasons = MatchingService.horoscope_compatibility(seeker, candidate)
    # star 40 + rasi 0 + dosham 20 = 60
    assert score == 60

    # No data on one side → not evaluated
    assert MatchingService.horoscope_compatibility(seeker, None) == (None, [])
