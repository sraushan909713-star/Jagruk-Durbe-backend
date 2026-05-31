# app/seed/mandi_seed.py
# ─────────────────────────────────────────────────────────────
# One-time seed script for Mandi items.
# Units are seeded by the Alembic migration; this only handles
# items, which you may want to customize before running.
#
# Run: python -m app.seed.mandi_seed
#
# Safe to re-run — checks for existing items by name.
# Edit the ITEMS list below before running if you want a
# different starter catalog.
# ─────────────────────────────────────────────────────────────

import uuid
from app.database import SessionLocal
from app.models.item import Item
from app.models.unit import Unit


# ── Starter item catalog ─────────────────────────────────────
# (name, name_hindi, default_unit_name, category, display_order)
ITEMS = [
    # Buy-side items (vendors buy from farmers — seasonal)
    ("Dhaan",          "धान",            "quintal", "grain", 100),
    ("Sarso",          "सरसों",          "quintal", "oilseed", 101),
    ("Gehu",           "गेहूँ",          "quintal", "grain", 102),

    # Sell-side staples (vendors sell to villagers — daily)
    ("Chawal",         "चावल",           "kg",      "grain", 1),
    ("Gehun ka Atta",  "गेहूँ का आटा",   "kg",      "grain", 2),
    ("Sarso Tel",      "सरसों का तेल",   "litre",   "oil", 3),
    ("Kadua Tel",      "कड़वा तेल",       "litre",   "oil", 4),
    ("Khali",          "खली",            "kg",      "feed", 5),
    ("Choker",         "छोकर",           "kg",      "feed", 6),
]


def seed():
    db = SessionLocal()
    try:
        # Build a lookup of units by name
        units_by_name = {u.name: u.id for u in db.query(Unit).filter(Unit.is_active == True).all()}
        if not units_by_name:
            print("❌ No units found. Run `alembic upgrade head` first to seed units.")
            return

        added = 0
        skipped = 0
        for name, name_hindi, unit_name, category, display_order in ITEMS:
            existing = db.query(Item).filter(Item.name == name, Item.is_active == True).first()
            if existing:
                skipped += 1
                continue

            unit_id = units_by_name.get(unit_name)
            if not unit_id:
                print(f"⚠️  Unit '{unit_name}' not found for item '{name}'. Skipping.")
                continue

            item = Item(
                id=str(uuid.uuid4()),
                name=name,
                name_hindi=name_hindi,
                default_unit_id=unit_id,
                category=category,
                display_order=display_order,
                is_custom=False,
            )
            db.add(item)
            added += 1

        db.commit()
        print(f"✅ Seed complete. Added: {added}, Skipped (already exist): {skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()