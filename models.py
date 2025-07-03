from datetime import datetime
from enum import Enum
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, Text
from werkzeug.security import generate_password_hash, check_password_hash

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(Enum):
    MERGE = "merge"
    SPLIT = "split"
    COMPRESS = "compress"
    OCR = "ocr"
    CONVERT_WORD = "convert_word"
    CONVERT_EXCEL = "convert_excel"

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # For custom auth
    profile_image_url = db.Column(db.String, nullable=True)
    is_premium = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship with jobs
    jobs = db.relationship('ProcessingJob', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Return user id as string for Flask-Login"""
        return str(self.id)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class ProcessingJob(db.Model):
    __tablename__ = 'processing_jobs'
    
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    job_type = db.Column(db.Enum(JobType), nullable=False)
    status = db.Column(db.Enum(JobStatus), default=JobStatus.PENDING)
    
    # File information
    input_files = db.Column(Text)  # JSON string of input file paths
    output_files = db.Column(Text)  # JSON string of output file paths
    
    # Progress tracking
    progress = db.Column(db.Integer, default=0)  # 0-100
    total_files = db.Column(db.Integer, default=0)
    processed_files = db.Column(db.Integer, default=0)
    
    # Error handling
    error_message = db.Column(Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Settings for specific job types
    settings = db.Column(Text)  # JSON string for job-specific settings

class FileUpload(db.Model):
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String, nullable=False)
    stored_filename = db.Column(db.String, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship with user
    user = db.relationship('User', backref='uploaded_files')
