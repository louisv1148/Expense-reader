# Expense Receipt Reader

Automatically extract expense data from receipt images using OCR and AI, with a web interface for manual review and corrections.

## Features

### Version 1.0 (Command Line)
- OCR text extraction from receipt images using Tesseract
- AI-powered data extraction using OpenAI GPT-4
- Batch processing for multiple receipts
- CSV export for expense reports

### Version 2.0 (Web Interface) 
- **Web-based dashboard** for reviewing all receipts
- **Manual editing interface** to correct extracted data
- **Image preview** alongside OCR text
- **Database storage** for processed receipts
- **CSV export** from web interface
- **Upload interface** for new receipts

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

### Web Interface (Version 2.0)

1. **Process existing receipts into database:**
   ```bash
   python web_batch_process.py receipts/
   ```

2. **Start the web interface:**
   ```bash
   python app.py
   ```

3. **Open in browser:** http://localhost:5000

4. **Web Interface Features:**
   - **Dashboard:** View all processed receipts
   - **Upload:** Add new receipt images 
   - **Review:** Edit extracted data with image preview
   - **Export:** Download CSV of all receipts

### Command Line (Version 1.0)

#### Single Receipt
```bash
python expense_reader.py
```

#### Multiple Receipts  
```bash
python batch_process.py receipts/
```

## Extracted Data
- Restaurant/venue name
- Date of purchase  
- Total amount (including tip)
- Source image filename
- Processing timestamp
- Review status

## Supported Image Formats
- JPG/JPEG
- PNG
- BMP
- TIFF
- GIF

## File Structure
```
├── app.py                 # Flask web application
├── expense_reader.py      # Core OCR and AI extraction
├── database.py           # SQLite database management
├── batch_process.py      # Command-line batch processing
├── web_batch_process.py  # Batch processing for web interface
├── templates/            # HTML templates
├── static/              # CSS and JS files
├── uploads/             # Uploaded receipt images
└── receipts/            # Sample receipts folder
```