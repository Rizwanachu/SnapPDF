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
    PROTECT = "protect"
    UNLOCK = "unlock"
    WATERMARK = "watermark"
    ROTATE = "rotate"
    EXTRACT_IMAGES = "extract_images"
    CONVERT_WORD = "convert_word"
    CONVERT_EXCEL = "convert_excel"
    REMOVE_PAGES = "remove_pages"
    EXTRACT_PAGES = "extract_pages"
    ORGANIZE = "organize"
    SCAN_TO_PDF = "scan_to_pdf"
    REPAIR = "repair"
    JPG_TO_PDF = "jpg_to_pdf"
    WORD_TO_PDF = "word_to_pdf"
    POWERPOINT_TO_PDF = "powerpoint_to_pdf"
    EXCEL_TO_PDF = "excel_to_pdf"
    HTML_TO_PDF = "html_to_pdf"
    PDF_TO_JPG = "pdf_to_jpg"
    PDF_TO_POWERPOINT = "pdf_to_powerpoint"
    PDF_TO_EXCEL = "pdf_to_excel"
    PDF_TO_PDFA = "pdf_to_pdfa"
    ADD_PAGE_NUMBERS = "add_page_numbers"
    CROP = "crop"
    EDIT = "edit"
    SIGN = "sign"
    REDACT = "redact"
    COMPARE = "compare"

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
import pytz

def get_now():
    """Get current time in Dubai (GST)"""
    return datetime.now(pytz.timezone('Asia/Dubai'))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # For custom auth
    profile_image_url = db.Column(db.String, nullable=True)
    is_premium = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=get_now)
    updated_at = db.Column(db.DateTime, default=get_now, onupdate=get_now)
    
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
    
    def has_active_subscription(self):
        """Check if user has an active premium subscription"""
        if self.is_premium:
            return True
        
        subs = db.session.query(Subscription).filter_by(user_id=self.id).all()
        for subscription in subs:
            if subscription.is_active():
                return True
        return False
    
    def get_active_subscription(self):
        """Get the user's active subscription if any"""
        subs = db.session.query(Subscription).filter_by(user_id=self.id).all()
        for subscription in subs:
            if subscription.is_active():
                return subscription
        return None

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

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    paypal_agreement_id = db.Column(db.String, unique=True, nullable=True)
    paypal_subscription_id = db.Column(db.String, unique=True, nullable=True)
    status = db.Column(db.Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING)
    plan_name = db.Column(db.String, default="Premium Monthly")
    amount = db.Column(db.Float, default=9.99)
    currency = db.Column(db.String, default="USD")
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    activated_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='subscriptions')
    
    def is_active(self):
        """Check if subscription is currently active"""
        return (self.status == SubscriptionStatus.ACTIVE and 
                (self.expires_at is None or self.expires_at > datetime.now()))
    
    def cancel(self):
        """Cancel the subscription"""
        self.status = SubscriptionStatus.CANCELLED
        self.cancelled_at = datetime.now()
