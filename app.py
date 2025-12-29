import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Helper to check if running on Vercel
IS_VERCEL = "VERCEL" in os.environ

# Configure database - use PostgreSQL in production, SQLite locally
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Ensure PostgreSQL URL is properly formatted for SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "connect_args": {"connect_timeout": 10}
    }
else:
    # Local development - use SQLite
    db_path = os.path.join('/tmp', 'pdf_tools.db')
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }

# Configure file storage
app.config["UPLOAD_FOLDER"] = os.path.join('/tmp', 'uploads')
app.config["PROCESSED_FOLDER"] = os.path.join('/tmp', 'processed')
app.config["TEMP_FOLDER"] = os.path.join('/tmp', 'temp')
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Free vs Premium tier limits
app.config["FREE_USER_FILE_LIMIT"] = 5 * 1024 * 1024  # 5MB per file
app.config["FREE_USER_BATCH_LIMIT"] = 3  # 3 files per batch
app.config["PREMIUM_USER_FILE_LIMIT"] = 100 * 1024 * 1024  # 100MB per file
app.config["PREMIUM_USER_BATCH_LIMIT"] = 100  # 100 files per batch

# Ensure directories exist at startup
def create_directories():
    """Create necessary directories at startup"""
    directories = [
        app.config["UPLOAD_FOLDER"],
        app.config["PROCESSED_FOLDER"],
        app.config["TEMP_FOLDER"]
    ]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create directory {directory}: {e}")

create_directories()

# Initialize database
db.init_app(app)

# Create tables and initialize
with app.app_context():
    # Import models to ensure they're registered
    import models  # noqa: F401
    
    # Create all tables
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")
    
    # Ensure directories exist
    create_directories()
    
    # Cleanup old files on startup (skip on Vercel to avoid cold start overhead)
    if not IS_VERCEL:
        try:
            from utils import cleanup_old_files
            cleanup_old_files(app.config['UPLOAD_FOLDER'], max_age_hours=24)
            cleanup_old_files(app.config['PROCESSED_FOLDER'], max_age_hours=24)
            logging.info("Cleanup of old files completed")
        except Exception as e:
            logging.warning(f"Cleanup encountered an error: {e}")

# Import routes after app is fully configured
import routes  # noqa: F401
