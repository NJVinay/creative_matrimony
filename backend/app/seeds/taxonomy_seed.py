"""
Seed script — populates taxonomy tables with Telugu MVP data.
Run: python -m app.seeds.taxonomy_seed
"""

import asyncio
from app.database import async_session, init_db


REGIONS = [
    {"canonical_id": "south_india", "name_en": "South India", "name_te": "దక్షిణ భారతదేశం", "is_enabled": True, "sort_order": 1},
    {"canonical_id": "north_india", "name_en": "North India", "name_te": "ఉత్తర భారతదేశం", "is_enabled": False, "sort_order": 2},
    {"canonical_id": "east_india", "name_en": "East India", "name_te": "తూర్పు భారతదేశం", "is_enabled": False, "sort_order": 3},
    {"canonical_id": "west_india", "name_en": "West India", "name_te": "పశ్చిమ భారతదేశం", "is_enabled": False, "sort_order": 4},
]

LANGUAGE_GROUPS = [
    {"canonical_id": "telugu", "name_en": "Telugu", "name_te": "తెలుగు", "is_enabled": True},
    {"canonical_id": "hindi", "name_en": "Hindi", "name_te": "హిందీ", "is_enabled": False},
    {"canonical_id": "tamil", "name_en": "Tamil", "name_te": "తమిళం", "is_enabled": False},
    {"canonical_id": "kannada", "name_en": "Kannada", "name_te": "కన్నడ", "is_enabled": False},
]

RELIGIONS = [
    {"canonical_id": "hindu", "name_en": "Hindu", "name_te": "హిందూ"},
    {"canonical_id": "muslim", "name_en": "Muslim", "name_te": "ముస్లిం"},
    {"canonical_id": "christian", "name_en": "Christian", "name_te": "క్రైస్తవ"},
    {"canonical_id": "sikh", "name_en": "Sikh", "name_te": "సిక్కు"},
    {"canonical_id": "buddhist", "name_en": "Buddhist", "name_te": "బౌద్ధ"},
    {"canonical_id": "jain", "name_en": "Jain", "name_te": "జైన"},
    {"canonical_id": "other", "name_en": "Other", "name_te": "ఇతర"},
]

# Telugu Hindu communities (MVP representative set)
TELUGU_HINDU_COMMUNITIES = [
    {"canonical_id": "kamma", "name_en": "Kamma", "name_te": "కమ్మ"},
    {"canonical_id": "kapu", "name_en": "Kapu", "name_te": "కాపు"},
    {"canonical_id": "reddy", "name_en": "Reddy", "name_te": "రెడ్డి"},
    {"canonical_id": "brahmin", "name_en": "Brahmin", "name_te": "బ్రాహ్మణ"},
    {"canonical_id": "vysya", "name_en": "Vysya / Arya Vysya", "name_te": "వైశ్య"},
    {"canonical_id": "velama", "name_en": "Velama", "name_te": "వెలమ"},
    {"canonical_id": "kshatriya", "name_en": "Kshatriya", "name_te": "క్షత్రియ"},
    {"canonical_id": "naidu", "name_en": "Naidu / Balija Naidu", "name_te": "నాయుడు"},
    {"canonical_id": "mudaliar", "name_en": "Mudaliar", "name_te": "ముదలియార్"},
    {"canonical_id": "goud", "name_en": "Goud", "name_te": "గౌడ్"},
    {"canonical_id": "padmasali", "name_en": "Padmasali", "name_te": "పద్మశాలి"},
    {"canonical_id": "munnuru_kapu", "name_en": "Munnuru Kapu", "name_te": "మున్నూరు కాపు"},
    {"canonical_id": "yadav", "name_en": "Yadav / Golla", "name_te": "యాదవ్"},
    {"canonical_id": "sc", "name_en": "SC", "name_te": "ఎస్సీ"},
    {"canonical_id": "st", "name_en": "ST", "name_te": "ఎస్టీ"},
    {"canonical_id": "bc", "name_en": "BC (Other)", "name_te": "బిసి"},
    {"canonical_id": "other_hindu", "name_en": "Other Hindu", "name_te": "ఇతర హిందూ"},
]


async def seed():
    import app.models  # noqa: F401 — ensure models are registered
    await init_db()

    from app.models.taxonomy import RegionGroup, LanguageGroup, Religion, Community
    from sqlalchemy import select

    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Religion).limit(1))
        if result.scalar_one_or_none():
            print("⚠️  Database already seeded — skipping.")
            return

        # Regions
        for r in REGIONS:
            db.add(RegionGroup(**r))

        # Language groups
        for lg in LANGUAGE_GROUPS:
            db.add(LanguageGroup(**lg))

        # Religions
        for rel in RELIGIONS:
            db.add(Religion(**rel))

        await db.flush()

        # Get IDs for FK references
        hindu_result = await db.execute(select(Religion).where(Religion.canonical_id == "hindu"))
        hindu = hindu_result.scalar_one()
        telugu_result = await db.execute(select(LanguageGroup).where(LanguageGroup.canonical_id == "telugu"))
        telugu = telugu_result.scalar_one()

        # Telugu Hindu communities
        for c in TELUGU_HINDU_COMMUNITIES:
            db.add(Community(
                canonical_id=c["canonical_id"],
                name_en=c["name_en"],
                name_te=c["name_te"],
                religion_id=hindu.id,
                language_group_id=telugu.id,
            ))

        await db.commit()
        print("✅  Taxonomy seed data loaded successfully!")
        print(f"   Regions: {len(REGIONS)}")
        print(f"   Language Groups: {len(LANGUAGE_GROUPS)}")
        print(f"   Religions: {len(RELIGIONS)}")
        print(f"   Communities: {len(TELUGU_HINDU_COMMUNITIES)}")


if __name__ == "__main__":
    asyncio.run(seed())
