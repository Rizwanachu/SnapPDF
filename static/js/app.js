// DocumentToolkit JavaScript functionality

// Global variables
let uploadInProgress = false;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Check for cleanup on page load
    scheduleCleanup();
}

function setupEventListeners() {
    // File input change handlers
    const fileInput = document.getElementById('file');
    const filesInput = document.getElementById('files');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleSingleFileChange);
    }
    
    if (filesInput) {
        filesInput.addEventListener('change', handleMultipleFileChange);
    }
    
    // Form submission handler
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmission);
    }
    
    // Operation change handler
    const operationSelect = document.getElementById('operation');
    if (operationSelect) {
        operationSelect.addEventListener('change', handleOperationChange);
    }
    
    // Prevent multiple submissions
    window.addEventListener('beforeunload', function(e) {
        if (uploadInProgress) {
            e.preventDefault();
            e.returnValue = 'File upload in progress. Are you sure you want to leave?';
        }
    });
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function handleSingleFileChange(event) {
    const file = event.target.files[0];
    if (file) {
        if (!validatePDFFile(file)) {
            event.target.value = '';
            return;
        }
        
        // Show file info
        showFileInfo(file);
    }
}

function handleMultipleFileChange(event) {
    const files = Array.from(event.target.files);
    
    if (files.length < 2) {
        showAlert('Please select at least 2 PDF files for merging.', 'warning');
        event.target.value = '';
        return;
    }
    
    // Validate all files
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!validatePDFFile(file)) {
            event.target.value = '';
            return;
        }
    }
    
    // Show files info
    showMultipleFilesInfo(files);
}

function validatePDFFile(file) {
    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showAlert(`File "${file.name}" is too large. Maximum size is 50MB.`, 'error');
        return false;
    }
    
    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showAlert(`File "${file.name}" is not a PDF file.`, 'error');
        return false;
    }
    
    // Check minimum size
    if (file.size < 100) {
        showAlert(`File "${file.name}" is too small to be a valid PDF.`, 'error');
        return false;
    }
    
    return true;
}

function showFileInfo(file) {
    const fileSize = formatFileSize(file.size);
    const info = `Selected: ${file.name} (${fileSize})`;
    
    // Create or update file info element
    let fileInfoElement = document.getElementById('fileInfo');
    if (!fileInfoElement) {
        fileInfoElement = document.createElement('div');
        fileInfoElement.id = 'fileInfo';
        fileInfoElement.className = 'alert alert-info mt-2';
        
        const fileInput = document.getElementById('file');
        fileInput.parentNode.appendChild(fileInfoElement);
    }
    
    fileInfoElement.innerHTML = `<i class="fas fa-file-pdf me-2"></i>${info}`;
}

function showMultipleFilesInfo(files) {
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    const info = `Selected: ${files.length} files (Total: ${formatFileSize(totalSize)})`;
    
    // Create or update file info element
    let fileInfoElement = document.getElementById('multiFileInfo');
    if (!fileInfoElement) {
        fileInfoElement = document.createElement('div');
        fileInfoElement.id = 'multiFileInfo';
        fileInfoElement.className = 'alert alert-info mt-2';
        
        const filesInput = document.getElementById('files');
        filesInput.parentNode.appendChild(fileInfoElement);
    }
    
    fileInfoElement.innerHTML = `<i class="fas fa-layer-group me-2"></i>${info}`;
}

function formatFileSize(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

function handleOperationChange(event) {
    const operation = event.target.value;
    const singleFileSection = document.getElementById('singleFileSection');
    const multiFileSection = document.getElementById('multiFileSection');
    const fileInput = document.getElementById('file');
    const filesInput = document.getElementById('files');
    
    // Clear any existing file info
    const fileInfo = document.getElementById('fileInfo');
    const multiFileInfo = document.getElementById('multiFileInfo');
    if (fileInfo) fileInfo.remove();
    if (multiFileInfo) multiFileInfo.remove();
    
    if (operation === 'merge_pdfs') {
        singleFileSection.classList.add('d-none');
        multiFileSection.classList.remove('d-none');
        fileInput.removeAttribute('required');
        filesInput.setAttribute('required', 'required');
        fileInput.value = '';
    } else {
        singleFileSection.classList.remove('d-none');
        multiFileSection.classList.add('d-none');
        fileInput.setAttribute('required', 'required');
        filesInput.removeAttribute('required');
        filesInput.value = '';
    }
}

function handleFormSubmission(event) {
    const form = event.target;
    const operation = form.operation.value;
    
    // Validate form based on operation
    if (operation === 'merge_pdfs') {
        const files = form.files.files;
        if (files.length < 2) {
            event.preventDefault();
            showAlert('Please select at least 2 PDF files for merging.', 'error');
            return;
        }
    } else {
        const file = form.file.files[0];
        if (!file) {
            event.preventDefault();
            showAlert('Please select a PDF file.', 'error');
            return;
        }
    }
    
    // Show loading state
    showLoadingState();
    uploadInProgress = true;
    
    // Set timeout for long operations
    setTimeout(function() {
        if (uploadInProgress) {
            showAlert('Processing is taking longer than expected. Please wait...', 'info');
        }
    }, 30000); // 30 seconds
}

function showLoadingState() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const submitBtn = document.getElementById('submitBtn');
    
    if (loadingIndicator) {
        loadingIndicator.classList.remove('d-none');
    }
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    }
    
    // Disable form inputs
    const form = document.getElementById('uploadForm');
    if (form) {
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => input.disabled = true);
    }
}

function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    const icon = type === 'error' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-triangle' : 
                 type === 'success' ? 'check-circle' : 'info-circle';
    
    alertDiv.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insert at the top of the main content
    const mainContent = document.querySelector('main.container');
    const firstChild = mainContent.firstChild;
    mainContent.insertBefore(alertDiv, firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function cleanupFiles() {
    if (confirm('Are you sure you want to clean up all temporary files?')) {
        fetch('/cleanup', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showAlert('Files cleaned up successfully!', 'success');
            } else {
                showAlert('Error cleaning up files: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error cleaning up files.', 'error');
        });
    }
}

function scheduleCleanup() {
    // Schedule cleanup every 30 minutes
    setInterval(function() {
        fetch('/cleanup', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Automatic cleanup completed:', data.message);
        })
        .catch(error => {
            console.error('Automatic cleanup error:', error);
        });
    }, 30 * 60 * 1000); // 30 minutes
}

// Utility functions for text processing results
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showAlert('Text copied to clipboard!', 'success');
    }, function(err) {
        console.error('Could not copy text: ', err);
        showAlert('Failed to copy text to clipboard.', 'error');
    });
}

function downloadAsText(text, filename) {
    const element = document.createElement('a');
    const file = new Blob([text], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

// Export functions for global use
window.cleanupFiles = cleanupFiles;
window.copyToClipboard = copyToClipboard;
window.downloadAsText = downloadAsText;
