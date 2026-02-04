#!/usr/bin/env python
"""
Database Seed Script.

Creates initial data for development/testing.

Run with: python seed_db.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, CharityApplication, Charity, Donation


def seed_database():
    """Seed the database with test data."""
    
    print("=" * 60)
    print("Seeding Database...")
    print("=" * 60)
    
    # Clean existing data (for repeatable seeds)
    print("Cleaning existing data...")
    Donation.query.delete()
    Charity.query.delete()
    CharityApplication.query.delete()
    User.query.delete()
    db.session.commit()
    print("✓ Cleaned existing data")
    
    # Create admin user
    admin = User(email="admin@test.com", role="admin", username="admin")
    admin.set_password("admin123")
    db.session.add(admin)
    print("✓ Created admin user: admin@test.com / admin123")
    
    # Create donor users
    donor1 = User(email="donor@test.com", role="donor", username="donor")
    donor1.set_password("donor123")
    db.session.add(donor1)
    print("✓ Created donor user: donor@test.com / donor123")
    
    donor2 = User(email="john@example.com", role="donor", username="john")
    donor2.set_password("password123")
    db.session.add(donor2)
    print("✓ Created donor user: john@example.com / password123")
    
    # Create charity users
    charity_user1 = User(email="charity@test.com", role="charity", username="charity1")
    charity_user1.set_password("charity123")
    db.session.add(charity_user1)
    print("✓ Created charity user: charity@test.com / charity123")
    
    charity_user2 = User(email="helpinghands@example.com", role="charity", username="helpinghands")
    charity_user2.set_password("password123")
    db.session.add(charity_user2)
    print("✓ Created charity user: helpinghands@example.com / password123")
    
    db.session.commit()
    print(f"✓ Created {User.query.count()} users total\n")
    
    # Create and approve charity application 1
    app1 = CharityApplication(
        user_id=charity_user1.id,
        name="Community Kitchen",
        description="Providing meals to those in need in our local community."
    )
    app1.approve()
    db.session.add(app1)
    
    charity1 = Charity(
        name="Community Kitchen",
        description="Providing meals to those in need in our local community.",
        user_id=charity_user1.id,
        is_active=True
    )
    db.session.add(charity1)
    print("✓ Created approved charity: Community Kitchen")
    
    # Create and approve charity application 2
    app2 = CharityApplication(
        user_id=charity_user2.id,
        name="Helping Hands Foundation",
        description="Supporting underprivileged children with education and healthcare."
    )
    app2.approve()
    db.session.add(app2)
    
    charity2 = Charity(
        name="Helping Hands Foundation",
        description="Supporting underprivileged children with education and healthcare.",
        user_id=charity_user2.id,
        is_active=True
    )
    db.session.add(charity2)
    print("✓ Created approved charity: Helping Hands Foundation")
    
    db.session.commit()
    print(f"✓ Created {Charity.query.count()} charities total\n")
    
    # Create donations
    donations_data = [
        {"amount": 5000, "donor_id": donor1.id, "charity_id": charity1.id, 
         "message": "Keep up the great work!", "is_anonymous": False},
        {"amount": 10000, "donor_id": donor1.id, "charity_id": charity2.id, 
         "message": "For the children!", "is_anonymous": True},
        {"amount": 2500, "donor_id": donor2.id, "charity_id": charity1.id, 
         "message": None, "is_anonymous": False},
        {"amount": 7500, "donor_id": donor2.id, "charity_id": charity2.id, 
         "message": "Happy to help!", "is_anonymous": False},
        {"amount": 15000, "donor_id": donor1.id, "charity_id": charity1.id, 
         "message": "Monthly donation", "is_recurring": True, "is_anonymous": False},
    ]
    
    for d_data in donations_data:
        donation = Donation(**d_data)
        db.session.add(donation)
    
    db.session.commit()
    print(f"✓ Created {len(donations_data)} donations\n")
    
    # Summary
    print("=" * 60)
    print("Seed Summary:")
    print("=" * 60)
    print(f"Users: {User.query.count()}")
    for user in User.query.all():
        print(f"  - {user.email} ({user.role})")
    
    print(f"\nCharities: {Charity.query.count()}")
    for charity in Charity.query.all():
        print(f"  - {charity.name} (active: {charity.is_active})")
    
    print(f"\nDonations: {Donation.query.count()}")
    total = sum(d.amount for d in Donation.query.all())
    print(f"  Total: ${total/100:.2f}")
    
    print("\n" + "=" * 60)
    print("✓ Database seeded successfully!")
    print("=" * 60)


def main():
    """Main entry point."""
    app = create_app()
    
    with app.app_context():
        seed_database()


if __name__ == "__main__":
    main()
