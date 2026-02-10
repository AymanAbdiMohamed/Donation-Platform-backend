"""
File Upload Utility.

Provides secure file upload handling for charity documents and images.

⚠️  WARNING — EPHEMERAL STORAGE (MVP)
Files are saved to the local filesystem (instance/uploads/).
On Render's ephemeral disk, uploads are LOST on every redeploy.
This is accepted for MVP.  Post-MVP, migrate to S3 / Cloudinary.
TODO: Replace local storage with a durable object-store before production scale.
"""
import os
import uuid
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app


# Allowed file extensions for document uploads
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

# Allowed file extensions for logo images
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

# Maximum file size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes


def validate_file_type(file, allowed_extensions):
    """
    Validate file extension.
    
    Args:
        file: Flask File object
        allowed_extensions: Set of allowed extensions
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    filename = file.filename
    if not filename:
        return False, "No filename provided"
    
    # Get file extension
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if not ext:
        return False, "File has no extension"
    
    if ext not in allowed_extensions:
        return False, f"File type '.{ext}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_file_size(file, max_size=MAX_FILE_SIZE):
    """
    Validate file size.
    
    Args:
        file: Flask File object
        max_size: Maximum file size in bytes
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    # Get file content length from headers if available
    content_length = request_content_length(file)
    
    if content_length and content_length > max_size:
        size_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum allowed ({size_mb:.1f}MB)"
    
    return True, None


def request_content_length(file):
    """
    Get content length from file headers.
    
    Args:
        file: Flask File object
        
    Returns:
        int: Content length in bytes or None
    """
    try:
        # Try to get content length from headers
        content_length = file.content_length
        if content_length > 0:
            return content_length
    except AttributeError:
        pass
    
    # Fallback: try stream
    try:
        file.stream.seek(0, 2)  # Seek to end
        length = file.stream.tell()
        file.stream.seek(0)  # Reset to beginning
        return length
    except (AttributeError, OSError):
        pass
    
    return None


def generate_secure_filename(original_filename):
    """
    Generate a secure, unique filename.
    
    Args:
        original_filename: Original file name
        
    Returns:
        str: Secure unique filename
    """
    # Use secure_filename to sanitize
    secure_name = secure_filename(original_filename)
    
    # Get extension
    ext = ''
    if '.' in secure_name:
        ext = '.' + secure_name.rsplit('.', 1)[-1].lower()
    
    # Generate unique filename with timestamp and UUID
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    return f"{timestamp}_{unique_id}{ext}"


def generate_storage_path(file_type, user_id, filename):
    """
    Generate storage path for uploaded file.
    
    Args:
        file_type: Type of file (documents, logos, etc.)
        user_id: User ID
        filename: Original or generated filename
        
    Returns:
        str: Storage path relative to upload directory
    """
    # Generate secure filename
    secure_filename = generate_secure_filename(filename)
    
    # Create path structure: type/year/month/user_id/filename
    date_parts = datetime.utcnow().strftime('%Y/%m')
    
    path = f"{file_type}/{date_parts}/{user_id}/{secure_filename}"
    
    return path


def get_absolute_upload_path(relative_path):
    """
    Get absolute path for file storage.
    
    Args:
        relative_path: Relative path from upload base
        
    Returns:
        str: Absolute path
    """
    base_path = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # Handle absolute paths
    if os.path.isabs(base_path):
        return os.path.join(base_path, relative_path)
    
    # Join with the app root directory (no circular import)
    return os.path.join(current_app.root_path, '..', base_path, relative_path)


def ensure_upload_directory(path):
    """
    Ensure the upload directory exists.
    
    Args:
        path: Directory path to create
        
    Returns:
        bool: True if directory exists or was created
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError as e:
        current_app.logger.error(f"Failed to create upload directory: {e}")
        return False


def save_uploaded_file(file, storage_path, max_size=MAX_FILE_SIZE):
    """
    Save uploaded file to storage.
    
    Args:
        file: Flask File object
        storage_path: Relative storage path
        max_size: Maximum file size in bytes
        
    Returns:
        tuple: (success, result or error_message)
    """
    # Validate file type
    ext = storage_path.rsplit('.', 1)[-1].lower() if '.' in storage_path else ''
    
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ALLOWED_IMAGE_EXTENSIONS
    else:
        allowed = ALLOWED_DOCUMENT_EXTENSIONS
    
    is_valid, error = validate_file_type(file, allowed)
    if not is_valid:
        return False, error
    
    # Validate file size
    is_valid, error = validate_file_size(file, max_size)
    if not is_valid:
        return False, error
    
    # Get absolute path
    absolute_path = get_absolute_upload_path(storage_path)
    
    # Ensure directory exists
    directory = os.path.dirname(absolute_path)
    if not ensure_upload_directory(directory):
        return False, "Failed to create upload directory"
    
    try:
        # Save file
        file.save(absolute_path)
        
        # Get file size
        file_size = os.path.getsize(absolute_path)
        
        return True, {
            'path': storage_path,
            'size': file_size,
            'filename': os.path.basename(storage_path)
        }
    
    except Exception as e:
        current_app.logger.error(f"Failed to save file: {e}")
        return False, "Failed to save file"


def delete_file(relative_path):
    """
    Delete a file from storage.
    
    Args:
        relative_path: Relative path to file
        
    Returns:
        bool: True if deleted successfully
    """
    try:
        absolute_path = get_absolute_upload_path(relative_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to delete file: {e}")
        return False


def get_file_url(relative_path):
    """
    Generate URL for accessing uploaded file.
    
    Args:
        relative_path: Relative path to file
        
    Returns:
        str: URL for file access
    """
    base_url = current_app.config.get('UPLOAD_BASE_URL', '/uploads')
    return f"{base_url}/{relative_path}"

