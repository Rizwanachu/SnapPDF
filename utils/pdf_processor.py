import os
import logging
import PyPDF2
import pdfplumber
from io import BytesIO
import zipfile
import tempfile

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.max_pages = 1000  # Limit for safety
        self.max_text_length = 1000000  # 1MB text limit
    
    def extract_text(self, pdf_path):
        """Extract text from PDF using both PyPDF2 and pdfplumber for better reliability"""
        try:
            text_content = []
            page_count = 0
            
            # First try with pdfplumber (better for complex layouts)
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        if page_num >= self.max_pages:
                            break
                        
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
                        page_count += 1
            except Exception as e:
                logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
                
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    page_count = len(pdf_reader.pages)
                    
                    if page_count > self.max_pages:
                        page_count = self.max_pages
                    
                    for page_num in range(page_count):
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
            
            full_text = "\n".join(text_content)
            
            # Limit text length for safety
            if len(full_text) > self.max_text_length:
                full_text = full_text[:self.max_text_length] + "\n\n[Text truncated due to length limit]"
            
            return {
                'text': full_text,
                'page_count': page_count,
                'character_count': len(full_text),
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return {
                'error': f'Error extracting text: {str(e)}',
                'success': False
            }
    
    def extract_metadata(self, pdf_path):
        """Extract metadata from PDF"""
        try:
            metadata = {}
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Basic info
                metadata['page_count'] = len(pdf_reader.pages)
                metadata['file_size'] = os.path.getsize(pdf_path)
                
                # PDF metadata
                if pdf_reader.metadata:
                    pdf_metadata = pdf_reader.metadata
                    metadata['title'] = pdf_metadata.get('/Title', 'N/A')
                    metadata['author'] = pdf_metadata.get('/Author', 'N/A')
                    metadata['subject'] = pdf_metadata.get('/Subject', 'N/A')
                    metadata['creator'] = pdf_metadata.get('/Creator', 'N/A')
                    metadata['producer'] = pdf_metadata.get('/Producer', 'N/A')
                    metadata['creation_date'] = pdf_metadata.get('/CreationDate', 'N/A')
                    metadata['modification_date'] = pdf_metadata.get('/ModDate', 'N/A')
                else:
                    metadata['title'] = 'N/A'
                    metadata['author'] = 'N/A'
                    metadata['subject'] = 'N/A'
                    metadata['creator'] = 'N/A'
                    metadata['producer'] = 'N/A'
                    metadata['creation_date'] = 'N/A'
                    metadata['modification_date'] = 'N/A'
                
                # Additional info
                metadata['encrypted'] = pdf_reader.is_encrypted
                
                return {
                    'metadata': metadata,
                    'success': True
                }
        
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                'error': f'Error extracting metadata: {str(e)}',
                'success': False
            }
    
    def split_pages(self, pdf_path, output_dir):
        """Split PDF into individual pages"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                if page_count > self.max_pages:
                    return {
                        'error': f'PDF has too many pages ({page_count}). Maximum allowed: {self.max_pages}',
                        'success': False
                    }
                
                output_files = []
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                
                for page_num in range(page_count):
                    pdf_writer = PyPDF2.PdfWriter()
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    output_filename = f"{base_name}_page_{page_num + 1}.pdf"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    with open(output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    
                    output_files.append(output_filename)
                
                # Create ZIP file with all pages
                zip_filename = f"{base_name}_split_pages.zip"
                zip_path = os.path.join(output_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for filename in output_files:
                        file_path = os.path.join(output_dir, filename)
                        zipf.write(file_path, filename)
                        # Remove individual PDF files after adding to ZIP
                        os.remove(file_path)
                
                return {
                    'zip_file': zip_filename,
                    'page_count': page_count,
                    'success': True
                }
        
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            return {
                'error': f'Error splitting PDF: {str(e)}',
                'success': False
            }
    
    def merge_pdfs(self, pdf_paths, output_dir):
        """Merge multiple PDFs into one"""
        try:
            pdf_writer = PyPDF2.PdfWriter()
            total_pages = 0
            source_files = []
            
            for pdf_path in pdf_paths:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    page_count = len(pdf_reader.pages)
                    
                    if total_pages + page_count > self.max_pages:
                        return {
                            'error': f'Total pages would exceed limit ({self.max_pages})',
                            'success': False
                        }
                    
                    for page_num in range(page_count):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    total_pages += page_count
                    source_files.append(os.path.basename(pdf_path))
            
            # Create output filename
            output_filename = f"merged_pdf_{len(pdf_paths)}_files.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            # Clean up source files
            for pdf_path in pdf_paths:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            
            return {
                'output_file': output_filename,
                'total_pages': total_pages,
                'source_files': source_files,
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            return {
                'error': f'Error merging PDFs: {str(e)}',
                'success': False
            }

    def compress_pdf(self, pdf_path, output_dir):
        """Compress PDF by reducing quality of images and removing metadata"""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)

            output_filename = f"compressed_{os.path.basename(pdf_path)}"
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                'output_file': output_filename,
                'success': True
            }
        except Exception as e:
            logger.error(f"Error compressing PDF: {str(e)}")
            return {'error': str(e), 'success': False}

    def protect_pdf(self, pdf_path, output_dir, password):
        """Protect PDF with a password"""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.encrypt(password)

            output_filename = f"protected_{os.path.basename(pdf_path)}"
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                'output_file': output_filename,
                'success': True
            }
        except Exception as e:
            logger.error(f"Error protecting PDF: {str(e)}")
            return {'error': str(e), 'success': False}

    def rotate_pdf(self, pdf_path, output_dir, rotation=90):
        """Rotate all pages in a PDF"""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page in reader.pages:
                page.rotate(rotation)
                writer.add_page(page)

            output_filename = f"rotated_{os.path.basename(pdf_path)}"
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                'output_file': output_filename,
                'success': True
            }
        except Exception as e:
            logger.error(f"Error rotating PDF: {str(e)}")
            return {'error': str(e), 'success': False}
