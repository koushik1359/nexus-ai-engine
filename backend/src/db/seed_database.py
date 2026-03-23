"""
Nexus AI Engine — Enterprise Database Seeder
Generates realistic Venue, Event, Ticket Sales, and Merchandise data.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Date, ForeignKey, Text, MetaData
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ============================================================
# DATABASE CONNECTION
# ============================================================
DATABASE_URL = "postgresql://nexus_admin:nexus_secret_2026@localhost:5432/nexus_enterprise"
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
fake = Faker()

# ============================================================
# SCHEMA DEFINITION (The Enterprise Data Warehouse)
# ============================================================

class Venue(Base):
    __tablename__ = "venues"
    venue_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    base_operating_cost = Column(Float, nullable=False)
    venue_type = Column(String(50), nullable=False)


class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False)
    event_name = Column(String(300), nullable=False)
    artist_name = Column(String(200), nullable=False)
    genre = Column(String(50), nullable=False)
    event_date = Column(Date, nullable=False)
    fan_satisfaction_score = Column(Float, nullable=True)


class TicketSale(Base):
    __tablename__ = "ticket_sales"
    sale_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id"), nullable=False)
    ticket_type = Column(String(20), nullable=False)
    price_paid = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    purchase_date = Column(Date, nullable=False)
    channel = Column(String(50), nullable=False)


class MerchandiseInventory(Base):
    __tablename__ = "merchandise_inventory"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    units_sold = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    restock_threshold = Column(Integer, nullable=False)


# ============================================================
# DATA GENERATION
# ============================================================

VENUE_TYPES = ["Arena", "Stadium", "Theater", "Convention Center", "Amphitheater"]
GENRES = ["Rock", "Pop", "Hip-Hop", "Country", "EDM", "Jazz", "R&B", "Classical"]
TICKET_TYPES = ["General", "VIP", "Premium", "Student"]
CHANNELS = ["Online", "Box Office", "Mobile App", "Reseller"]
MERCH_CATEGORIES = ["Apparel", "Accessories", "Collectibles", "Food & Beverage"]
MERCH_ITEMS = {
    "Apparel": ["Tour T-Shirt", "Hoodie", "Cap", "Jersey"],
    "Accessories": ["Poster", "Keychain", "Wristband", "Tote Bag"],
    "Collectibles": ["Signed Album", "Limited Vinyl", "Photo Print"],
    "Food & Beverage": ["Craft Beer", "Soda Combo", "Nachos Pack", "Hot Dog Meal"],
}

US_CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"),
    ("San Antonio", "TX"), ("San Diego", "CA"), ("Dallas", "TX"),
    ("Nashville", "TN"), ("Austin", "TX"), ("Denver", "CO"),
    ("Atlanta", "GA"), ("Miami", "FL"), ("Seattle", "WA"),
]


def seed_database():
    """Main seeder function."""
    # Drop and recreate all tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    print("🏟️  Seeding Venues...")
    venues = []
    for i in range(15):
        city, state = US_CITIES[i]
        venue = Venue(
            name=f"{city} {random.choice(VENUE_TYPES)}",
            city=city,
            state=state,
            capacity=random.randint(5000, 80000),
            base_operating_cost=round(random.uniform(15000, 150000), 2),
            venue_type=random.choice(VENUE_TYPES),
        )
        venues.append(venue)
    session.add_all(venues)
    session.commit()
    print(f"   ✅ {len(venues)} venues created.")

    print("🎤  Seeding Events...")
    events = []
    start_date = datetime(2025, 1, 1)
    for _ in range(200):
        genre = random.choice(GENRES)
        event = Event(
            venue_id=random.randint(1, len(venues)),
            event_name=f"{fake.catch_phrase()} {genre} Festival",
            artist_name=fake.name(),
            genre=genre,
            event_date=start_date + timedelta(days=random.randint(0, 450)),
            fan_satisfaction_score=round(random.uniform(50, 100), 1),
        )
        events.append(event)
    session.add_all(events)
    session.commit()
    print(f"   ✅ {len(events)} events created.")

    print("🎟️  Seeding Ticket Sales...")
    ticket_sales = []
    for event in events:
        num_sales = random.randint(20, 80)
        for _ in range(num_sales):
            ticket_type = random.choice(TICKET_TYPES)
            base_price = {"General": 45, "VIP": 150, "Premium": 250, "Student": 25}
            sale = TicketSale(
                event_id=event.event_id,
                ticket_type=ticket_type,
                price_paid=round(base_price[ticket_type] * random.uniform(0.8, 1.5), 2),
                quantity=random.randint(1, 4),
                purchase_date=event.event_date - timedelta(days=random.randint(1, 90)),
                channel=random.choice(CHANNELS),
            )
            ticket_sales.append(sale)
    session.add_all(ticket_sales)
    session.commit()
    print(f"   ✅ {len(ticket_sales)} ticket sales created.")

    print("👕  Seeding Merchandise Inventory...")
    merch_items = []
    for event in events:
        num_items = random.randint(3, 8)
        for _ in range(num_items):
            category = random.choice(MERCH_CATEGORIES)
            product = random.choice(MERCH_ITEMS[category])
            stock = random.randint(50, 500)
            sold = random.randint(0, stock)
            item = MerchandiseInventory(
                event_id=event.event_id,
                product_name=product,
                category=category,
                stock_quantity=stock,
                units_sold=sold,
                unit_price=round(random.uniform(5, 75), 2),
                restock_threshold=random.randint(10, 50),
            )
            merch_items.append(item)
    session.add_all(merch_items)
    session.commit()
    print(f"   ✅ {len(merch_items)} merchandise items created.")

    session.close()
    print("\n🚀 Database seeding complete!")
    print(f"   Total Records: {len(venues) + len(events) + len(ticket_sales) + len(merch_items)}")


if __name__ == "__main__":
    seed_database()
