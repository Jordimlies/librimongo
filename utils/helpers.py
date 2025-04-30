"""
Helper functions for the LibriMongo application.
"""

import re
import os
import hashlib
from datetime import datetime, timedelta
from flask import current_app

def sanitize_filename(filename):
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: The sanitized filename
    """
    # Replace invalid characters with underscores
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def generate_hash(text):
    """
    Generate a SHA-256 hash of the given text.
    
    Args:
        text (str): The text to hash
        
    Returns:
        str: The hexadecimal digest of the hash
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def calculate_due_date(days=14):
    """
    Calculate a due date based on the current date.
    
    Args:
        days (int): Number of days to add to the current date
        
    Returns:
        datetime: The calculated due date
    """
    return datetime.utcnow() + timedelta(days=days)

def format_date(date, format_str='%Y-%m-%d'):
    """
    Format a date object as a string.
    
    Args:
        date (datetime): The date to format
        format_str (str): The format string to use
        
    Returns:
        str: The formatted date string
    """
    if date is None:
        return ''
    return date.strftime(format_str)

def parse_date(date_str, format_str='%Y-%m-%d'):
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str (str): The date string to parse
        format_str (str): The format string to use
        
    Returns:
        datetime: The parsed datetime object, or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, format_str)
    except (ValueError, TypeError):
        return None

def paginate(items, page=1, per_page=10):
    """
    Paginate a list of items.
    
    Args:
        items (list): The items to paginate
        page (int): The page number (1-indexed)
        per_page (int): The number of items per page
        
    Returns:
        tuple: (paginated_items, total_pages, total_items)
    """
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    return items[start_idx:end_idx], total_pages, total_items

def log_activity(activity_type, user_id=None, book_id=None, details=None):
    """
    Log an activity in the application.
    
    Args:
        activity_type (str): The type of activity
        user_id (int, optional): The ID of the user involved
        book_id (int, optional): The ID of the book involved
        details (dict, optional): Additional details about the activity
    """
    activity = {
        'type': activity_type,
        'timestamp': datetime.utcnow(),
        'user_id': user_id,
        'book_id': book_id,
        'details': details or {}
    }
    
    # In a real application, this would be logged to a database or file
    current_app.logger.info(f"Activity: {activity}")