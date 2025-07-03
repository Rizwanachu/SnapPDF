import os
import logging
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# Import routes after app creation
from routes import *

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return render_template('index.html', error="File too large. Maximum size is 50MB."), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error="Internal server error. Please try again."), 500
