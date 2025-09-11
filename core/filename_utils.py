import os
import re
from datetime import datetime

def format_receipt_filename(date_str, restaurant_name, file_extension='.jpeg'):
    """
    Format filename as yyyy_mm_Restaurant Name.ext
    
    Args:
        date_str: Date in YYYY-MM-DD format
        restaurant_name: Name of the restaurant
        file_extension: File extension (default .jpeg)
    
    Returns:
        Formatted filename string
    """
    if not date_str or not restaurant_name:
        return None
    
    try:
        # Parse date to get year and month
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        year_month = date_obj.strftime('%Y_%m')
        
        # Clean restaurant name (remove special characters, limit length)
        clean_name = re.sub(r'[^\w\s-]', '', restaurant_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        clean_name = clean_name[:30]  # Limit length
        
        # Format filename
        formatted_name = f"{year_month}_{clean_name}{file_extension}"
        
        return formatted_name
        
    except (ValueError, TypeError):
        return None

def rename_receipt_file(old_path, new_filename):
    """
    Rename a receipt file to the new format
    
    Args:
        old_path: Current file path
        new_filename: New filename to use
    
    Returns:
        New file path if successful, None if failed
    """
    if not os.path.exists(old_path) or not new_filename:
        return None
    
    try:
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_filename)
        
        # Avoid overwriting existing files
        counter = 1
        base_name, ext = os.path.splitext(new_filename)
        while os.path.exists(new_path):
            new_path = os.path.join(directory, f"{base_name}_{counter}{ext}")
            counter += 1
        
        os.rename(old_path, new_path)
        return new_path
        
    except (OSError, IOError):
        return None

def get_receipt_display_name(date_str, restaurant_name):
    """
    Get display name for receipt in the format used in filenames
    
    Args:
        date_str: Date in YYYY-MM-DD format  
        restaurant_name: Name of the restaurant
    
    Returns:
        Display name string
    """
    formatted = format_receipt_filename(date_str, restaurant_name, '')
    return formatted.rstrip('_') if formatted else 'Unknown Receipt'