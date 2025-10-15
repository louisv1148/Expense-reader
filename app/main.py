from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
from core.expense_reader import ExpenseReader
from app.database import ExpenseDatabase
from core.file_utils import format_receipt_filename, get_export_folder, get_unique_filename, export_organized_receipts
import base64
from io import BytesIO
import pandas as pd
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize components
reader = ExpenseReader()
db = ExpenseDatabase()

@app.route('/')
def index():
    """Main dashboard showing all receipts"""
    receipts = db.get_all_receipts()

    # Add formatted filename for display with duplicate handling
    # Track which filenames we've seen to add _2, _3, etc.
    seen_filenames = {}

    for receipt in receipts:
        if receipt.get('reviewed') and receipt.get('date') and receipt.get('restaurant_name'):
            formatted_name = format_receipt_filename(receipt['date'], receipt['restaurant_name'])

            if formatted_name:
                # Check if we've seen this filename before
                if formatted_name in seen_filenames:
                    seen_filenames[formatted_name] += 1
                    display_name = f"{formatted_name}_{seen_filenames[formatted_name]}.pdf"
                else:
                    seen_filenames[formatted_name] = 1
                    display_name = f"{formatted_name}.pdf"

                receipt['display_filename'] = display_name
            else:
                receipt['display_filename'] = receipt['filename']
        else:
            receipt['display_filename'] = receipt['filename']

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
                upload_path = os.path.join('data/uploads', filename)
                os.makedirs('data/uploads', exist_ok=True)
                file.save(upload_path)
                
                # Process with OCR or PDF extraction
                extracted_text = reader.extract_text_from_file(upload_path)
                if extracted_text:
                    # Extract data with AI
                    receipt_data = reader.extract_receipt_data(extracted_text)
                    
                    # Save to database
                    db.add_receipt(
                        filename=filename,
                        file_path=upload_path,
                        ocr_text=extracted_text,
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
    
    # Handle file display based on type
    image_data = None
    is_pdf = False
    if os.path.exists(receipt['file_path']):
        file_extension = os.path.splitext(receipt['file_path'])[1].lower()
        if file_extension == '.pdf':
            is_pdf = True
            # For PDFs, we'll just provide the file path for download/viewing
        else:
            # For images, convert to base64 for display
            with open(receipt['file_path'], 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
    
    return render_template('review.html', receipt=receipt, image_data=image_data, is_pdf=is_pdf)

@app.route('/view-pdf/<int:receipt_id>')
def view_pdf(receipt_id):
    """Serve PDF file for viewing"""
    receipt = db.get_receipt(receipt_id)
    if not receipt or not os.path.exists(receipt['file_path']):
        flash('Receipt file not found')
        return redirect(url_for('index'))
    
    file_extension = os.path.splitext(receipt['file_path'])[1].lower()
    if file_extension != '.pdf':
        flash('File is not a PDF')
        return redirect(url_for('review', receipt_id=receipt_id))
    
    return send_file(receipt['file_path'], as_attachment=False, mimetype='application/pdf')

@app.route('/update/<int:receipt_id>', methods=['POST'])
def update_receipt(receipt_id):
    """Update receipt data after manual review"""
    restaurant_name = request.form.get('restaurant_name')
    date = request.form.get('date')
    total_amount = request.form.get('total_amount')
    cuenta_contable = request.form.get('cuenta_contable')
    cc = request.form.get('cc')
    fx_rate = request.form.get('fx_rate')
    markup_percent = request.form.get('markup_percent')
    reembolso = request.form.get('reembolso')
    detalle = request.form.get('detalle')
    
    # Convert numeric fields
    try:
        total_amount = float(total_amount) if total_amount else None
        fx_rate = float(fx_rate) if fx_rate else None
        markup_percent = float(markup_percent) if markup_percent else None
    except ValueError:
        flash('Invalid numeric values provided')
        return redirect(url_for('review', receipt_id=receipt_id))
    
    # Update receipt with all new fields
    db.update_receipt(receipt_id, restaurant_name, date, total_amount,
                     cuenta_contable, cc, fx_rate, markup_percent, reembolso, detalle)

    # Generate intended filename for export (yyyy_mm_RestaurantName)
    if date and restaurant_name:
        intended_filename = format_receipt_filename(date, restaurant_name)
        if intended_filename:
            flash(f'Receipt updated successfully. Will export as: {intended_filename}.pdf')
        else:
            flash('Receipt updated successfully')
    else:
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

@app.route('/export/pdf')
def export_pdf():
    """Export expense report as PDF with receipt images"""
    try:
        from generators.pdf_generator import ExpensePDFGenerator
        from datetime import datetime

        # Get current month for folder organization
        current_date = datetime.now()
        year_month = f"{current_date.year}_{current_date.month:02d}"

        # Get export folder
        export_folder = get_export_folder(year_month)
        output_filename = 'expense_report_approval.pdf'
        output_path = export_folder / output_filename

        # Generate PDF
        generator = ExpensePDFGenerator()
        pdf_filename = generator.generate_expense_report(str(output_path), include_images=True)

        # Send file for download
        response = send_file(pdf_filename, as_attachment=True, download_name=output_filename)

        flash(f'✅ PDF report saved to: {export_folder}')
        return response

    except ValueError as e:
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}')
        return redirect(url_for('index'))

@app.route('/export/pdf-summary')
def export_pdf_summary():
    """Export expense report as PDF summary only (no images)"""
    try:
        from generators.pdf_generator import ExpensePDFGenerator
        from datetime import datetime

        # Get current month for folder organization
        current_date = datetime.now()
        year_month = f"{current_date.year}_{current_date.month:02d}"

        # Get export folder
        export_folder = get_export_folder(year_month)
        output_filename = 'expense_summary.pdf'
        output_path = export_folder / output_filename

        # Generate PDF
        generator = ExpensePDFGenerator()
        pdf_filename = generator.generate_expense_report(str(output_path), include_images=False)

        # Send file for download
        response = send_file(pdf_filename, as_attachment=True, download_name=output_filename)

        flash(f'✅ PDF summary saved to: {export_folder}')
        return response

    except ValueError as e:
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}')
        return redirect(url_for('index'))

@app.route('/export/excel')
def export_excel():
    """Export expense report as Excel file matching company format"""
    try:
        from generators.excel_generator import ExcelExpenseGenerator
        from datetime import datetime

        # Create Excel filename with current month
        current_date = datetime.now()
        year_month = f"{current_date.year}_{current_date.month:02d}"
        output_filename = f"{year_month}_Gastos_MX.xlsx"

        # Get export folder
        export_folder = get_export_folder(year_month)
        output_path = export_folder / output_filename

        # Generate Excel
        generator = ExcelExpenseGenerator()
        excel_filename = generator.generate_monthly_report(str(output_path))

        # Send file for download
        response = send_file(excel_filename, as_attachment=True, download_name=output_filename)

        flash(f'✅ Excel report saved to: {export_folder}')
        return response

    except ValueError as e:
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error generating Excel: {str(e)}')
        return redirect(url_for('index'))

@app.route('/delete/<int:receipt_id>', methods=['POST'])
def delete_receipt_route(receipt_id):
    """Delete a receipt"""
    receipt = db.get_receipt(receipt_id)
    if receipt:
        # Delete file if it exists
        if os.path.exists(receipt['file_path']):
            os.remove(receipt['file_path'])
        
        # Delete from database
        if db.delete_receipt(receipt_id):
            flash('Receipt deleted successfully')
        else:
            flash('Error deleting receipt')
    else:
        flash('Receipt not found')
    
    return redirect(url_for('index'))

@app.route('/export/organized-files')
def export_organized_files():
    """Export all reviewed receipts as organized PDFs to Downloads/Expense_Receipts folder"""
    try:
        # Get all reviewed receipts
        receipts = db.get_all_receipts()
        reviewed_receipts = [r for r in receipts if r.get('reviewed')]

        if not reviewed_receipts:
            flash('No reviewed receipts to export. Please review receipts first.')
            return redirect(url_for('index'))

        # Export organized files
        result = export_organized_receipts(reviewed_receipts, db)

        if result['success']:
            exported = result['exported_count']
            skipped = result['skipped_count']
            folder = result['folder']

            message = f"✅ Exported {exported} receipt(s) to: {folder}"
            if skipped > 0:
                message += f"\n⚠️ Skipped {skipped} receipt(s)"

            flash(message)
        else:
            flash(f"❌ Error exporting files: {result.get('error', 'Unknown error')}")

    except Exception as e:
        flash(f'Error exporting organized files: {str(e)}')

    return redirect(url_for('index'))

@app.route('/api/reembolso-suggestions')
def get_reembolso_suggestions():
    """Get remembered reembolso suggestions for autocomplete"""
    try:
        suggestions = db.get_remembered_categories('reembolso')
        return jsonify(suggestions)
    except Exception as e:
        return jsonify([])

@app.route('/api/cost-centers')
def get_cost_centers():
    """Get all available cost centers"""
    try:
        cost_centers = db.get_remembered_categories('cc')
        # Add default cost centers if none exist
        if not cost_centers:
            cost_centers = ['Alternativos', 'Corporativo', 'Operaciones']
        return jsonify(cost_centers)
    except Exception as e:
        return jsonify(['Alternativos', 'Corporativo', 'Operaciones'])

@app.route('/api/add-cost-center', methods=['POST'])
def add_cost_center():
    """Add a new cost center"""
    data = request.get_json()
    cost_center_name = data.get('name')
    
    if not cost_center_name:
        return jsonify({'error': 'Cost center name required'}), 400
    
    db.add_cost_center(cost_center_name)
    return jsonify({'success': True})

@app.route('/divide-cc/<int:receipt_id>', methods=['POST'])
def divide_between_cost_centers(receipt_id):
    """Divide expense between multiple cost centers"""
    data = request.get_json()
    cost_centers = data.get('cost_centers', [])
    
    if len(cost_centers) < 2:
        return jsonify({'error': 'Need at least 2 cost centers to split'}), 400
    
    if db.duplicate_receipt_with_cc_split(receipt_id, cost_centers):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to split receipt'}), 500

@app.route('/api/update-fx-rate', methods=['POST'])
def update_fx_rate():
    """Update FX rate for all receipts"""
    data = request.get_json()
    fx_rate = data.get('fx_rate')
    markup_percent = data.get('markup_percent', 2.5)
    
    if not fx_rate or fx_rate <= 0:
        return jsonify({'error': 'Valid FX rate required'}), 400
    
    try:
        updated_count = db.update_all_fx_rates(fx_rate, markup_percent)
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated FX rate for {updated_count} receipts'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-all', methods=['POST'])
def clear_all_receipts():
    """Clear all receipts from the database"""
    try:
        deleted_records, deleted_files = db.clear_all_receipts()
        return jsonify({
            'success': True,
            'deleted_records': deleted_records,
            'deleted_files': deleted_files,
            'message': f'Cleared {deleted_records} receipts and {deleted_files} files'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)