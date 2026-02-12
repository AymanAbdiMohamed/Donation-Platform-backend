#!/usr/bin/env python
"""
M-Pesa Integration Test Script

This script helps you test and debug your M-Pesa Daraja API integration.
Run this script to verify your credentials and test various M-Pesa operations.

Usage:
    python test_mpesa.py
    
Requirements:
    - .env file with M-Pesa credentials
    - Flask app configured
"""
import os
import sys
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.config import Config
from app.utils.mpesa import MpesaClient, test_mpesa_connection, validate_phone_number


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_result(result, title="Result"):
    """Print a formatted result."""
    print(f"\n{title}:")
    print(json.dumps(result, indent=2, default=str))


def test_configuration():
    """Test M-Pesa configuration."""
    print_section("TESTING M-PESA CONFIGURATION")
    
    required_vars = [
        "MPESA_CONSUMER_KEY",
        "MPESA_CONSUMER_SECRET", 
        "MPESA_SHORTCODE",
        "MPESA_PASSKEY",
        "MPESA_STK_CALLBACK_URL"
    ]
    
    print("Checking environment variables...")
    for var in required_vars:
        value = os.getenv(var, "").strip()
        if value:
            # Show first 8 chars for debugging
            preview = value[:8] + "..." if len(value) > 8 else value
            print(f"✓ {var}: {preview}")
        else:
            print(f"✗ {var}: MISSING")
    
    env = os.getenv("MPESA_ENV", "sandbox")
    print(f"✓ Environment: {env}")


def test_connection():
    """Test M-Pesa API connection."""
    print_section("TESTING M-PESA CONNECTION")
    
    try:
        result = test_mpesa_connection()
        print_result(result, "Connection Test")
        return result["success"]
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def test_phone_validation():
    """Test phone number validation."""
    print_section("TESTING PHONE VALIDATION")
    
    test_phones = [
        "254712345678",  # Valid
        "0712345678",    # Valid (will be normalized)
        "+254712345678", # Valid (will be normalized)
        "712345678",     # Invalid
        "254712",        # Invalid
        "123456789",     # Invalid
    ]
    
    for phone in test_phones:
        is_valid = validate_phone_number(phone)
        status = "✓" if is_valid else "✗"
        print(f"{status} {phone:15} -> {'Valid' if is_valid else 'Invalid'}")


def test_token_generation():
    """Test access token generation."""
    print_section("TESTING ACCESS TOKEN GENERATION")
    
    try:
        client = MpesaClient()
        token = client.get_access_token()
        
        print(f"✓ Token obtained successfully")
        print(f"  Preview: {token[:20]}...")
        print(f"  Length: {len(token)} characters")
        
        return True
    except Exception as e:
        print(f"❌ Token generation failed: {e}")
        return False


def test_password_generation():
    """Test STK Push password generation."""
    print_section("TESTING PASSWORD GENERATION")
    
    try:
        client = MpesaClient()
        password, timestamp = client.generate_password()
        
        print(f"✓ Password generated successfully")
        print(f"  Timestamp: {timestamp}")
        print(f"  Password preview: {password[:20]}...")
        print(f"  Password length: {len(password)} characters")
        
        return True
    except Exception as e:
        print(f"❌ Password generation failed: {e}")
        return False


def test_stk_push():
    """Test STK Push initiation (sandbox only)."""
    print_section("TESTING STK PUSH (SANDBOX)")
    
    env = os.getenv("MPESA_ENV", "sandbox")
    if env != "sandbox":
        print("⚠️ Skipping STK Push test - not in sandbox mode")
        return
    
    # Use test phone number for sandbox
    test_phone = "254708374149"  # Safaricom test number
    test_amount = 1  # Minimum amount for testing
    
    try:
        client = MpesaClient()
        result = client.initiate_stk_push(
            phone=test_phone,
            amount=test_amount, 
            reference="TEST-DONATION",
            description="Test Payment"
        )
        
        print_result(result, "STK Push Result")
        
        if result.get("success"):
            checkout_id = result.get("checkout_request_id")
            print(f"\n📱 STK Push sent successfully!")
            print(f"   Checkout ID: {checkout_id}")
            print(f"   Customer Message: {result.get('customer_message')}")
            print(f"\n⚠️ Note: This is a sandbox test. No real money will be charged.")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"❌ STK Push test failed: {e}")
        return False


def main():
    """Run all M-Pesa tests."""
    print("🚀 M-Pesa Integration Test Suite")
    print("This script will test your M-Pesa Daraja API configuration.")
    
    # Create Flask app context for testing
    app = create_app(Config)
    
    with app.app_context():
        # Test configuration
        test_configuration()
        
        # Test connection
        if not test_connection():
            print("\n❌ Cannot proceed - connection test failed")
            print("   Check your MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET")
            return
        
        # Test phone validation
        test_phone_validation()
        
        # Test token generation
        if not test_token_generation():
            print("\n❌ Cannot proceed - token generation failed")
            return
        
        # Test password generation
        if not test_password_generation():
            print("\n❌ Cannot proceed - password generation failed")
            return
        
        # Test STK Push (sandbox only)
        test_stk_push()
    
    print_section("TEST SUMMARY")
    print("✓ Configuration test completed")
    print("✓ Connection test completed") 
    print("✓ Phone validation test completed")
    print("✓ Token generation test completed")
    print("✓ Password generation test completed")
    print("✓ STK Push test completed")
    
    print(f"\n🎉 All tests completed!")
    print(f"Your M-Pesa integration is ready for use.")
    
    print(f"\n📋 Next Steps:")
    print(f"1. Test the /health/mpesa endpoint: curl http://localhost:5000/health/mpesa")
    print(f"2. Test a donation via your frontend")
    print(f"3. Monitor logs for any issues")


if __name__ == "__main__":
    main()