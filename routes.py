import os
import tempfile
import zipfile
from flask import render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from app import app
from utils.pdf_processor import PDFProcessor
from utils.file_validator import FileValidator
import logging

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file is present
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        operation = request.form.get('operation', 'extract_text')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        # Validate file
        validator = FileValidator()
        is_valid, error_message = validator.validate_file(file)
        
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process PDF
        processor = PDFProcessor()
        result = None
        
        try:
            if operation == 'extract_text':
                result = processor.extract_text(filepath)
            elif operation == 'extract_metadata':
                result = processor.extract_metadata(filepath)
            elif operation == 'split_pages':
                result = processor.split_pages(filepath, app.config['TEMP_FOLDER'])
            elif operation == 'merge_pdfs':
                # For merge operation, handle multiple files
                files = request.files.getlist('files')
                if len(files) < 2:
                    flash('Please select at least 2 PDF files to merge', 'error')
                    return redirect(url_for('index'))
                
                file_paths = []
                for f in files:
                    if f.filename != '':
                        is_valid, error_message = validator.validate_file(f)
                        if is_valid:
                            fname = secure_filename(f.filename)
                            fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                            f.save(fpath)
                            file_paths.append(fpath)
                
                if len(file_paths) < 2:
                    flash('Please select at least 2 valid PDF files', 'error')
                    return redirect(url_for('index'))
                
                result = processor.merge_pdfs(file_paths, app.config['TEMP_FOLDER'])
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return render_template('result.html', 
                                 operation=operation, 
                                 result=result, 
                                 filename=filename)
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            flash(f'Error processing PDF: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['TEMP_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        flash('Error downloading file', 'error')
        return redirect(url_for('index'))

@app.route('/cleanup')
def cleanup_files():
    """Clean up temporary files"""
    try:
        # Clean up temp folder
        temp_folder = app.config['TEMP_FOLDER']
        for filename in os.listdir(temp_folder):
            if filename != '.gitkeep':
                file_path = os.path.join(temp_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        # Clean up upload folder
        upload_folder = app.config['UPLOAD_FOLDER']
        for filename in os.listdir(upload_folder):
            if filename != '.gitkeep':
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        return jsonify({'status': 'success', 'message': 'Files cleaned up successfully'})
    
    except Exception as e:
        logger.error(f"Error cleaning up files: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Error cleaning up files'}), 500
