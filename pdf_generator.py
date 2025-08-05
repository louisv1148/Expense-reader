from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage
import os
from datetime import datetime
from database import ExpenseDatabase

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
        
        # Individual receipt pages with images
        if include_images:
            story.append(PageBreak())
            story = self._add_receipt_details(story, receipts)
        
        # Build PDF
        doc.build(story)
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
        data = [["Date", "Restaurant/Venue", "Amount", "Receipt #"]]
        
        # Add receipt data
        for receipt in receipts:
            # Calculate USD amount
            amount_usd = receipt.get('amount_mxn')  # This field stores USD amount
            if not amount_usd and receipt.get('total_amount') and receipt.get('fx_rate'):
                markup = receipt.get('markup_percent', 2.5)
                usd_base = receipt['total_amount'] / receipt['fx_rate']
                amount_usd = usd_base * (1 + markup / 100)
            
            # Create paragraph for filename to handle long names
            filename_para = Paragraph(receipt['filename'] or 'N/A', self.normal_style)
            
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
    
    def _resize_image_for_pdf(self, image_path, max_width=5*inch, max_height=6*inch):
        """Resize image to fit in PDF while maintaining aspect ratio"""
        
        # Open image to get dimensions
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
        img = Image(image_path, width=new_width, height=new_height)
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