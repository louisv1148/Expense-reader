#!/usr/bin/env python3
import os
import sys
from expense_reader import ExpenseReader

def main():
    if len(sys.argv) != 2:
        print("Usage: python batch_process.py <folder_path>")
        print("Example: python batch_process.py ./receipts")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a directory")
        sys.exit(1)
    
    print(f"Processing all receipt images in: {folder_path}")
    
    # Initialize the expense reader
    reader = ExpenseReader()
    
    # Process all receipts in the folder
    results = reader.process_receipts_folder(folder_path)
    
    if not results:
        print("No receipts were successfully processed.")
        return
    
    print(f"\nSuccessfully processed {len(results)} receipts:")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.get('image_file', 'Unknown')}")
        print(f"   Restaurant: {result.get('restaurant_name', 'N/A')}")
        print(f"   Date: {result.get('date', 'N/A')}")
        print(f"   Amount: ${result.get('total_amount', 'N/A')}")
        print()
    
    # Save to CSV
    output_file = "expense_report.csv"
    reader.save_to_csv(results, output_file)
    
    print(f"Results exported to: {output_file}")

if __name__ == "__main__":
    main()