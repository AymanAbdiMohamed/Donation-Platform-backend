"""
User Service.

Business logic for user-related operations.
"""
from app.extensions import db
from app.models import User


class UserService:
    """Service class for user operations."""
    
    @staticmethod
    def create_user(email, password, role="donor", username=None):
        """
        Create a new user.
        
        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            role: User role (donor, charity, admin)
            username: Optional username
            
        Returns:
            User: Created user instance
            
        Raises:
            ValueError: If email already exists or role is invalid
        """
        # Check for existing email
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already registered")
        
        # Validate role
        if role not in User.VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(User.VALID_ROLES)}")
        
        # Create user
        user = User(email=email, role=role, username=username)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    @staticmethod
    def authenticate(email, password):
        """
        Authenticate a user.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            User: Authenticated user or None if authentication fails
        """
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            return user
        
        return None
    
    @staticmethod
    def get_by_id(user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User's ID
            
        Returns:
            User: User instance or None
        """
        return User.query.get(user_id)
    
    @staticmethod
    def get_by_email(email):
        """
        Get user by email.
        
        Args:
            email: User's email
            
        Returns:
            User: User instance or None
        """
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_all_users():
        """
        Get all users.
        
        Returns:
            list: List of all users
        """
        return User.query.all()
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """
        Update user attributes.
        
        Args:
            user_id: User's ID
            **kwargs: Attributes to update
            
        Returns:
            User: Updated user or None if not found
        """
        user = User.query.get(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ('id', 'password_hash'):
                setattr(user, key, value)
        
        db.session.commit()
        return user
    
    @staticmethod
    def change_password(user_id, new_password):
        """
        Change user's password.
        
        Args:
            user_id: User's ID
            new_password: New plain text password
            
        Returns:
            bool: True if password changed successfully
        """
        user = User.query.get(user_id)
        if not user:
            return False
        
        user.set_password(new_password)
        db.session.commit()
        return True
