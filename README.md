# Expense Receipt Reader

Automatically extract expense data from receipt images using OCR and AI.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

## Usage

### Single Receipt
```bash
python expense_reader.py
```

### Multiple Receipts
1. Put receipt images in the `receipts/` folder
2. Run batch processing:
   ```bash
   python batch_process.py receipts
   ```

### Output
- Console output shows extracted data
- CSV file (`expense_report.csv`) contains all results

## Extracted Data
- Restaurant/venue name
- Date of purchase  
- Total amount (including tip)
- Source image filename
- Processing timestamp

## Supported Image Formats
- JPG/JPEG
- PNG
- BMP
- TIFF