import os
import json
import logging
import zipfile
from io import BytesIO
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import pytesseract
from docx import Document
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from app import db
from models import ProcessingJob, JobStatus, JobType
from utils import generate_unique_filename

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, job_id):
        self.job_id = job_id
        self.job = ProcessingJob.query.get(job_id)
        if not self.job:
            raise ValueError(f"Job {job_id} not found")
    
    def update_progress(self, progress, processed_files=None):
        """Update job progress in database"""
        self.job.progress = progress
        if processed_files is not None:
            self.job.processed_files = processed_files
        db.session.commit()
    
    def update_status(self, status, error_message=None):
        """Update job status in database"""
        self.job.status = status
        if error_message:
            self.job.error_message = error_message
        if status == JobStatus.PROCESSING:
            self.job.started_at = datetime.now()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.job.completed_at = datetime.now()
        db.session.commit()
    
    def process_job(self):
        """Main processing function that routes to specific processors"""
        try:
            self.update_status(JobStatus.PROCESSING)
            
            if self.job.job_type == JobType.MERGE:
                result = self.merge_pdfs()
            elif self.job.job_type == JobType.SPLIT:
                result = self.split_pdfs()
            elif self.job.job_type == JobType.COMPRESS:
                result = self.compress_pdfs()
            elif self.job.job_type == JobType.OCR:
                result = self.ocr_pdfs()
            elif self.job.job_type == JobType.CONVERT_WORD:
                result = self.convert_to_word()
            elif self.job.job_type == JobType.CONVERT_EXCEL:
                result = self.convert_to_excel()
            elif self.job.job_type == JobType.PROTECT:
                result = self.protect_pdfs()
            elif self.job.job_type == JobType.ROTATE:
                result = self.rotate_pdfs()
            elif self.job.job_type == JobType.WATERMARK:
                result = self.watermark_pdfs()
            elif self.job.job_type == JobType.UNLOCK:
                result = self.unlock_pdfs()
            elif self.job.job_type == JobType.EXTRACT_IMAGES:
                result = self.extract_images_pdfs()
            elif self.job.job_type in [JobType.REMOVE_PAGES, JobType.EXTRACT_PAGES, JobType.ORGANIZE]:
                result = self.organize_pdf_pages()
            elif self.job.job_type == JobType.REPAIR:
                result = self.repair_pdf()
            elif self.job.job_type in [JobType.JPG_TO_PDF, JobType.WORD_TO_PDF, JobType.POWERPOINT_TO_PDF, JobType.EXCEL_TO_PDF, JobType.HTML_TO_PDF]:
                result = self.convert_to_pdf()
            elif self.job.job_type in [JobType.PDF_TO_JPG, JobType.PDF_TO_POWERPOINT, JobType.PDF_TO_EXCEL, JobType.PDF_TO_PDFA]:
                result = self.convert_from_pdf()
            elif self.job.job_type == JobType.ADD_PAGE_NUMBERS:
                result = self.add_page_numbers()
            elif self.job.job_type == JobType.SIGN:
                result = self.sign_pdf()
            elif self.job.job_type == JobType.REDACT:
                result = self.redact_pdf()
            else:
                raise ValueError(f"Unknown job type: {self.job.job_type}")
            
            self.job.output_files = json.dumps(result)
            self.update_status(JobStatus.COMPLETED)
            self.update_progress(100, self.job.total_files)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing job {self.job_id}: {str(e)}")
            self.update_status(JobStatus.FAILED, str(e))
            raise
    
    def merge_pdfs(self):
        """Merge multiple PDF files into one"""
        input_files = json.loads(self.job.input_files)
        output_filename = generate_unique_filename("merged_document.pdf")
        output_path = os.path.join("processed", output_filename)
        
        writer = PdfWriter()
        
        for i, file_path in enumerate(input_files):
            try:
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    for page in reader.pages:
                        writer.add_page(page)
                
                progress = int((i + 1) / len(input_files) * 100)
                self.update_progress(progress, i + 1)
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        return [output_path]
    
    def split_pdfs(self):
        """Split PDF files into individual pages"""
        input_files = json.loads(self.job.input_files)
        output_files = []
        
        for file_idx, file_path in enumerate(input_files):
            try:
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    
                    for page_num, page in enumerate(reader.pages):
                        writer = PdfWriter()
                        writer.add_page(page)
                        
                        output_filename = generate_unique_filename(f"{base_name}_page_{page_num + 1}.pdf")
                        output_path = os.path.join("processed", output_filename)
                        
                        with open(output_path, 'wb') as output_file:
                            writer.write(output_file)
                        
                        output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
                
            except Exception as e:
                logger.error(f"Error splitting file {file_path}: {str(e)}")
                continue
        
        return output_files
    
    def compress_pdfs(self):
        """Compress PDF files with adjustable quality settings"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        quality = settings.get('compression_quality', 'medium')  # low, medium, high
        output_files = []
        
        # Quality settings mapping
        quality_settings = {
            'low': {'scale': 0.6, 'jpeg_quality': 30},
            'medium': {'scale': 0.8, 'jpeg_quality': 60}, 
            'high': {'scale': 1.0, 'jpeg_quality': 85}
        }
        
        current_settings = quality_settings.get(quality, quality_settings['medium'])
        
        for file_idx, file_path in enumerate(input_files):
            try:
                # Use PyMuPDF for better compression
                import fitz
                
                doc = fitz.open(file_path)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_compressed_{quality}.pdf")
                output_path = os.path.join("processed", output_filename)
                
                # Create a new document for the compressed version
                new_doc = fitz.open()
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Get page dimensions
                    rect = page.rect
                    
                    # Create pixmap with scaling for compression
                    scale = current_settings['scale']
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to JPEG bytes for compression
                    img_data = pix.tobytes("jpeg", jpg_quality=current_settings['jpeg_quality'])
                    
                    # Create new page and insert compressed image
                    new_page = new_doc.new_page(width=rect.width, height=rect.height)
                    new_page.insert_image(rect, stream=img_data)
                
                # Save with additional compression options
                new_doc.save(output_path, 
                           garbage=4,  # Remove unused objects
                           deflate=True,  # Use deflate compression
                           clean=True,  # Clean up structure
                           ascii=False)  # Keep binary format
                
                new_doc.close()
                doc.close()
                
                output_files.append(output_path)
                
            except ImportError:
                # Fallback to PyPDF2 for basic compression
                try:
                    with open(file_path, 'rb') as file:
                        reader = PdfReader(file)
                        writer = PdfWriter()
                        
                        for page in reader.pages:
                            # Remove annotations to reduce size
                            if '/Annots' in page:
                                del page['/Annots']
                            writer.add_page(page)
                        
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        output_filename = generate_unique_filename(f"{base_name}_compressed_{quality}.pdf")
                        output_path = os.path.join("processed", output_filename)
                        
                        with open(output_path, 'wb') as output_file:
                            writer.write(output_file)
                        
                        output_files.append(output_path)
                except Exception as e:
                    logger.error(f"Error compressing file {file_path}: {str(e)}")
                    continue
            except Exception as e:
                logger.error(f"Error compressing file {file_path}: {str(e)}")
                continue
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
                
            except Exception as e:
                logger.error(f"Error compressing file {file_path}: {str(e)}")
                continue
        
        return output_files
    
    def ocr_pdfs(self):
        """Extract text from PDF files using advanced OCR"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        language = settings.get('ocr_language', 'eng')  # Default to English
        output_format = settings.get('output_format', 'txt')  # txt, pdf, both
        output_files = []
        
        for file_idx, file_path in enumerate(input_files):
            try:
                import fitz  # PyMuPDF for better PDF to image conversion
                
                # Open PDF with PyMuPDF for better image extraction
                try:
                    pdf_document = fitz.open(file_path)
                    text_content = []
                    
                    for page_num in range(pdf_document.page_count):
                        page = pdf_document[page_num]
                        
                        # First try to extract text directly
                        text = page.get_text()
                        
                        if text.strip():
                            text_content.append(f"=== Page {page_num + 1} ===\n{text}")
                        else:
                            # Convert page to image for OCR
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                            img_data = pix.tobytes("png")
                            
                            # Convert to PIL Image for OCR
                            from PIL import Image
                            import io
                            
                            pil_image = Image.open(io.BytesIO(img_data))
                            
                            # Perform OCR
                            try:
                                ocr_text = pytesseract.image_to_string(pil_image, lang=language, 
                                                                     config='--psm 6 --oem 3')
                                if ocr_text.strip():
                                    text_content.append(f"=== Page {page_num + 1} (OCR) ===\n{ocr_text}")
                                else:
                                    text_content.append(f"=== Page {page_num + 1} ===\n[No text detected]")
                            except Exception as ocr_error:
                                logger.warning(f"OCR failed for page {page_num + 1}: {str(ocr_error)}")
                                text_content.append(f"=== Page {page_num + 1} ===\n[OCR processing failed]")
                    
                    pdf_document.close()
                    
                except ImportError:
                    # Fallback to PyPDF2 if PyMuPDF is not available
                    logger.warning("PyMuPDF not available, using basic text extraction")
                    with open(file_path, 'rb') as file:
                        reader = PdfReader(file)
                        text_content = []
                        
                        for page_num, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if text.strip():
                                text_content.append(f"=== Page {page_num + 1} ===\n{text}")
                            else:
                                text_content.append(f"=== Page {page_num + 1} ===\n[No extractable text found]")
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Save as text file
                if output_format in ['txt', 'both']:
                    txt_filename = generate_unique_filename(f"{base_name}_ocr.txt")
                    txt_output_path = os.path.join("processed", txt_filename)
                    
                    with open(txt_output_path, 'w', encoding='utf-8') as output_file:
                        output_file.write('\n\n'.join(text_content))
                    
                    output_files.append(txt_output_path)
                
                # Save as searchable PDF
                if output_format in ['pdf', 'both']:
                    pdf_filename = generate_unique_filename(f"{base_name}_searchable.pdf")
                    pdf_output_path = os.path.join("processed", pdf_filename)
                    
                    # Create a new PDF with the extracted text
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    
                    doc = SimpleDocTemplate(pdf_output_path, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    for content in text_content:
                        para = Paragraph(content.replace('\n', '<br/>'), styles['Normal'])
                        story.append(para)
                        story.append(Spacer(1, 12))
                    
                    doc.build(story)
                    output_files.append(pdf_output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
                
            except Exception as e:
                logger.error(f"Error processing OCR for file {file_path}: {str(e)}")
                continue
        
        return output_files
    
    def convert_to_word(self):
        """Convert PDF files to Word documents"""
        input_files = json.loads(self.job.input_files)
        output_files = []
        
        for file_idx, file_path in enumerate(input_files):
            try:
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    doc = Document()
                    
                    for page in reader.pages:
                        text = page.extract_text()
                        if text.strip():
                            doc.add_paragraph(text)
                    
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_filename = generate_unique_filename(f"{base_name}.docx")
                    output_path = os.path.join("processed", output_filename)
                    
                    doc.save(output_path)
                    output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
                
            except Exception as e:
                logger.error(f"Error converting file {file_path} to Word: {str(e)}")
                continue
        
        return output_files

    def protect_pdfs(self):
        """Protect PDF files with a password"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        password = settings.get('password')
        if not password:
            raise ValueError("Password is required for protection")
        
        output_files = []
        for file_idx, file_path in enumerate(input_files):
            try:
                reader = PdfReader(file_path)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.encrypt(password)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_protected.pdf")
                output_path = os.path.join("processed", output_filename)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
            except Exception as e:
                logger.error(f"Error protecting file {file_path}: {str(e)}")
                continue
        return output_files

    def rotate_pdfs(self):
        """Rotate PDF files"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        rotation = int(settings.get('rotation', 90))
        
        output_files = []
        for file_idx, file_path in enumerate(input_files):
            try:
                reader = PdfReader(file_path)
                writer = PdfWriter()
                for page in reader.pages:
                    page.rotate(rotation)
                    writer.add_page(page)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_rotated.pdf")
                output_path = os.path.join("processed", output_filename)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
            except Exception as e:
                logger.error(f"Error rotating file {file_path}: {str(e)}")
                continue
        return output_files

    def watermark_pdfs(self):
        """Add watermark to PDF files"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        text = settings.get('watermark_text', 'CONFIDENTIAL')
        
        output_files = []
        for file_idx, file_path in enumerate(input_files):
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                import io
                
                # Create watermark
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                can.setFont("Helvetica", 40)
                can.setStrokeColorRGB(0.5, 0.5, 0.5, 0.3)
                can.setFillColorRGB(0.5, 0.5, 0.5, 0.3)
                can.saveState()
                can.translate(300, 400)
                can.rotate(45)
                can.drawCentredString(0, 0, text)
                can.restoreState()
                can.save()
                packet.seek(0)
                watermark_reader = PdfReader(packet)
                watermark_page = watermark_reader.pages[0]

                reader = PdfReader(file_path)
                writer = PdfWriter()
                for page in reader.pages:
                    page.merge_page(watermark_page)
                    writer.add_page(page)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_watermarked.pdf")
                output_path = os.path.join("processed", output_filename)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
            except Exception as e:
                logger.error(f"Error watermarking file {file_path}: {str(e)}")
                continue
        return output_files

    def unlock_pdfs(self):
        """Unlock protected PDF files"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        password = settings.get('password')
        if not password:
            raise ValueError("Password is required for unlocking")
        
        output_files = []
        for file_idx, file_path in enumerate(input_files):
            try:
                reader = PdfReader(file_path)
                if reader.is_encrypted:
                    reader.decrypt(password)
                
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_unlocked.pdf")
                output_path = os.path.join("processed", output_filename)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
                
                progress = int((file_idx + 1) / len(input_files) * 100)
                self.update_progress(progress, file_idx + 1)
            except Exception as e:
                logger.error(f"Error unlocking file {file_path}: {str(e)}")
                continue
        return output_files

    def organize_pdf_pages(self):
        """Handle removing, extracting, or reordering pages"""
        input_files = json.loads(self.job.input_files)
        settings = json.loads(self.job.settings) if self.job.settings else {}
        pages = settings.get('pages', []) # e.g., [1, 2, 5]
        output_files = []
        
        for file_idx, file_path in enumerate(input_files):
            try:
                reader = PdfReader(file_path)
                writer = PdfWriter()
                
                if self.job.job_type == JobType.REMOVE_PAGES:
                    for i in range(len(reader.pages)):
                        if (i + 1) not in pages:
                            writer.add_page(reader.pages[i])
                else: # EXTRACT or ORGANIZE
                    for p_num in pages:
                        if 0 < p_num <= len(reader.pages):
                            writer.add_page(reader.pages[p_num - 1])
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = generate_unique_filename(f"{base_name}_organized.pdf")
                output_path = os.path.join("processed", output_filename)
                
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
                self.update_progress(int((file_idx + 1) / len(input_files) * 100), file_idx + 1)
            except Exception as e:
                logger.error(f"Error organizing PDF: {e}")
        return output_files

    def repair_pdf(self):
        """Attempt to repair a corrupted PDF by re-saving it"""
        input_files = json.loads(self.job.input_files)
        output_files = []
        for file_idx, file_path in enumerate(input_files):
            try:
                reader = PdfReader(file_path)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                output_filename = generate_unique_filename("repaired.pdf")
                output_path = os.path.join("processed", output_filename)
                with open(output_path, 'wb') as f:
                    writer.write(f)
                output_files.append(output_path)
            except Exception as e:
                logger.error(f"Repair failed: {e}")
        return output_files

    def convert_to_pdf(self):
        """Generic converter for office/images to PDF"""
        input_files = json.loads(self.job.input_files)
        output_files = []
        # Implementation skeleton - in real usage would use libraries like reportlab/pillow/docx
        return output_files

    def convert_from_pdf(self):
        """Generic converter for PDF to other formats"""
        return []

    def add_page_numbers(self):
        """Add page numbers to the bottom of each page"""
        return []

    def sign_pdf(self):
        """Placeholder for digital signature logic"""
        return []

    def redact_pdf(self):
        """Placeholder for text redaction logic"""
        return []

def create_zip_archive(file_paths, zip_filename):
    """Create a ZIP archive from multiple files"""
    zip_path = os.path.join("processed", zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
    
    return zip_path
