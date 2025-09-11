import os
import openai
import pytesseract
from PIL import Image
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
import PyPDF2

# Load environment variables
load_dotenv()

class ExpenseReader:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Set Tesseract path if specified
        tesseract_path = os.getenv('TESSERACT_PATH')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
            return None
    
    def extract_text_from_image(self, image_path):
        """Extract text from receipt image using OCR"""
        try:
            image = Image.open(image_path)
            # Convert to RGB if needed (handles EXIF issues)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            # Auto-rotate based on EXIF orientation
            try:
                from PIL import ImageOps
                image = ImageOps.exif_transpose(image)
            except:
                pass
            ocr_text = pytesseract.image_to_string(image, lang='eng')
            return ocr_text
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return None
    
    def extract_text_from_file(self, file_path):
        """Extract text from either image or PDF file"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        else:
            # Assume it's an image file
            return self.extract_text_from_image(file_path)
    
    def extract_receipt_data(self, ocr_text, use_training_examples=True):
        """Use OpenAI to extract structured data from OCR text with few-shot learning"""
        
        # Build prompt with training examples from previous corrections
        prompt = """You are an AI assistant that extracts structured information from receipts.

Here are some examples of correctly extracted data from similar receipts:

"""
        
        # Add training examples if available and requested
        if use_training_examples:
            try:
                from app.database import ExpenseDatabase
                db = ExpenseDatabase()
                examples = db.get_training_examples(limit=3)
                
                for i, example in enumerate(examples, 1):
                    prompt += f"""Example {i}:
OCR Text: {example['ocr_text'][:200]}...
Correct extraction:
{{"restaurant_name": "{example['restaurant_name']}", "date": "{example['date']}", "total_amount": {example['total_amount']}}}

"""
            except Exception as e:
                # If database isn't available, continue without examples
                pass
        
        prompt += f"""
Now extract data from this new receipt:

---
{ocr_text}
---

Please extract and return the information in JSON format with these exact keys:
- "restaurant_name": The name of the restaurant/venue (be consistent with naming)
- "date": The date of purchase (format: YYYY-MM-DD)
- "total_amount": The total amount paid including tip (just the number, no currency symbol)

Learn from the examples above to be more accurate. If any information is not found, use null for that field.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            # Parse the JSON response
            result_text = response.choices[0].message.content
            # Extract JSON from the response (in case it's wrapped in markdown)
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            return json.loads(result_text)
            
        except Exception as e:
            print(f"Error extracting data with OpenAI: {e}")
            return None
    
    def process_single_receipt(self, file_path):
        """Process a single receipt file (image or PDF) and return extracted data"""
        print(f"Processing: {file_path}")
        
        # Extract text using OCR or PDF extraction
        extracted_text = self.extract_text_from_file(file_path)
        if not extracted_text:
            return None
        
        print("Extracted Text:")
        print("-" * 50)
        print(extracted_text)
        print("-" * 50)
        
        # Extract structured data using OpenAI
        receipt_data = self.extract_receipt_data(extracted_text)
        if receipt_data:
            receipt_data['file_name'] = os.path.basename(file_path)
            receipt_data['processed_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return receipt_data
    
    def process_receipts_folder(self, folder_path):
        """Process all receipt files (images and PDFs) in a folder"""
        results = []
        supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
        
        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in supported_extensions):
                file_path = os.path.join(folder_path, filename)
                receipt_data = self.process_single_receipt(file_path)
                if receipt_data:
                    results.append(receipt_data)
        
        return results
    
    def save_to_csv(self, results, output_file="expense_report.csv"):
        """Save results to CSV file"""
        if not results:
            print("No data to save")
            return
        
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")

def main():
    # Example usage
    reader = ExpenseReader()
    
    # Process a single image
    image_path = input("Enter the path to your receipt image: ")
    if os.path.exists(image_path):
        result = reader.process_single_receipt(image_path)
        if result:
            print("\nExtracted Data:")
            print(json.dumps(result, indent=2))
    else:
        print("Image file not found")

if __name__ == "__main__":
    main()