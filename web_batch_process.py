#!/usr/bin/env python3
import os
import sys
from expense_reader import ExpenseReader
from database import ExpenseDatabase

def process_receipts_to_database(folder_path):
    """Process receipts and store in database for web interface"""
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist")
        return
    
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a directory")
        return
    
    print(f"Processing all receipt images in: {folder_path}")
    
    # Initialize components
    reader = ExpenseReader()
    db = ExpenseDatabase()
    
    # Get list of image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    image_files = []
    
    for filename in os.listdir(folder_path):
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            image_files.append(filename)
    
    if not image_files:
        print("No image files found in the specified folder")
        return
    
    processed_count = 0
    
    for filename in image_files:
        image_path = os.path.join(folder_path, filename)
        print(f"Processing: {filename}")
        
        # Extract text using OCR
        ocr_text = reader.extract_text_from_image(image_path)
        if not ocr_text:
            print(f"  Failed to extract text from {filename}")
            continue
        
        # Extract structured data using OpenAI
        receipt_data = reader.extract_receipt_data(ocr_text)
        
        # Save to database
        receipt_id = db.add_receipt(
            filename=filename,
            file_path=image_path,
            ocr_text=ocr_text,
            restaurant_name=receipt_data.get('restaurant_name') if receipt_data else None,
            date=receipt_data.get('date') if receipt_data else None,
            total_amount=receipt_data.get('total_amount') if receipt_data else None
        )
        
        print(f"  Saved to database with ID: {receipt_id}")
        processed_count += 1
    
    print(f"\nSuccessfully processed {processed_count} receipts")
    print("You can now review and edit them using the web interface:")
    print("Run: python app.py")
    print("Then open: http://localhost:5000")

def main():
    if len(sys.argv) != 2:
        print("Usage: python web_batch_process.py <folder_path>")
        print("Example: python web_batch_process.py ./receipts")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    process_receipts_to_database(folder_path)

if __name__ == "__main__":
    main()