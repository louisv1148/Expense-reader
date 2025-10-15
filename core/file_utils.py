"""
Utility functions for file handling, sanitization, and PDF conversion
"""
import os
import re
import unicodedata
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader


def sanitize_filename(text):
    """
    Sanitize text for use in filenames.
    Removes accents, special characters, and replaces spaces with underscores.

    Examples:
        "Café René" -> "Cafe_Rene"
        "Restaurant & Bar!" -> "Restaurant_Bar"
        "  Multiple   Spaces  " -> "Multiple_Spaces"
    """
    if not text:
        return "Unknown"

    # Remove accents: Café -> Cafe
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')

    # Remove special characters, keep alphanumeric, spaces, hyphens, underscores
    text = re.sub(r'[^\w\s-]', '', text)

    # Replace multiple spaces/hyphens with single underscore
    text = re.sub(r'[-\s]+', '_', text)

    # Remove leading/trailing underscores
    text = text.strip('_')

    return text if text else "Unknown"


def format_receipt_filename(date, restaurant_name):
    """
    Format receipt filename according to yyyy_mm_RestaurantName pattern.

    Args:
        date: Date string in YYYY-MM-DD format
        restaurant_name: Restaurant name to sanitize

    Returns:
        Formatted filename without extension (e.g., "2025_10_Cafe_Rene")
    """
    if not date or not restaurant_name:
        return None

    # Extract year and month from date (YYYY-MM-DD -> YYYY_MM)
    try:
        year_month = date[:7].replace('-', '_')  # "2025-10-15" -> "2025_10"
    except:
        return None

    # Sanitize restaurant name
    sanitized_name = sanitize_filename(restaurant_name)

    # Format: yyyy_mm_RestaurantName
    return f"{year_month}_{sanitized_name}"


def get_export_folder(year_month=None):
    """
    Get the export folder path, creating it if necessary.

    Args:
        year_month: Optional YYYY_MM string for subfolder (e.g., "2025_10")

    Returns:
        Path object for export folder
    """
    base_folder = Path.home() / 'Downloads' / 'Expense_Receipts'

    if year_month:
        export_folder = base_folder / year_month
    else:
        export_folder = base_folder

    # Create folder if it doesn't exist
    export_folder.mkdir(parents=True, exist_ok=True)

    return export_folder


def get_unique_filename(folder, base_name, extension):
    """
    Generate a unique filename by adding _2, _3, etc. if file exists.

    Args:
        folder: Path object for destination folder
        base_name: Base filename without extension
        extension: File extension (e.g., ".pdf")

    Returns:
        Unique filename string
    """
    filename = f"{base_name}{extension}"
    filepath = folder / filename

    if not filepath.exists():
        return filename

    # File exists, add counter
    counter = 2
    while True:
        filename = f"{base_name}_{counter}{extension}"
        filepath = folder / filename
        if not filepath.exists():
            return filename
        counter += 1


def convert_image_to_pdf(image_path, output_path):
    """
    Convert an image file to PDF format using ReportLab.
    Maintains aspect ratio and fits to letter size page.

    Args:
        image_path: Path to source image file
        output_path: Path for output PDF file

    Returns:
        True if successful, False otherwise
    """
    try:
        # If already a PDF, just copy it
        if str(image_path).lower().endswith('.pdf'):
            import shutil
            shutil.copy(image_path, output_path)
            return True

        # Open image with PIL to get dimensions
        img = Image.open(image_path)

        # Convert RGBA to RGB if necessary (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        img_width, img_height = img.size

        # Create PDF with letter size
        page_width, page_height = letter

        # Calculate scaling to fit image on page with margins
        margin = 36  # 0.5 inch margins
        max_width = page_width - (2 * margin)
        max_height = page_height - (2 * margin)

        # Calculate aspect ratio scaling
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scale = min(width_ratio, height_ratio)

        # New dimensions
        new_width = img_width * scale
        new_height = img_height * scale

        # Center on page
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2

        # Create PDF
        c = canvas.Canvas(str(output_path), pagesize=letter)

        # Draw image
        c.drawImage(ImageReader(img), x, y, width=new_width, height=new_height)

        # Save PDF
        c.save()

        return True

    except Exception as e:
        print(f"Error converting {image_path} to PDF: {e}")
        return False


def export_organized_receipts(receipts, db):
    """
    Export all reviewed receipts as organized PDFs to Downloads folder.

    Args:
        receipts: List of receipt dictionaries
        db: ExpenseDatabase instance

    Returns:
        Dictionary with success status, folder path, and stats
    """
    try:
        exported_files = []
        skipped_files = []

        for receipt in receipts:
            if not receipt.get('reviewed'):
                continue

            # Get source file
            source_path = receipt.get('file_path')
            if not source_path or not os.path.exists(source_path):
                skipped_files.append(f"Missing file: {receipt.get('filename', 'Unknown')}")
                continue

            # Get date and restaurant name
            date = receipt.get('date')
            restaurant_name = receipt.get('restaurant_name')

            if not date or not restaurant_name:
                skipped_files.append(f"Missing data: {receipt.get('filename', 'Unknown')}")
                continue

            # Format filename
            base_name = format_receipt_filename(date, restaurant_name)
            if not base_name:
                skipped_files.append(f"Invalid date/name: {receipt.get('filename', 'Unknown')}")
                continue

            # Get year_month for subfolder (e.g., "2025_10")
            year_month = date[:7].replace('-', '_')

            # Get export folder
            export_folder = get_export_folder(year_month)

            # Get unique filename
            output_filename = get_unique_filename(export_folder, base_name, '.pdf')
            output_path = export_folder / output_filename

            # Convert to PDF
            if convert_image_to_pdf(source_path, output_path):
                exported_files.append(str(output_path))
            else:
                skipped_files.append(f"Conversion failed: {receipt.get('filename', 'Unknown')}")

        return {
            'success': True,
            'exported_count': len(exported_files),
            'skipped_count': len(skipped_files),
            'exported_files': exported_files,
            'skipped_files': skipped_files,
            'folder': str(get_export_folder())
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
