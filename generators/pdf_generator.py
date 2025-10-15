from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage
import os
from datetime import datetime
from app.database import ExpenseDatabase

class ExpensePDFGenerator:
    def __init__(self):
        self.db = ExpenseDatabase()
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def generate_expense_report(self, output_filename="expense_report.pdf", include_images=True):
        """Generate a complete expense report PDF with receipt images"""
        
        # Get all reviewed receipts
        receipts = [r for r in self.db.get_all_receipts() if r['reviewed']]
        
        if not receipts:
            raise ValueError("No reviewed receipts found. Please review receipts in the web interface first.")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Summary table (removed title page)
        story = self._add_summary_table(story, receipts)
        
        # Individual receipt pages with images - show each unique image only once
        if include_images:
            story.append(PageBreak())
            story = self._add_unique_receipt_images(story, receipts)
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary files
        if hasattr(self, '_temp_files'):
            for temp_file in self._temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass  # Don't fail if cleanup doesn't work
            del self._temp_files
        
        return output_filename
    
    def _add_title_page(self, story, receipts):
        """Add title page with report summary"""
        
        # Title
        story.append(Paragraph("EXPENSE REIMBURSEMENT REQUEST", self.title_style))
        story.append(Spacer(1, 20))
        
        # Report info
        total_amount = sum(r['total_amount'] or 0 for r in receipts)
        date_range = self._get_date_range(receipts)
        
        info_data = [
            ["Report Period:", date_range],
            ["Number of Receipts:", str(len(receipts))],
            ["Total Amount:", f"${total_amount:.2f}"],
            ["Generated Date:", datetime.now().strftime("%B %d, %Y")],
            ["Generated Time:", datetime.now().strftime("%I:%M %p")]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        # Submission info
        story.append(Paragraph("EMPLOYEE INFORMATION", self.header_style))
        
        employee_data = [
            ["Employee Name:", "_" * 40],
            ["Employee ID:", "_" * 40],
            ["Department:", "_" * 40],  
            ["Manager Approval:", "_" * 40],
            ["Date:", "_" * 40]
        ]
        
        employee_table = Table(employee_data, colWidths=[2*inch, 4*inch])
        employee_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        
        story.append(employee_table)
        story.append(PageBreak())
        
        return story
    
    def _add_summary_table(self, story, receipts):
        """Add summary table of all expenses"""

        story.append(Paragraph("EXPENSE SUMMARY", self.header_style))
        story.append(Spacer(1, 12))

        # Table headers
        data = [["Date", "Restaurant/Venue", "Amount", "Receipt Name"]]

        # Track duplicate filenames for sequential numbering
        from core.file_utils import format_receipt_filename
        seen_filenames = {}

        # Add receipt data
        for receipt in receipts:
            # Calculate USD amount
            amount_usd = receipt.get('amount_mxn')  # This field stores USD amount
            if not amount_usd and receipt.get('total_amount') and receipt.get('fx_rate'):
                markup = receipt.get('markup_percent', 2.5)
                usd_base = receipt['total_amount'] / receipt['fx_rate']
                amount_usd = usd_base * (1 + markup / 100)

            # Generate formatted filename with duplicate handling
            display_filename = receipt['filename']
            if receipt.get('date') and receipt.get('restaurant_name'):
                formatted_name = format_receipt_filename(receipt['date'], receipt['restaurant_name'])
                if formatted_name:
                    if formatted_name in seen_filenames:
                        seen_filenames[formatted_name] += 1
                        display_filename = f"{formatted_name}_{seen_filenames[formatted_name]}.pdf"
                    else:
                        seen_filenames[formatted_name] = 1
                        display_filename = f"{formatted_name}.pdf"

            # Create paragraph for filename to handle long names
            filename_para = Paragraph(display_filename or 'N/A', self.normal_style)

            data.append([
                receipt['date'] or 'N/A',
                receipt['restaurant_name'] or 'N/A',
                f"${amount_usd:.2f}" if amount_usd else 'N/A',
                filename_para
            ])
        
        # Add total row
        total_amount_usd = 0
        for receipt in receipts:
            amount_usd = receipt.get('amount_mxn')
            if not amount_usd and receipt.get('total_amount') and receipt.get('fx_rate'):
                markup = receipt.get('markup_percent', 2.5)
                usd_base = receipt['total_amount'] / receipt['fx_rate']
                amount_usd = usd_base * (1 + markup / 100)
            total_amount_usd += amount_usd or 0
        
        data.append(['', '', '', ''])  # Empty row
        data.append(['', 'TOTAL:', f"${total_amount_usd:.2f}", ''])
        
        # Create table with wider columns to prevent text overlap
        table = Table(data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 2.2*inch])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            
            # Data rows
            ('FONTNAME', (0,1), (-1,-3), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-3), 10),
            ('ROWBACKGROUNDS', (0,1), (-1,-3), [colors.beige, colors.white]),
            
            # Total row
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 12),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('LINEABOVE', (0,-1), (-1,-1), 2, colors.black),
            
            # General formatting
            ('GRID', (0,0), (-1,-3), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (1,1), (1,-3), 6),  # Restaurant names left-aligned
            ('ALIGN', (1,1), (1,-3), 'LEFT'),
            ('WORDWRAP', (0,0), (-1,-1), True),  # Enable word wrapping for all cells
        ]))
        
        story.append(table)
        return story
    
    def _add_receipt_details(self, story, receipts):
        """Add individual receipt pages with images"""
        
        story.append(Paragraph("RECEIPT DETAILS", self.title_style))
        story.append(Spacer(1, 20))
        
        for i, receipt in enumerate(receipts, 1):
            # Receipt header
            story.append(Paragraph(f"Receipt #{i:03d}", self.header_style))
            
            # Receipt info table
            # Calculate USD amount
            amount_usd = receipt.get('amount_mxn')  # This field stores USD amount
            if not amount_usd and receipt.get('total_amount') and receipt.get('fx_rate'):
                markup = receipt.get('markup_percent', 2.5)
                usd_base = receipt['total_amount'] / receipt['fx_rate']
                amount_usd = usd_base * (1 + markup / 100)
            
            info_data = [
                ["Restaurant:", receipt['restaurant_name'] or 'N/A'],
                ["Date:", receipt['date'] or 'N/A'],
                ["Amount:", f"${amount_usd:.2f}" if amount_usd else 'N/A'],
                ["Image File:", receipt['filename'] or 'N/A']
            ]
            
            info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 15))
            
            # Add receipt image if it exists
            if os.path.exists(receipt['file_path']):
                try:
                    # Resize image to fit page
                    img = self._resize_image_for_pdf(receipt['file_path'])
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"[Image could not be loaded: {str(e)}]", self.normal_style))
            else:
                story.append(Paragraph("[Receipt image not found]", self.normal_style))
            
            # Add page break between receipts (except for the last one)
            if i < len(receipts):
                story.append(PageBreak())
        
        return story
    
    def _add_unique_receipt_images(self, story, receipts):
        """Add individual receipt pages with images - show each unique image only once"""
        
        story.append(Paragraph("RECEIPT IMAGES", self.title_style))
        story.append(Spacer(1, 20))
        
        # Track unique images by restaurant name + date to avoid duplicates from divided expenses
        # Also check file existence
        seen_receipts = set()
        unique_receipts = []
        
        for receipt in receipts:
            # Create a unique key based on restaurant name and date
            unique_key = f"{receipt.get('restaurant_name', 'Unknown')}_{receipt.get('date', 'Unknown')}"
            file_path = receipt['file_path']
            
            # Only add if we haven't seen this receipt before AND the file exists
            if (unique_key not in seen_receipts and 
                file_path and 
                os.path.exists(file_path)):
                seen_receipts.add(unique_key)
                unique_receipts.append(receipt)
        
        for i, receipt in enumerate(unique_receipts, 1):
            # Generate formatted filename
            from core.file_utils import format_receipt_filename
            display_filename = receipt['filename']
            if receipt.get('date') and receipt.get('restaurant_name'):
                formatted_name = format_receipt_filename(receipt['date'], receipt['restaurant_name'])
                if formatted_name:
                    display_filename = f"{formatted_name}.pdf"

            # Receipt header - use formatted filename as title
            story.append(Paragraph(display_filename, self.header_style))

            # Receipt info table - show basic info (Image File line removed as it's redundant)
            info_data = [
                ["Restaurant:", receipt['restaurant_name'] or 'N/A'],
                ["Date:", receipt['date'] or 'N/A']
            ]
            
            info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 15))
            
            # Add receipt image if it exists
            if os.path.exists(receipt['file_path']):
                try:
                    # Resize image to fit page
                    img = self._resize_image_for_pdf(receipt['file_path'])
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"[Image could not be loaded: {str(e)}]", self.normal_style))
            else:
                story.append(Paragraph("[Receipt image not found]", self.normal_style))
            
            # Add page break between receipts (except for the last one)
            if i < len(unique_receipts):
                story.append(PageBreak())
        
        return story
    
    def _resize_image_for_pdf(self, image_path, max_width=5*inch, max_height=6*inch):
        """Resize image to fit in PDF while maintaining aspect ratio and fixing orientation"""
        
        # Open image and fix orientation if needed
        try:
            with PILImage.open(image_path) as pil_img:
                # Check if image needs rotation based on EXIF orientation
                needs_rotation = False
                try:
                    exif = pil_img._getexif()
                    if exif is not None:
                        orientation = exif.get(274)  # 274 is the EXIF orientation tag
                        if orientation and orientation > 1:
                            needs_rotation = True
                            if orientation == 3:
                                pil_img = pil_img.rotate(180, expand=True)
                            elif orientation == 6:
                                pil_img = pil_img.rotate(270, expand=True)
                            elif orientation == 8:
                                pil_img = pil_img.rotate(90, expand=True)
                except:
                    # If EXIF processing fails, continue with original image
                    pass
                
                # Get dimensions after potential rotation
                orig_width, orig_height = pil_img.size
                
                # If rotation was needed, save corrected image
                if needs_rotation:
                    import tempfile
                    temp_path = tempfile.mktemp(suffix='.jpg')
                    pil_img.save(temp_path, 'JPEG', quality=85)
                    use_temp_file = True
                else:
                    temp_path = image_path
                    use_temp_file = False
        except Exception as e:
            # If image processing fails, use original
            temp_path = image_path
            use_temp_file = False
            with PILImage.open(image_path) as pil_img:
                orig_width, orig_height = pil_img.size
        
        # Calculate scaling factor
        width_ratio = max_width / orig_width
        height_ratio = max_height / orig_height
        scale_factor = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = orig_width * scale_factor
        new_height = orig_height * scale_factor
        
        # Create ReportLab Image object
        img = Image(temp_path, width=new_width, height=new_height)
        
        # Store temp file path for cleanup after PDF is built
        if use_temp_file and hasattr(self, '_temp_files'):
            self._temp_files.append(temp_path)
        elif use_temp_file:
            self._temp_files = [temp_path]
        
        return img
    
    def _get_date_range(self, receipts):
        """Get date range from receipts"""
        dates = [r['date'] for r in receipts if r['date']]
        if not dates:
            return "N/A"
        
        dates.sort()
        if len(dates) == 1:
            return dates[0]
        else:
            return f"{dates[0]} to {dates[-1]}"

def main():
    """Test PDF generation"""
    generator = ExpensePDFGenerator()
    try:
        filename = generator.generate_expense_report("expense_report_with_receipts.pdf")
        print(f"PDF generated successfully: {filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")

if __name__ == "__main__":
    main()