#!/usr/bin/env python
"""
Database Seed Script.

Creates realistic demo data for the SheNeeds platform.
WARNING: Drops and recreates all tables — development only.

Run with: python seed_db.py
"""
import os
import sys
from datetime import timedelta

os.environ["FLASK_CLI_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, CharityApplication, Charity, Donation
from app.models.donation import DonationStatus
from app.utils.helpers import utc_now


# ---------------------------------------------------------------------------
# Charity data — real-sounding Kenyan menstrual health organisations
# ---------------------------------------------------------------------------

CHARITIES = [
    {
        "email": "info@afyayangu.co.ke",
        "username": "afyayangu",
        "name": "Afya Yangu Foundation",
        "description": (
            "Afya Yangu Foundation works in Nairobi's informal settlements — Kibera, "
            "Mathare, and Korogocho — to ensure schoolgirls never miss class due to "
            "lack of menstrual supplies. We run monthly distribution drives, train "
            "community health volunteers, and partner with local schools to embed "
            "menstrual health education into the curriculum."
        ),
        "mission": (
            "To eliminate period poverty in Nairobi's informal settlements by providing "
            "sustainable access to menstrual hygiene products and education."
        ),
        "goals": "Target: 10-18 years | Programme: School-based pad distribution | Reach: 8,000 girls/year",
        "category": "health",
        "location": "Nairobi — Kibera, Mathare, Korogocho",
        "contact_email": "info@afyayangu.co.ke",
        "contact_phone": "+254 700 123 456",
        "website": "https://afyayangu.co.ke",
    },
    {
        "email": "hello@sherises.or.ke",
        "username": "sherises",
        "name": "She Rises Initiative",
        "description": (
            "She Rises Initiative operates across Western Kenya's fishing communities "
            "and rural schools in Siaya, Kisumu, and Homa Bay counties. We manufacture "
            "reusable sanitary pads locally — creating income for women's groups while "
            "providing affordable, sustainable menstrual products to girls in the region."
        ),
        "mission": (
            "Empower girls in Western Kenya through sustainable menstrual hygiene "
            "solutions and reproductive health education, keeping them in school."
        ),
        "goals": "Target: 9-20 years | Programme: Reusable pad manufacturing + distribution | Reach: 12,000 girls/year",
        "category": "health",
        "location": "Western Kenya — Kisumu, Siaya, Homa Bay",
        "contact_email": "hello@sherises.or.ke",
        "contact_phone": "+254 711 234 567",
        "website": "https://sherises.or.ke",
    },
    {
        "email": "contact@pinkpowerkenya.org",
        "username": "pinkpower",
        "name": "Pink Power Kenya",
        "description": (
            "Pink Power Kenya focuses on rural schools in the Rift Valley — Nakuru, "
            "Baringo, and Laikipia counties — where girls have the least access to "
            "menstrual products. We install hand-washing stations, stock school sanitation "
            "rooms, and run peer-educator programmes training older students to support "
            "their younger peers."
        ),
        "mission": (
            "Build dignified, safe sanitation environments in rural Rift Valley schools "
            "so that menstruation is never a reason a girl stays home."
        ),
        "goals": "Target: 10-17 years | Programme: WASH + peer education | Reach: 6,500 girls/year",
        "category": "education",
        "location": "Rift Valley — Nakuru, Baringo, Laikipia",
        "contact_email": "contact@pinkpowerkenya.org",
        "contact_phone": "+254 722 345 678",
        "website": "https://pinkpowerkenya.org",
    },
    {
        "email": "team@inuamama.or.ke",
        "username": "inuamama",
        "name": "Inua Mama Kenya",
        "description": (
            "Inua Mama Kenya serves girls in North Rift counties — Elgeyo Marakwet, "
            "West Pokot, and Turkana — where FGM, early marriage, and period poverty "
            "intersect. Beyond pad distribution, we run safe-house programmes, work "
            "with community elders to shift norms, and provide psychosocial support "
            "to girls who have experienced gender-based violence."
        ),
        "mission": (
            "Protect girls in North Rift Kenya from FGM and early marriage while "
            "ensuring menstrual health is never a barrier to education or safety."
        ),
        "goals": "Target: 8-20 years | Programme: Safe-house + menstrual health | Reach: 3,200 girls/year",
        "category": "humanitarian",
        "location": "North Rift — Elgeyo Marakwet, West Pokot, Turkana",
        "contact_email": "team@inuamama.or.ke",
        "contact_phone": "+254 733 456 789",
        "website": "https://inuamama.or.ke",
    },
    {
        "email": "info@mwanafunzishe.org",
        "username": "mwanafunzi",
        "name": "Mwanafunzi She Foundation",
        "description": (
            "Mwanafunzi She Foundation works along the Kenyan coast — Kilifi, Kwale, "
            "and Tana River counties — where poverty and distance from towns make "
            "menstrual products inaccessible to most schoolgirls. Our mobile outreach "
            "teams visit remote schools quarterly, combining pad distribution with "
            "training for teachers on how to handle menstruation-related absenteeism."
        ),
        "mission": (
            "Ensure that every girl on the Kenyan coast has what she needs to attend "
            "school every day of the month, every month of the year."
        ),
        "goals": "Target: 10-19 years | Programme: Mobile outreach + teacher training | Reach: 5,800 girls/year",
        "category": "education",
        "location": "Coast — Kilifi, Kwale, Tana River",
        "contact_email": "info@mwanafunzishe.org",
        "contact_phone": "+254 744 567 890",
        "website": "https://mwanafunzishe.org",
    },
]

# ---------------------------------------------------------------------------
# Donation scenarios — amounts in cents (KES * 100), all SUCCESS
# ---------------------------------------------------------------------------

DONATION_SCENARIOS = [
    # (donor_index, charity_index, amount_kes, is_anonymous, is_recurring, message, days_ago)
    (0, 0, 1500, False, False, "Keep up the amazing work in Kibera!", 45),
    (0, 1, 2500, False, True,  "Monthly contribution — stay strong.", 30),
    (0, 2, 500,  True,  False, None, 20),
    (0, 3, 1000, False, False, "Every girl deserves to stay in school.", 12),
    (0, 4, 750,  False, False, "Proud to support coastal communities.", 5),
    (1, 0, 3000, False, True,  "Recurring — for Nairobi's girls.", 60),
    (1, 1, 5000, True,  False, None, 35),
    (1, 2, 2000, False, False, "Rift Valley schools need this support.", 18),
    (1, 3, 500,  False, False, "Small but consistent. Keep going!", 8),
    (2, 0, 10000, False, False, "Corporate donation — team fundraiser.", 25),
    (2, 1, 1500, True,  False, None, 14),
    (2, 4, 3500, False, True,  "Monthly — coast communities matter.", 7),
]


def seed_database():
    print("=" * 60)
    print("Seeding SheNeeds database...")
    print("=" * 60)

    # ── Users ────────────────────────────────────────────────────
    print("\nCreating users...")

    admin = User(email="admin@sheneeds.dev", role="admin", username="admin")
    admin.set_password("admin123")
    db.session.add(admin)

    donors = []
    donor_data = [
        ("donor@sheneeds.dev", "donor", "donor123"),
        ("wanjiku@example.co.ke", "wanjiku", "password123"),
        ("odhiambo@example.co.ke", "odhiambo", "password123"),
    ]
    for email, username, password in donor_data:
        d = User(email=email, role="donor", username=username)
        d.set_password(password)
        db.session.add(d)
        donors.append(d)

    charity_users = []
    for c in CHARITIES:
        u = User(email=c["email"], role="charity", username=c["username"])
        u.set_password("charity123")
        db.session.add(u)
        charity_users.append(u)

    db.session.commit()
    print(f"  ✓ {User.query.count()} users created")

    # ── Charities ────────────────────────────────────────────────
    print("\nCreating charities...")
    charities = []

    for i, c_data in enumerate(CHARITIES):
        user = charity_users[i]

        # Approved application
        app = CharityApplication(
            user_id=user.id,
            name=c_data["name"],
            description=c_data["description"],
            mission=c_data["mission"],
            goals=c_data["goals"],
            category=c_data["category"],
            location=c_data["location"],
            contact_email=c_data["contact_email"],
            contact_phone=c_data["contact_phone"],
            website=c_data.get("website"),
        )
        app.approve()
        db.session.add(app)

        # Active charity record
        charity = Charity(
            user_id=user.id,
            name=c_data["name"],
            description=c_data["description"],
            mission=c_data["mission"],
            goals=c_data["goals"],
            category=c_data["category"],
            location=c_data["location"],
            contact_email=c_data["contact_email"],
            contact_phone=c_data["contact_phone"],
            website=c_data.get("website"),
            is_active=True,
        )
        db.session.add(charity)
        charities.append(charity)
        print(f"  ✓ {c_data['name']}")

    db.session.commit()

    # ── Donations ────────────────────────────────────────────────
    print("\nCreating donations...")
    now = utc_now()

    for donor_i, charity_i, amount_kes, is_anon, is_recurring, message, days_ago in DONATION_SCENARIOS:
        donation = Donation(
            amount=amount_kes * 100,          # store in cents
            donor_id=donors[donor_i].id,
            charity_id=charities[charity_i].id,
            status=DonationStatus.SUCCESS,     # explicitly SUCCESS — not PENDING
            is_anonymous=is_anon,
            is_recurring=is_recurring,
            message=message,
            mpesa_receipt_number=f"QGK{now.strftime('%Y%m%d')}{donor_i}{charity_i}{amount_kes}",
            payment_method="STK_PUSH",
            verification_status="VERIFIED",
        )
        # Backdate created_at so analytics charts have spread data
        donation.created_at = now - timedelta(days=days_ago)
        donation.updated_at = donation.created_at
        db.session.add(donation)

    db.session.commit()
    print(f"  ✓ {Donation.query.count()} donations created (all SUCCESS)")

    # ── One pending application (for admin demo) ─────────────────
    print("\nCreating pending application for admin demo...")
    pending_user = User(
        email="zawadi@example.co.ke",
        role="charity",
        username="zawadi"
    )
    pending_user.set_password("charity123")
    db.session.add(pending_user)
    db.session.flush()

    pending_app = CharityApplication(
        user_id=pending_user.id,
        name="Zawadi Girls Network",
        description=(
            "We provide menstrual hygiene kits and reproductive health education to "
            "girls in Kakamega and Vihiga counties in Western Kenya."
        ),
        mission="Ensuring every girl in Western Kenya has access to menstrual hygiene products and education.",
        goals="Target: 10-18 years | Programme: Kit distribution + school education | Reach: 4,000 girls/year",
        category="health",
        location="Western Kenya — Kakamega, Vihiga",
        contact_email="zawadi@example.co.ke",
        contact_phone="+254 755 678 901",
        status="draft",                        # explicit — column default not applied until flush
    )
    db.session.add(pending_app)
    db.session.flush()                         # persist so .submit() sees status="draft"
    pending_app.submit()
    db.session.commit()
    print("  ✓ Zawadi Girls Network — pending review")

    # ── Summary ─────────────────────────────────────────────────
    total_kes = sum(d.amount for d in Donation.query.all()) / 100
    print("\n" + "=" * 60)
    print("Seed complete.")
    print("=" * 60)
    print(f"\nUsers ({User.query.count()}):")
    for u in User.query.order_by(User.role).all():
        print(f"  {u.role:<10} {u.email}")
    print(f"\nCharities: {Charity.query.count()} active")
    print(f"Applications: {CharityApplication.query.filter_by(status='submitted').count()} pending review")
    print(f"Donations: {Donation.query.count()} (KES {total_kes:,.0f} total)")
    print("\nTest credentials (all roles use the password shown):")
    print("  admin@sheneeds.dev       admin123")
    print("  donor@sheneeds.dev       donor123")
    print("  wanjiku@example.co.ke    password123")
    print("  info@afyayangu.co.ke     charity123  (approved charity)")
    print("  zawadi@example.co.ke     charity123  (pending application)")


def main():
    app = create_app()
    with app.app_context():
        print("Dropping existing tables...")
        db.drop_all()
        print("Creating tables...")
        db.create_all()
        seed_database()


if __name__ == "__main__":
    main()
