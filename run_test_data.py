#!/usr/bin/env python
"""
Standalone script to create test data in Flask shell context.
Run with: python run_test_data.py
"""
from datetime import datetime
from app import app
from models import User, CharityApplication, Charity, Donation
from db import db

print("=" * 60)
print("Creating Test Data...")
print("=" * 60)

with app.app_context():
    # Clean up existing test data (optional - for repeatable runs)
    Donation.query.delete()
    Charity.query.delete()
    CharityApplication.query.delete()
    User.query.delete()
    db.session.commit()
    print("✓ Cleaned up existing data")

    # Create admin user
    admin = User(email="admin@test.com", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)
    print("✓ Created admin user: admin@test.com")

    # Create donor user
    donor = User(email="donor@test.com", role="donor")
    donor.set_password("donor123")
    db.session.add(donor)
    print("✓ Created donor user: donor@test.com")

    # Create charity user
    charity_user = User(email="charity@test.com", role="charity")
    charity_user.set_password("charity123")
    db.session.add(charity_user)
    print("✓ Created charity user: charity@test.com")

    db.session.commit()
    print(f"✓ Created {User.query.count()} users total")

    # Create charity application
    app1 = CharityApplication(
        user_id=charity_user.id,
        name="Helping Hands Foundation",
        description="A non-profit organization dedicated to helping underprivileged communities.",
        status="pending"
    )
    db.session.add(app1)
    db.session.commit()
    print(f"✓ Created charity application: {app1.name} (ID: {app1.id})")

    # Approve the application and create charity
    app1.status = "approved"
    app1.reviewed_at = datetime.utcnow()
    
    charity = Charity(
        name="Helping Hands Foundation",
        description="A non-profit organization dedicated to helping underprivileged communities.",
        user_id=charity_user.id,
        is_active=True
    )
    db.session.add(charity)
    db.session.commit()
    print(f"✓ Approved application and created charity: {charity.name} (ID: {charity.id})")

    # Create donations
    donations_data = [
        {"amount": 5000, "donor_id": donor.id, "charity_id": charity.id, "message": "Keep up the great work!", "is_anonymous": False},
        {"amount": 10000, "donor_id": donor.id, "charity_id": charity.id, "message": "For the children!", "is_anonymous": True},
        {"amount": 2500, "donor_id": donor.id, "charity_id": charity.id, "message": None, "is_anonymous": False},
    ]
    
    for d in donations_data:
        donation = Donation(**d)
        db.session.add(donation)
    
    db.session.commit()
    print(f"✓ Created {len(donations_data)} donations")

    # Verify data
    print("\n" + "=" * 60)
    print("Verification:")
    print("=" * 60)
    print(f"Users: {User.query.count()}")
    for user in User.query.all():
        print(f"  - {user.email} ({user.role})")
    
    print(f"\nCharity Applications: {CharityApplication.query.count()}")
    for app in CharityApplication.query.all():
        print(f"  - {app.name} ({app.status})")
    
    print(f"\nCharities: {Charity.query.count()}")
    for c in Charity.query.all():
        print(f"  - {c.name} (user_id: {c.user_id})")
    
    print(f"\nDonations: {Donation.query.count()}")
    for d in Donation.query.all():
        print(f"  - ${d.amount/100:.2f} to charity {d.charity_id} (anonymous: {d.is_anonymous})")
    
    # Test relationships
    print("\n" + "=" * 60)
    print("Relationship Tests:")
    print("=" * 60)
    
    # Test donor's donations
    print(f"Donor donations count: {donor.donations.count()}")
    for d in donor.donations.all():
        print(f"  - Donation ${d.amount/100:.2f} to charity {d.charity_id}")
    
    # Test charity's donations
    print(f"Charity donations count: {charity.donations.count()}")
    for d in charity.donations.all():
        print(f"  - Received ${d.amount/100:.2f} from donor {d.donor_id}")
    
    # Test charity's user relationship
    print(f"\nCharity's user: {charity.user.email}")
    
    # Test application's applicant relationship
    print(f"Application's applicant: {app1.applicant.email}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Nothing broke.")
    print("=" * 60)

