"""
Backend Module B - Development workspace for BE3
This module contains backend functionality and utilities for the donation platform.
"""

from flask import Flask, request, jsonify, Blueprint
from functools import wraps
import sqlite3
import hashlib
import jwt
from datetime import datetime, timedelta
import os

# Import from parent modules
import sys
sys.path.append('../../')
from models import db, User, Charity, Donation
from config import Config

# Create blueprint for this module
b_bp = Blueprint('b', __name__)

class BackendHelper:
    """Helper class for backend operations"""
    
    @staticmethod
    def hash_password(password):
        """Hash password for secure storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, hashed):
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    @staticmethod
    def generate_token(user_id, role):
        """Generate JWT token for authentication"""
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

class DataProcessor:
    """Class for processing donation platform data"""
    
    @staticmethod
    def process_donation_data(donation_data):
        """Process donation data before saving"""
        processed = {}
        processed['amount'] = float(donation_data.get('amount', 0))
        processed['donor_id'] = int(donation_data.get('donor_id'))
        processed['charity_id'] = int(donation_data.get('charity_id'))
        processed['message'] = donation_data.get('message', '').strip()
        processed['timestamp'] = datetime.utcnow()
        return processed
    
    @staticmethod
    def validate_donation_amount(amount):
        """Validate donation amount"""
        try:
            amount = float(amount)
            return amount > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def format_response(success=True, message="", data=None):
        """Format standard API response"""
        response = {
            'success': success,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        if data is not None:
            response['data'] = data
        return response

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = BackendHelper.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.user_id = payload['user_id']
        request.user_role = payload['role']
        return f(*args, **kwargs)
    
    return decorated_function

@b_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify module is working"""
    return jsonify(DataProcessor.format_response(
        success=True, 
        message="Backend module B is working correctly",
        data={'module': 'b.py', 'status': 'active'}
    ))

@b_bp.route('/process-donation', methods=['POST'])
@require_auth
def process_donation():
    """Process a new donation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(key in data for key in ['amount', 'charity_id']):
            return jsonify(DataProcessor.format_response(
                success=False, 
                message="Missing required fields"
            )), 400
        
        # Validate donation amount
        if not DataProcessor.validate_donation_amount(data['amount']):
            return jsonify(DataProcessor.format_response(
                success=False, 
                message="Invalid donation amount"
            )), 400
        
        # Process donation data
        processed_data = DataProcessor.process_donation_data(data)
        processed_data['donor_id'] = request.user_id
        
        # Create donation record
        donation = Donation(
            donor_id=processed_data['donor_id'],
            charity_id=processed_data['charity_id'],
            amount=processed_data['amount'],
            message=processed_data['message'],
            created_at=processed_data['timestamp']
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return jsonify(DataProcessor.format_response(
            success=True,
            message="Donation processed successfully",
            data={'donation_id': donation.id}
        ))
        
    except Exception as e:
        return jsonify(DataProcessor.format_response(
            success=False,
            message=f"Error processing donation: {str(e)}"
        )), 500

@b_bp.route('/analytics', methods=['GET'])
@require_auth
def get_analytics():
    """Get donation analytics (for admin/charity users)"""
    try:
        if request.user_role not in ['admin', 'charity']:
            return jsonify(DataProcessor.format_response(
                success=False,
                message="Insufficient permissions"
            )), 403
        
        # Basic analytics
        total_donations = Donation.query.count()
        total_amount = db.session.query(db.func.sum(Donation.amount)).scalar() or 0
        
        analytics_data = {
            'total_donations': total_donations,
            'total_amount': float(total_amount),
            'average_donation': float(total_amount / max(total_donations, 1))
        }
        
        return jsonify(DataProcessor.format_response(
            success=True,
            message="Analytics retrieved successfully",
            data=analytics_data
        ))
        
    except Exception as e:
        return jsonify(DataProcessor.format_response(
            success=False,
            message=f"Error retrieving analytics: {str(e)}"
        )), 500

# Utility functions for BE3
def debug_print(message, level="INFO"):
    """Debug print with timestamp"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def get_database_stats():
    """Get database statistics"""
    try:
        users_count = User.query.count()
        charities_count = Charity.query.count()
        donations_count = Donation.query.count()
        
        return {
            'users': users_count,
            'charities': charities_count,
            'donations': donations_count
        }
    except Exception as e:
        debug_print(f"Error getting database stats: {str(e)}", "ERROR")
        return None

# Example usage and testing functions
if __name__ == "__main__":
    print("Backend Module B - Development Environment")
    print("This module is ready for BE3 to work with.")
    print("\nAvailable classes and functions:")
    print("- BackendHelper: Authentication and utility functions")
    print("- DataProcessor: Data processing and validation")
    print("- require_auth: Authentication decorator")
    print("- Blueprint routes: /test, /process-donation, /analytics")
    print("\nUtility functions:")
    print("- debug_print(): Debug logging with timestamps")
    print("- get_database_stats(): Database statistics")