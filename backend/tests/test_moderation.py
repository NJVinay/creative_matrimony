"""Contact-sharing + abusive-language filters (chat and profile text)."""

import pytest

from tests.conftest import make_client, create_profile
from app.config import settings
from app.services.moderation import contains_abuse, contains_contact_info


@pytest.mark.parametrize("text", [
    "call me 9876543210",
    "98765 43210",
    "+91-98765-43210",
    "(+91) 98765.43210",
    "9 8 7 6 5 4 3 2 1 0",
    "nine eight seven six five four three two one zero",
    "Nine Eight 7 6 5 four 3 2 1 0",
    "double nine 876 triple five 4321",
    "tommidi enimidi edu aaru aidu nalugu moodu rendu okati sunna",
    "number: ౯౮౭౬౫౪౩౨౧౦",  # Telugu digits
    "९८७६५४३२१०",  # Devanagari digits
    "ravi.k@gmail.com",
    "ravi.k at gmail dot com",
    "ravi (at) yahoo [dot] co [dot] in",
    "mail me: ravi at gmail",
    "ravi @ outlook . com",
    "my insta is @ravi_k",
    "@ravi.kumar99",
    "insta: ravi_k",
    "fb id ravi.kumar",
    "telegram username is ravi_k",
])
def test_contact_info_is_detected(text):
    assert contains_contact_info(text), text


@pytest.mark.parametrize("text", [
    "Namaste! Nice to match with you.",
    "Smoke test bio",
    "I earn 12,00,000 per annum",
    "Expecting 10,00,000 - 15,00,000 salary",
    "Born in 1995, height 5.8 ft, 2 brothers and 1 sister",
    "Let's meet at 5.30 pm at the temple",
    "See you at home, I work at TCS since 2019",
    "We are a BC family from Guntur",
    "One or two kids, settled in Hyderabad",
    "Whatsapp is how my family stays in touch",
])
def test_normal_text_is_not_flagged_as_contact(text):
    assert not contains_contact_info(text), text


@pytest.mark.parametrize("text", [
    "you are a bitch",
    "Fucking idiot",
    "SEND NUDES",
    "nuvvu lanja",
    "madarchod",
    "I will kill you",
])
def test_abusive_language_is_detected(text):
    assert contains_abuse(text), text


@pytest.mark.parametrize("text", [
    "I support anti-harassment campaigns",   # old substring list blocked this
    "No abuse of any kind, please",
    "maa intiki randi",                       # Telugu: "please come to our home"
    "I had dengue fever last year",
    "Grew up in Scunthorpe",
    "Classic novels, assassin's creed and cricket",
])
def test_innocent_text_is_not_flagged_as_abuse(text):
    assert not contains_abuse(text), text


def test_blocklist_is_configurable(monkeypatch):
    assert not contains_abuse("such an idiotic reply")
    monkeypatch.setattr(settings, "MODERATION_BLOCKED_TERMS", "idiot*, stupid fellow")
    assert contains_abuse("such an idiotic reply")
    assert contains_abuse("what a stupid   fellow")
    assert not contains_abuse("stupid mistake")


async def _chat_room(a, b, a_profile_id: int) -> int:
    resp = await b.post(f"/api/interests/{a_profile_id}")
    assert resp.status_code == 200, resp.text
    interest_id = (await a.get("/api/interests/received")).json()[0]["id"]
    resp = await a.put(f"/api/interests/{interest_id}/accept")
    assert resp.status_code == 200, resp.text
    return (await a.get("/api/chat/rooms")).json()[0]["id"]


@pytest.mark.asyncio
async def test_chat_blocks_contact_bypasses_and_allows_normal_messages():
    sita = await make_client("+919500000001")
    ram = await make_client("+919500000002")
    try:
        p_sita = await create_profile(sita, display_name="Sita Mod", gender="female")
        await create_profile(ram, display_name="Ram Mod", gender="male")
        room_id = await _chat_room(sita, ram, p_sita["id"])

        for blocked in ("98765 43210", "+91-98765-43210", "nine eight seven six five four three two one zero",
                        "ram at gmail dot com", "add me @ram_k"):
            resp = await ram.post(f"/api/chat/rooms/{room_id}/messages", json={"content": blocked})
            assert resp.status_code == 403, blocked
            assert "contact information" in resp.json()["detail"]

        resp = await ram.post(f"/api/chat/rooms/{room_id}/messages", json={"content": "you bitch"})
        assert resp.status_code == 403
        assert "community guidelines" in resp.json()["detail"]

        resp = await ram.post(f"/api/chat/rooms/{room_id}/messages",
                              json={"content": "I volunteer for an anti-harassment NGO"})
        assert resp.status_code == 200, resp.text
    finally:
        await sita.aclose()
        await ram.aclose()


@pytest.mark.asyncio
async def test_profile_text_rejects_contact_info_on_create_and_update():
    client = await make_client("+919500000010")
    try:
        resp = await client.post("/api/profiles", json={
            "profile_mode": "self", "display_name": "Lakshmi", "gender": "female",
            "date_of_birth": "1997-04-02", "city_village": "Vijayawada", "state": "Andhra Pradesh",
            "bio": "Call my father on 98765 43210",
        })
        assert resp.status_code == 422, resp.text
        error = resp.json()["detail"][0]
        assert error["loc"][-1] == "bio"
        assert "phone numbers" in error["msg"]

        await create_profile(client, display_name="Lakshmi", gender="female",
                             bio="Software engineer who loves Carnatic music")

        for field, value in (("family_details", "Father: +91-98765-43210"),
                             ("partner_preferences", "DM me on insta: lakshmi_k"),
                             ("bio", "lakshmi at gmail dot com"),
                             ("display_name", "Lakshmi 9876543210")):
            resp = await client.patch("/api/profiles/me", json={field: value})
            assert resp.status_code == 422, f"{field}: {resp.text}"
            assert resp.json()["detail"][0]["loc"][-1] == field

        resp = await client.patch("/api/profiles/me", json={
            "family_details": "Father retired from APSRTC, 1 elder brother",
            "partner_preferences": "Well-settled, salary 10,00,000 - 15,00,000",
        })
        assert resp.status_code == 200, resp.text
    finally:
        await client.aclose()
