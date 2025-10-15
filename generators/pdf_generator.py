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
import pypdfium2 as pdfium
import tempfile

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

        # Sort receipts alphabetically by display_filename
        receipts.sort(key=lambda r: (r.get('display_filename') or r['filename']).lower())

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

        # Add receipt data
        for receipt in receipts:
            # Calculate USD amount
            amount_usd = receipt.get('amount_mxn')  # This field stores USD amount
            if not amount_usd and receipt.get('total_amount') and receipt.get('fx_rate'):
                markup = receipt.get('markup_percent', 2.5)
                usd_base = receipt['total_amount'] / receipt['fx_rate']
                amount_usd = usd_base * (1 + markup / 100)

            # Use display_filename from database (set when receipt was reviewed)
            display_filename = receipt.get('display_filename') or receipt['filename']

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

            # Add receipt image(s) if file exists
            if os.path.exists(receipt['file_path']):
                try:
                    # Resize image(s) to fit page - returns list (multiple for PDFs, single for images)
                    images = self._resize_image_for_pdf(receipt['file_path'])

                    if images:
                        # Add all images/pages
                        for page_num, img in enumerate(images):
                            if page_num > 0:
                                # Add page label for multi-page PDFs
                                story.append(Spacer(1, 10))
                                story.append(Paragraph(f"Page {page_num + 1}", self.normal_style))
                                story.append(Spacer(1, 10))
                            story.append(img)

                            # Add page break between pages of same receipt (except last page)
                            if page_num < len(images) - 1:
                                story.append(PageBreak())
                    else:
                        story.append(Paragraph("[Image could not be loaded]", self.normal_style))
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

        # Track unique images by file_path to avoid duplicates from divided expenses
        # (Multiple expense entries may share the same receipt image)
        seen_file_paths = set()
        unique_receipts = []

        for receipt in receipts:
            file_path = receipt['file_path']

            # Only add if we haven't seen this file path before AND the file exists
            if (file_path and
                file_path not in seen_file_paths and
                os.path.exists(file_path)):
                seen_file_paths.add(file_path)
                unique_receipts.append(receipt)
        
        for i, receipt in enumerate(unique_receipts, 1):
            # Use display_filename from database (set when receipt was reviewed)
            display_filename = receipt.get('display_filename') or receipt['filename']

            # Receipt header - use display filename as title
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

            # Add receipt image(s) if file exists
            if os.path.exists(receipt['file_path']):
                try:
                    # Resize image(s) to fit page - returns list (multiple for PDFs, single for images)
                    images = self._resize_image_for_pdf(receipt['file_path'])

                    if images:
                        # Add all images/pages
                        for page_num, img in enumerate(images):
                            if page_num > 0:
                                # Add page label for multi-page PDFs
                                story.append(Spacer(1, 10))
                                story.append(Paragraph(f"Page {page_num + 1}", self.normal_style))
                                story.append(Spacer(1, 10))
                            story.append(img)

                            # Add page break between pages of same receipt (except last page)
                            if page_num < len(images) - 1:
                                story.append(PageBreak())
                    else:
                        story.append(Paragraph("[Image could not be loaded]", self.normal_style))
                except Exception as e:
                    story.append(Paragraph(f"[Image could not be loaded: {str(e)}]", self.normal_style))
            else:
                story.append(Paragraph("[Receipt image not found]", self.normal_style))

            # Add page break between receipts (except for the last one)
            if i < len(unique_receipts):
                story.append(PageBreak())
        
        return story
    
    def _convert_pdf_to_images(self, pdf_path):
        """Convert all pages of a PDF to PIL Images"""
        pil_images = []
        temp_files = []

        try:
            pdf = pdfium.PdfDocument(pdf_path)

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                # Render at 2x resolution for better quality
                bitmap = page.render(scale=2.0)
                pil_img = bitmap.to_pil()
                pil_images.append(pil_img)

        except Exception as e:
            print(f"Error converting PDF {pdf_path}: {e}")
            return []

        return pil_images

    def _is_pdf_file(self, file_path):
        """Check if file is actually a PDF by reading its header"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except:
            return False

    def _resize_image_for_pdf(self, image_path, max_width=5*inch, max_height=6*inch):
        """Resize image to fit in PDF while maintaining aspect ratio and fixing orientation
        Returns a list of ReportLab Image objects (list will have multiple items for multi-page PDFs)"""

        images_to_process = []

        # Check if this is a PDF file (by content, not just extension)
        if self._is_pdf_file(image_path):
            # Convert PDF pages to PIL images
            pil_images = self._convert_pdf_to_images(image_path)
            if not pil_images:
                return []
            images_to_process = [(pil_img, True) for pil_img in pil_images]  # (image, needs_temp_file)
        else:
            # Handle regular image files
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

                    if needs_rotation:
                        images_to_process = [(pil_img.copy(), True)]
                    else:
                        images_to_process = [(image_path, False)]  # Use original file path
            except Exception as e:
                print(f"Error opening image {image_path}: {e}")
                return []

        # Process all images (single image or multiple PDF pages)
        result_images = []

        for img_data, needs_temp_file in images_to_process:
            try:
                # Get image dimensions
                if needs_temp_file:
                    # It's a PIL Image object
                    pil_img = img_data
                    orig_width, orig_height = pil_img.size

                    # Save to temp file
                    temp_path = tempfile.mktemp(suffix='.jpg')
                    pil_img.save(temp_path, 'JPEG', quality=85)
                    use_temp_file = True
                else:
                    # It's a file path
                    with PILImage.open(img_data) as pil_img:
                        orig_width, orig_height = pil_img.size
                    temp_path = img_data
                    use_temp_file = False

                # Calculate scaling factor
                width_ratio = max_width / orig_width
                height_ratio = max_height / orig_height
                scale_factor = min(width_ratio, height_ratio)

                # Calculate new dimensions
                new_width = orig_width * scale_factor
                new_height = orig_height * scale_factor

                # Create ReportLab Image object
                img = Image(temp_path, width=new_width, height=new_height)
                result_images.append(img)

                # Store temp file path for cleanup after PDF is built
                if use_temp_file:
                    if not hasattr(self, '_temp_files'):
                        self._temp_files = []
                    self._temp_files.append(temp_path)

            except Exception as e:
                print(f"Error processing image: {e}")
                continue

        return result_images
    
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