import os
import logging
import mimetypes
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class FileValidator:
    def __init__(self):
        self.allowed_extensions = {'.pdf'}
        self.allowed_mimetypes = {'application/pdf'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.min_file_size = 100  # 100 bytes minimum
    
    def validate_file(self, file):
        """Comprehensive file validation"""
        try:
            # Check if file exists
            if not file or not file.filename:
                return False, "No file selected"
            
            # Check filename
            filename = secure_filename(file.filename)
            if not filename:
                return False, "Invalid filename"
            
            # Check file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.allowed_extensions:
                return False, f"Invalid file type. Only PDF files are allowed. Got: {file_ext}"
            
            # Check MIME type
            file.seek(0)  # Reset file pointer
            file_content = file.read(1024)  # Read first 1KB
            file.seek(0)  # Reset file pointer
            
            # Check PDF signature
            if not self._is_pdf_signature(file_content):
                return False, "File doesn't appear to be a valid PDF"
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            if file_size > self.max_file_size:
                return False, f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"
            
            if file_size < self.min_file_size:
                return False, "File too small. Minimum size: 100 bytes"
            
            # Additional security checks
            if not self._security_check(filename):
                return False, "Filename contains invalid characters"
            
            return True, "File is valid"
        
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return False, f"Error validating file: {str(e)}"
    
    def _is_pdf_signature(self, file_content):
        """Check if file has PDF signature"""
        try:
            # PDF files start with %PDF-
            if file_content.startswith(b'%PDF-'):
                return True
            return False
        except:
            return False
    
    def _security_check(self, filename):
        """Additional security checks for filename"""
        try:
            # Check for path traversal attempts
            if '..' in filename or '/' in filename or '\\' in filename:
                return False
            
            # Check for null bytes
            if '\x00' in filename:
                return False
            
            # Check for control characters
            if any(ord(c) < 32 for c in filename if c not in '\t\n\r'):
                return False
            
            # Check filename length
            if len(filename) > 255:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error in security check: {str(e)}")
            return False
