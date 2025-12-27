import os
import uuid
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename

def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension"""
    filename = secure_filename(original_filename)
    name, ext = os.path.splitext(filename)
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name}_{timestamp}_{unique_id}{ext}"

def get_file_hash(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def cleanup_old_files(directory, max_age_hours=24):
    """Remove files older than max_age_hours from a directory and database records"""
    from app import db, app
    from models import ProcessingJob, FileUpload
    from datetime import datetime, timedelta
    
    now = datetime.now()
    max_age_seconds = max_age_hours * 3600
    cutoff_time = now - timedelta(hours=max_age_hours)
    
    # 1. Cleanup Physical Files
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_age = now - datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_age.total_seconds() > max_age_seconds:
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    # 2. Cleanup Database Records (Recent Jobs/History)
    with app.app_context():
        try:
            # Delete old processing jobs
            old_jobs = ProcessingJob.query.filter(ProcessingJob.created_at < cutoff_time).all()
            for job in old_jobs:
                db.session.delete(job)
            
            # Delete old file uploads
            old_uploads = FileUpload.query.filter(FileUpload.created_at < cutoff_time).all()
            for upload in old_uploads:
                db.session.delete(upload)
                
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error during DB cleanup: {e}")

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_pdf_file(file):
    """Validate that uploaded file is a supported format"""
    if not file or not file.filename:
        return False, "No file selected"
    
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.pptx', '.xlsx', '.html'}
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in allowed_extensions:
        return False, f"Unsupported file format: {ext}"
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, "Valid file format"

def get_user_display_name(user):
    """Get a display name for a user"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.email:
        return user.email.split('@')[0]
    else:
        return f"User {user.id}"
