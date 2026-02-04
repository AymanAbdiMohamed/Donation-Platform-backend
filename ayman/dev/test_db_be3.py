#!/usr/bin/env python3
"""
Database validation test for BE3
This script verifies that the database is properly initialized and working.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from app import app
from models import db, User, Charity, Donation, CharityApplication
from werkzeug.security import generate_password_hash

def test_database():
    """Test database functionality"""
    print("=" * 50)
    print("BE3 Database Validation Test")
    print("=" * 50)
    
    with app.app_context():
        # Check extensions
        print("✓ Flask app created successfully")
        print(f"✓ Extensions loaded: {list(app.extensions.keys())}")
        
        # Check database connection
        print(f"✓ Database session available: {hasattr(db, 'session')}")
        
        # Test basic queries
        try:
            user_count = User.query.count()
            charity_count = Charity.query.count()
            donation_count = Donation.query.count()
            application_count = CharityApplication.query.count()
            
            print("✓ Database queries working:")
            print(f"  - Users: {user_count}")
            print(f"  - Charities: {charity_count}")
            print(f"  - Donations: {donation_count}")
            print(f"  - Applications: {application_count}")
            
        except Exception as e:
            print(f"✗ Database query error: {e}")
            return False
        
        # Test database operations
        try:
            # Create test user
            test_user = User(
                username="test_be3",
                email="be3@test.com",
                password=generate_password_hash("testpass"),
                role="donor"
            )
            
            db.session.add(test_user)
            db.session.commit()
            print("✓ Database write operation successful")
            
            # Query test user
            found_user = User.query.filter_by(email="be3@test.com").first()
            if found_user:
                print(f"✓ Database read operation successful (User ID: {found_user.id})")
                
                # Clean up
                db.session.delete(found_user)
                db.session.commit()
                print("✓ Database delete operation successful")
            else:
                print("✗ Could not find test user")
                return False
                
        except Exception as e:
            print(f"✗ Database operation error: {e}")
            db.session.rollback()
            return False
        
        print("\n" + "=" * 50)
        print("SUCCESS: All database tests passed!")
        print("BE3 can now work with the database using:")
        print("- User.query.all()")
        print("- db.session.add(object)")
        print("- db.session.commit()")
        print("- db.session.rollback()")
        print("=" * 50)
        
        return True

if __name__ == "__main__":
    test_database()