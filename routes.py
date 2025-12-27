import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
from flask import session, render_template, request, redirect, url_for, flash, jsonify, send_file, abort, Response
from werkzeug.utils import secure_filename
from flask_login import current_user, login_user, logout_user, login_required
from app import app, db
from models import ProcessingJob, JobStatus, JobType, FileUpload, User, Subscription, SubscriptionStatus
from forms import RegistrationForm, LoginForm
from queue_manager import get_queue_manager, start_queue_manager
from pdf_processor import create_zip_archive
from utils import generate_unique_filename, validate_pdf_file, format_file_size, get_user_display_name

logger = logging.getLogger(__name__)

# Register the authentication blueprint
# Configure Flask-Login
from flask_login import LoginManager
from typing import Optional
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))

# Start the queue manager
start_queue_manager()

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    """Main landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('tools'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('tools'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User()
        user.id = str(uuid.uuid4())
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Log in the user
        login_user(user)
        flash('Account created successfully! Welcome to PDF Tools.', 'success')
        return redirect(url_for('tools'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('tools'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                parsed = urlparse(next_page)
                if parsed.netloc or not next_page.startswith('/'):
                    next_page = None
            if not next_page:
                next_page = url_for('tools')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/tools')
@login_required
def tools():
    """Main tools page for authenticated users"""
    user_jobs = ProcessingJob.query.filter_by(user_id=current_user.id).order_by(ProcessingJob.created_at.desc()).limit(10).all()
    return render_template('tools.html', user=current_user, recent_jobs=user_jobs)

@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """Handle file uploads with strict tier enforcement"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    # Strict Premium Check
    is_premium = current_user.is_premium
    
    # Check batch limits
    batch_limit = app.config['FREE_USER_BATCH_LIMIT'] if not is_premium else 100
    if len(files) > batch_limit:
        return jsonify({'error': f'Batch limit exceeded. limit is {batch_limit} files.'}), 400
    
    uploaded_files = []
    total_size = 0
    
    file_limit = app.config['FREE_USER_FILE_LIMIT'] if not is_premium else 100 * 1024 * 1024
    
    for file in files:
        # Validate file
        is_valid, message = validate_pdf_file(file)
        if not is_valid:
            return jsonify({'error': f'File {file.filename}: {message}'}), 400
        
        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > file_limit:
            return jsonify({'error': f'File {file.filename} exceeds {format_file_size(file_limit)} limit'}), 400
        
        total_size += file_size
    
    # Save files
    for file in files:
        try:
            file_id = str(uuid.uuid4())
            stored_filename = generate_unique_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
            
            file.save(file_path)
            
            # Get size again for safety
            file.seek(0, 2)
            current_file_size = file.tell()
            file.seek(0)
            
            # Save to database
            file_upload = FileUpload()
            file_upload.id = file_id
            file_upload.user_id = current_user.id
            file_upload.original_filename = file.filename
            file_upload.stored_filename = stored_filename
            file_upload.file_size = current_file_size
            file_upload.file_path = file_path
            
            db.session.add(file_upload)
            
            uploaded_files.append({
                'id': file_id,
                'original_filename': file.filename,
                'file_size': current_file_size,
                'formatted_size': format_file_size(current_file_size)
            })
            
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {str(e)}")
            return jsonify({'error': f'Error saving file {file.filename}'}), 500
    
    db.session.commit()
    
    return jsonify({
        'message': f'Successfully uploaded {len(uploaded_files)} files',
        'files': uploaded_files,
        'total_size': format_file_size(total_size)
    })

@app.route('/process', methods=['POST'])
@login_required
def process_files():
    """Create a processing job"""
    data = request.get_json()
    
    if not data or 'job_type' not in data or 'file_ids' not in data:
        return jsonify({'error': 'Missing job type or file IDs'}), 400
    
    job_type_str = data['job_type']
    file_ids = data['file_ids']
    
    # Validate job type
    try:
        job_type = JobType(job_type_str)
    except ValueError:
        return jsonify({'error': 'Invalid job type'}), 400
    
    # Get file paths
    file_uploads = FileUpload.query.filter(
        FileUpload.id.in_(file_ids),
        FileUpload.user_id == current_user.id
    ).all()
    
    if len(file_uploads) != len(file_ids):
        return jsonify({'error': 'Some files not found or not owned by user'}), 400
    
    input_files = [fu.file_path for fu in file_uploads]
    
    # Create processing job
    job_id = str(uuid.uuid4())
    job = ProcessingJob()
    job.id = job_id
    job.user_id = current_user.id
    job.job_type = job_type
    job.input_files = json.dumps(input_files)
    job.total_files = len(input_files)
    job.settings = json.dumps(data.get('settings', {}))
    
    db.session.add(job)
    db.session.commit()
    
    # Add to queue
    queue_manager = get_queue_manager()
    queue_manager.add_job(job_id)
    
    return jsonify({
        'job_id': job_id,
        'message': 'Processing job created successfully'
    })

@app.route('/job/<job_id>/status')
@login_required
def job_status(job_id):
    """Get job status"""
    job = ProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    queue_manager = get_queue_manager()
    status = queue_manager.get_job_status(job_id)
    
    if status:
        # Add output files info if completed
        if job.status == JobStatus.COMPLETED and job.output_files:
            output_files = json.loads(job.output_files)
            status['output_files'] = []
            for file_path in output_files:
                if os.path.exists(file_path):
                    status['output_files'].append({
                        'filename': os.path.basename(file_path),
                        'path': file_path,
                        'size': format_file_size(os.path.getsize(file_path))
                    })
    
    return jsonify(status or {'error': 'Job not found'})

@app.route('/job/<job_id>/cancel', methods=['POST'])
@login_required
def cancel_job(job_id):
    """Cancel a job"""
    job = ProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    queue_manager = get_queue_manager()
    success = queue_manager.cancel_job(job_id)
    
    if success:
        return jsonify({'message': 'Job cancelled successfully'})
    else:
        return jsonify({'error': 'Job cannot be cancelled (already processing or completed)'}), 400

@app.route('/download/<job_id>')
@login_required
def download_job_results(job_id):
    """Download job results as ZIP file"""
    job = ProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job or job.status != JobStatus.COMPLETED:
        abort(404)
    
    if not job.output_files:
        abort(404)
    
    output_files = json.loads(job.output_files)
    
    # If single file, serve directly
    if len(output_files) == 1:
        file_path = output_files[0]
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
    
    # Multiple files, create ZIP
    zip_filename = f"job_{job_id}_results.zip"
    zip_path = create_zip_archive(output_files, zip_filename)
    
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    
    abort(404)

@app.route('/download/file/<job_id>/<filename>')
@login_required
def download_single_file(job_id, filename):
    """Download a single file from job results"""
    job = ProcessingJob.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job or job.status != JobStatus.COMPLETED:
        abort(404)
    
    if not job.output_files:
        abort(404)
    
    output_files = json.loads(job.output_files)
    
    for file_path in output_files:
        if os.path.basename(file_path) == filename:
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
    
    abort(404)

@app.route('/preview/<file_id>')
@login_required
def preview_file(file_id):
    """Preview uploaded PDF file"""
    file_upload = FileUpload.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not file_upload:
        abort(404)
    
    try:
        import fitz
        
        # Open PDF and get first page for preview
        pdf_document = fitz.open(file_upload.file_path)
        if pdf_document.page_count > 0:
            page = pdf_document[0]
            # Convert to image with reasonable quality
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # type: ignore
            img_data = pix.tobytes("png")
            pdf_document.close()
            
            from flask import Response
            return Response(img_data, mimetype='image/png')
        else:
            abort(404)
            
    except Exception as e:
        logger.error(f"Error generating preview for file {file_id}: {str(e)}")
        abort(500)

@app.route('/file-info/<file_id>')
@login_required
def file_info(file_id):
    """Get detailed file information"""
    file_upload = FileUpload.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not file_upload:
        abort(404)
    
    try:
        # Get PDF metadata
        file_info = {
            'id': file_upload.id,
            'filename': file_upload.original_filename,
            'size': file_upload.file_size,
            'formatted_size': format_file_size(file_upload.file_size),
            'upload_date': file_upload.created_at.isoformat()
        }
        
        # Try to get PDF specific info
        try:
            from PyPDF2 import PdfReader
            with open(file_upload.file_path, 'rb') as file:
                reader = PdfReader(file)
                file_info.update({
                    'pages': len(reader.pages),
                    'metadata': reader.metadata._get_object() if reader.metadata else {},  # type: ignore
                    'encrypted': reader.is_encrypted
                })
        except Exception as e:
            logger.warning(f"Could not read PDF metadata: {str(e)}")
            file_info.update({
                'pages': 'Unknown',
                'metadata': {},
                'encrypted': False
            })
        
        return jsonify(file_info)
        
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {str(e)}")
        return jsonify({'error': 'Could not retrieve file information'}), 500

@app.route('/api/queue/status')
@login_required
def queue_status():
    """Get queue status"""
    queue_manager = get_queue_manager()
    status = queue_manager.get_queue_status()
    
    # Add user's jobs
    user_jobs = ProcessingJob.query.filter_by(user_id=current_user.id).filter(
        ProcessingJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
    ).order_by(ProcessingJob.created_at.desc()).all()
    
    status['user_jobs'] = []
    for job in user_jobs:
        status['user_jobs'].append({
            'id': job.id,
            'job_type': job.job_type.value,
            'status': job.status.value,
            'progress': job.progress,
            'created_at': job.created_at.isoformat()
        })
    
    return jsonify(status)

@app.route('/preview-processed/<job_id>/<filename>')
@login_required
def preview_processed_file(job_id, filename):
    """Preview processed PDF file from job results"""
    try:
        # Get the job and verify ownership
        job = ProcessingJob.query.filter_by(
            id=job_id,
            user_id=current_user.id
        ).first()
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job.status != JobStatus.COMPLETED:
            return jsonify({'error': 'Job not completed'}), 400
        
        # Find the file in the job's output files
        output_files = json.loads(job.output_files) if job.output_files else []
        file_path = None
        
        for file in output_files:
            if file.endswith(filename):
                file_path = file
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Generate preview image using PyMuPDF
        import fitz
        
        doc = fitz.open(file_path)
        page = doc[0]  # First page
        pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))  # type: ignore  # 1.2x zoom
        img_data = pix.tobytes("png")
        doc.close()
        
        return Response(img_data, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error generating preview for processed file {filename}: {str(e)}")
        return jsonify({'error': 'Could not generate preview'}), 500

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Cleanup old files (moved to app.py initialization)
def cleanup_files():
    from utils import cleanup_old_files
    cleanup_old_files(app.config['UPLOAD_FOLDER'])
    cleanup_old_files(app.config['PROCESSED_FOLDER'])

# Premium subscription system - simplified for demo

@app.route('/premium')
@login_required
def premium():
    """Premium subscription page"""
    user_subscription = current_user.get_active_subscription()
    return render_template('premium.html', 
                         user=current_user, 
                         subscription=user_subscription)

@app.route('/subscribe', methods=['POST'])
@login_required
def create_premium_subscription():
    """Create premium subscription with verified status"""
    try:
        # Only $4.99 per month
        amount = 4.99
        currency = "USD"
        plan_name = "SnapPDF Pro"
        
        # In a real app, we'd verify the payment via a webhook or API call here.
        # For now, we simulate a 'payment_id' coming from the frontend after success.
        payment_confirmed = request.form.get('payment_confirmed') == 'true'
        
        if not payment_confirmed:
            flash('Payment was not confirmed. Please try again.', 'error')
            return redirect(url_for('premium'))

        # Create subscription record
        subscription = Subscription()
        subscription.id = str(uuid.uuid4())
        subscription.user_id = current_user.id
        subscription.paypal_subscription_id = "verified_" + str(uuid.uuid4())[:8]
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.activated_at = datetime.now()
        subscription.expires_at = datetime.now() + timedelta(days=30)
        subscription.amount = amount
        subscription.currency = currency
        subscription.plan_name = plan_name
        
        db.session.add(subscription)
        
        # Update user premium status
        current_user.is_premium = True
        db.session.commit()
        
        flash('Welcome to SnapPDF Pro! Your unlimited document journey starts now.', 'success')
        return redirect(url_for('tools'))
        
    except Exception as e:
        logger.error(f"Subscription creation error: {e}")
        flash('Error verifying payment. Please contact support.', 'error')
        return redirect(url_for('premium'))

# Simplified demo routes removed complex PayPal integration

@app.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user subscription"""
    try:
        subscription = current_user.get_active_subscription()
        if subscription:
            subscription.cancel()
            current_user.is_premium = False
            db.session.commit()
            flash('Subscription cancelled successfully.', 'info')
        else:
            flash('No active subscription found.', 'error')
    except Exception as e:
        logger.error(f"Subscription cancellation error: {e}")
        flash('Error cancelling subscription. Please contact support.', 'error')
    
    return redirect(url_for('premium'))

# Tool routes
TOOL_CONFIGS = {
    'merge': {'title': 'Merge PDF', 'category': 'Organize', 'job_type': 'merge', 'multiple': True},
    'split': {'title': 'Split PDF', 'category': 'Organize', 'job_type': 'split', 'multiple': False},
    'compress': {'title': 'Compress PDF', 'category': 'Optimize', 'job_type': 'compress', 'multiple': True},
    'repair': {'title': 'Repair PDF', 'category': 'Optimize', 'job_type': 'repair', 'multiple': True},
    'ocr': {'title': 'OCR PDF', 'category': 'Optimize', 'job_type': 'ocr', 'multiple': True},
    'jpg-to-pdf': {'title': 'JPG to PDF', 'category': 'Convert to PDF', 'job_type': 'jpg_to_pdf', 'multiple': True},
    'word-to-pdf': {'title': 'Word to PDF', 'category': 'Convert to PDF', 'job_type': 'word_to_pdf', 'multiple': True},
    'powerpoint-to-pdf': {'title': 'PowerPoint to PDF', 'category': 'Convert to PDF', 'job_type': 'powerpoint_to_pdf', 'multiple': True},
    'excel-to-pdf': {'title': 'Excel to PDF', 'category': 'Convert to PDF', 'job_type': 'excel_to_pdf', 'multiple': True},
    'html-to-pdf': {'title': 'HTML to PDF', 'category': 'Convert to PDF', 'job_type': 'html_to_pdf', 'multiple': True},
    'pdf-to-jpg': {'title': 'PDF to JPG', 'category': 'Convert from PDF', 'job_type': 'pdf_to_jpg', 'multiple': True},
    'pdf-to-word': {'title': 'PDF to Word', 'category': 'Convert from PDF', 'job_type': 'convert_word', 'multiple': True},
    'pdf-to-powerpoint': {'title': 'PDF to PowerPoint', 'category': 'Convert from PDF', 'job_type': 'pdf_to_powerpoint', 'multiple': True},
    'pdf-to-excel': {'title': 'PDF to Excel', 'category': 'Convert from PDF', 'job_type': 'pdf_to_excel', 'multiple': True},
    'pdf-to-pdfa': {'title': 'PDF to PDF/A', 'category': 'Convert from PDF', 'job_type': 'pdf_to_pdfa', 'multiple': True},
    'rotate': {'title': 'Rotate PDF', 'category': 'Edit', 'job_type': 'rotate', 'multiple': True},
    'add-page-numbers': {'title': 'Add Page Numbers', 'category': 'Edit', 'job_type': 'add_page_numbers', 'multiple': True},
    'add-watermark': {'title': 'Add Watermark', 'category': 'Edit', 'job_type': 'watermark', 'multiple': True},
    'crop': {'title': 'Crop PDF', 'category': 'Edit', 'job_type': 'crop', 'multiple': True},
    'edit': {'title': 'Edit PDF', 'category': 'Edit', 'job_type': 'edit', 'multiple': True},
    'unlock': {'title': 'Unlock PDF', 'category': 'Security', 'job_type': 'unlock', 'multiple': True},
    'protect': {'title': 'Protect PDF', 'category': 'Security', 'job_type': 'protect', 'multiple': True},
    'sign': {'title': 'Sign PDF', 'category': 'Security', 'job_type': 'sign', 'multiple': True},
    'redact': {'title': 'Redact PDF', 'category': 'Security', 'job_type': 'redact', 'multiple': True},
    'compare': {'title': 'Compare PDF', 'category': 'Security', 'job_type': 'compare', 'multiple': True},
    'extract-images': {'title': 'Extract Images', 'category': 'Organize', 'job_type': 'extract_images', 'multiple': True},
    'remove-pages': {'title': 'Remove Pages', 'category': 'Organize', 'job_type': 'remove_pages', 'multiple': False},
    'extract-pages': {'title': 'Extract Pages', 'category': 'Organize', 'job_type': 'extract_pages', 'multiple': False},
    'organize': {'title': 'Organize PDF', 'category': 'Organize', 'job_type': 'organize', 'multiple': False},
}

@app.route('/tool/<tool_id>', methods=['GET', 'POST'])
@login_required
def tool_page(tool_id):
    """Generic tool page for all PDF operations"""
    if tool_id not in TOOL_CONFIGS:
        flash('Tool not found', 'error')
        return redirect(url_for('tools'))
    
    config = TOOL_CONFIGS[tool_id]
    
    if request.method == 'POST':
        # Get uploaded files from form
        if 'files' not in request.files:
            flash('No files uploaded', 'error')
            return redirect(url_for('tool_page', tool_id=tool_id))
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('No files selected', 'error')
            return redirect(url_for('tool_page', tool_id=tool_id))
        
        try:
            # Save uploaded files
            uploaded_file_ids = []
            for file in files:
                if file and file.filename:
                    file_id = str(uuid.uuid4())
                    stored_filename = generate_unique_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
                    file.save(file_path)
                    
                    file_upload = FileUpload()
                    file_upload.id = file_id
                    file_upload.user_id = current_user.id
                    file_upload.original_filename = file.filename
                    file_upload.stored_filename = stored_filename
                    file_upload.file_size = os.path.getsize(file_path)
                    file_upload.file_path = file_path
                    
                    db.session.add(file_upload)
                    uploaded_file_ids.append(file_id)
            
            db.session.commit()
            
            if not uploaded_file_ids:
                flash('No files uploaded', 'error')
                return redirect(url_for('tool_page', tool_id=tool_id))
            
            # Prepare settings based on tool
            settings = {}
            
            if tool_id == 'compress':
                settings['compression_quality'] = request.form.get('compression_quality', 'medium')
            elif tool_id == 'rotate':
                settings['rotation'] = request.form.get('rotation', '90')
            elif tool_id == 'add-watermark':
                settings['watermark_text'] = request.form.get('watermark_text', 'CONFIDENTIAL')
            elif tool_id == 'crop':
                settings['crop_box'] = [0.1, 0.1, 0.9, 0.9]
            elif tool_id == 'protect':
                settings['password'] = request.form.get('password', '')
            elif tool_id == 'unlock':
                settings['password'] = request.form.get('password', '')
            elif tool_id == 'sign':
                settings['signature_text'] = request.form.get('signature_text', 'Signed')
            elif tool_id == 'redact':
                keywords_str = request.form.get('keywords', '')
                settings['keywords'] = [k.strip() for k in keywords_str.split(',') if k.strip()]
            elif tool_id in ['remove-pages', 'extract-pages', 'organize']:
                pages_str = request.form.get('pages', '')
                try:
                    settings['pages'] = [int(p.strip()) for p in pages_str.split(',') if p.strip()]
                except ValueError:
                    flash('Invalid page numbers', 'error')
                    return redirect(url_for('tool_page', tool_id=tool_id))
            elif tool_id == 'ocr':
                settings['ocr_language'] = request.form.get('ocr_language', 'eng')
                settings['output_format'] = request.form.get('output_format', 'txt')
            
            # Create processing job
            job_id = str(uuid.uuid4())
            file_uploads = FileUpload.query.filter(FileUpload.id.in_(uploaded_file_ids)).all()
            input_files = [fu.file_path for fu in file_uploads]
            
            job = ProcessingJob()
            job.id = job_id
            job.user_id = current_user.id
            job.job_type = JobType(config['job_type'])
            job.input_files = json.dumps(input_files)
            job.total_files = len(input_files)
            job.settings = json.dumps(settings)
            
            db.session.add(job)
            db.session.commit()
            
            # Add to queue
            queue_manager = get_queue_manager()
            queue_manager.add_job(job_id)
            
            flash(f'{config["title"]} job started!', 'success')
            return redirect(url_for('job_status', job_id=job_id))
            
        except Exception as e:
            logger.error(f"Error in tool_page: {str(e)}")
            flash('Error processing request', 'error')
            return redirect(url_for('tool_page', tool_id=tool_id))
    
    return render_template('tool.html', tool_id=tool_id, config=config)

@app.route('/all-tools')
@login_required
def all_tools():
    """Display all available tools"""
    tools_by_category = {}
    for tool_id, config in TOOL_CONFIGS.items():
        category = config['category']
        if category not in tools_by_category:
            tools_by_category[category] = []
        tools_by_category[category].append({
            'id': tool_id,
            'title': config['title'],
            'url': url_for('tool_page', tool_id=tool_id)
        })
    
    return render_template('all-tools.html', tools_by_category=tools_by_category)
