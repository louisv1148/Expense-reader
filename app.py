from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
from expense_reader import ExpenseReader
from database import ExpenseDatabase
import base64
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize components
reader = ExpenseReader()
db = ExpenseDatabase()

@app.route('/')
def index():
    """Main dashboard showing all receipts"""
    receipts = db.get_all_receipts()
    return render_template('index.html', receipts=receipts)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload and process receipt images"""
    if request.method == 'POST':
        if 'files[]' not in request.files:
            flash('No files selected')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        processed_count = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and allowed_file(file.filename):
                # Save uploaded file
                filename = file.filename
                upload_path = os.path.join('uploads', filename)
                os.makedirs('uploads', exist_ok=True)
                file.save(upload_path)
                
                # Process with OCR
                ocr_text = reader.extract_text_from_image(upload_path)
                if ocr_text:
                    # Extract data with AI
                    receipt_data = reader.extract_receipt_data(ocr_text)
                    
                    # Save to database
                    db.add_receipt(
                        filename=filename,
                        file_path=upload_path,
                        ocr_text=ocr_text,
                        restaurant_name=receipt_data.get('restaurant_name') if receipt_data else None,
                        date=receipt_data.get('date') if receipt_data else None,
                        total_amount=receipt_data.get('total_amount') if receipt_data else None
                    )
                    processed_count += 1
        
        flash(f'Successfully processed {processed_count} receipts')
        return redirect(url_for('index'))
    
    return render_template('upload.html')

@app.route('/review/<int:receipt_id>')
def review(receipt_id):
    """Review and edit a specific receipt"""
    receipt = db.get_receipt(receipt_id)
    if not receipt:
        flash('Receipt not found')
        return redirect(url_for('index'))
    
    # Convert image to base64 for display
    image_data = None
    if os.path.exists(receipt['file_path']):
        with open(receipt['file_path'], 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()
    
    return render_template('review.html', receipt=receipt, image_data=image_data)

@app.route('/update/<int:receipt_id>', methods=['POST'])
def update_receipt(receipt_id):
    """Update receipt data after manual review"""
    restaurant_name = request.form.get('restaurant_name')
    date = request.form.get('date')
    total_amount = request.form.get('total_amount')
    
    # Convert amount to float if provided
    if total_amount:
        try:
            total_amount = float(total_amount)
        except ValueError:
            total_amount = None
    
    db.update_receipt(receipt_id, restaurant_name, date, total_amount)
    flash('Receipt updated successfully')
    
    return redirect(url_for('index'))

@app.route('/export')
def export():
    """Export all receipts to CSV"""
    df = db.export_to_csv()
    if df is None:
        flash('No receipts to export')
        return redirect(url_for('index'))
    
    # Save to temporary file
    csv_path = 'expense_report.csv'
    df.to_csv(csv_path, index=False)
    
    return send_file(csv_path, as_attachment=True, download_name='expense_report.csv')

@app.route('/delete/<int:receipt_id>', methods=['POST'])
def delete_receipt(receipt_id):
    """Delete a receipt"""
    receipt = db.get_receipt(receipt_id)
    if receipt:
        # Delete file if it exists
        if os.path.exists(receipt['file_path']):
            os.remove(receipt['file_path'])
        
        # Delete from database (we'll need to add this method)
        flash('Receipt deleted successfully')
    
    return redirect(url_for('index'))

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)