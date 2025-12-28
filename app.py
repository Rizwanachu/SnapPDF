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
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - using SQLite for local storage
db_path = os.path.join(app.instance_path, 'pdf_tools.db')
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}

# App configuration
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["PROCESSED_FOLDER"] = "processed"
app.config["FREE_USER_FILE_LIMIT"] = 5 * 1024 * 1024  # 5MB per file for free users
app.config["FREE_USER_BATCH_LIMIT"] = 3  # 3 files per batch for free users
app.config["PRO_USER_FILE_LIMIT"] = 100 * 1024 * 1024  # 100MB per file for pro users
app.config["PRO_USER_BATCH_LIMIT"] = 100  # 100 files per batch for pro users

# Initialize the app with the extension
db.init_app(app)

# Create upload and processed directories
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

with app.app_context():
    # Import models to create tables
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    
    # Cleanup old files on startup
    from utils import cleanup_old_files
    cleanup_old_files(app.config['UPLOAD_FOLDER'])
    cleanup_old_files(app.config['PROCESSED_FOLDER'])

# Import routes after app is configured
import routes  # noqa: F401
