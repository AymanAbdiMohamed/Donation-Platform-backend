"""
Helper Functions.

Common utility functions used across the application.

TODO: validate_email, format_currency, sanitize_string, and
get_pagination_params are currently unused by any route or service.
Either integrate them into routes/services or remove in next cleanup.
"""
import re


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: Email string to validate
        
    Returns:
        bool: True if valid email format
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def format_currency(cents, symbol="$"):
    """
    Format cents as currency string.
    
    Args:
        cents: Amount in cents
        symbol: Currency symbol (default: $)
        
    Returns:
        str: Formatted currency string (e.g., "$50.00")
    """
    dollars = cents / 100
    return f"{symbol}{dollars:,.2f}"


def sanitize_string(value, max_length=None):
    """
    Sanitize and optionally truncate a string.
    
    Args:
        value: String to sanitize
        max_length: Optional maximum length
        
    Returns:
        str: Sanitized string
    """
    if not value:
        return ""
    
    # Strip whitespace
    result = str(value).strip()
    
    # Truncate if needed
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result


def get_pagination_params(request, default_page=1, default_per_page=20, max_per_page=100):
    """
    Extract pagination parameters from request.
    
    Args:
        request: Flask request object
        default_page: Default page number
        default_per_page: Default items per page
        max_per_page: Maximum items per page
        
    Returns:
        tuple: (page, per_page)
    """
    try:
        page = int(request.args.get("page", default_page))
        page = max(1, page)  # Ensure positive
    except (TypeError, ValueError):
        page = default_page
    
    try:
        per_page = int(request.args.get("per_page", default_per_page))
        per_page = max(1, min(per_page, max_per_page))  # Clamp to range
    except (TypeError, ValueError):
        per_page = default_per_page
    
    return page, per_page
