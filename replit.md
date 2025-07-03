# PDF Tools Application

## Overview

This is a Flask-based web application that provides comprehensive PDF processing tools including merging, splitting, compression, OCR, and document conversion capabilities. The application features user authentication through Replit Auth, a job queue system for background processing, and a modern Bootstrap-based UI.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite with SQLAlchemy models (local storage)
- **Authentication**: Custom user authentication with Flask-Login
- **Session Management**: Flask-Login for user session handling
- **File Processing**: Background job queue system using threading

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with responsive design
- **JavaScript**: Vanilla JavaScript with modular class-based structure
- **File Handling**: Drag-and-drop interface with progress tracking
- **Real-time Updates**: AJAX-based queue status monitoring

## Key Components

### Database Models
- **User**: Core user model with premium status tracking (required for Replit Auth)
- **OAuth**: OAuth token storage for authentication (required for Replit Auth)
- **ProcessingJob**: Job tracking with status, progress, and file metadata
- **JobType/JobStatus**: Enums for job categorization and state management

### Processing Engine
- **PDFProcessor**: Main processing class handling all PDF operations
- **QueueManager**: Thread-based job queue with configurable worker limits
- **Background Workers**: Dedicated threads for non-blocking file processing

### File Management
- **Upload System**: Secure file upload with size limits and validation
- **Storage Strategy**: Local filesystem with organized upload/processed directories
- **Cleanup Utilities**: Automated file cleanup for storage management

### Security Features
- **Authentication**: OAuth-based user authentication
- **File Validation**: PDF format validation and size restrictions
- **Session Security**: Secure session management with proper timeouts
- **User Limits**: Free tier restrictions (10MB per file, 5 files per batch)

## Data Flow

1. **User Authentication**: Users authenticate via Replit Auth OAuth flow
2. **File Upload**: Files are uploaded and validated on the client side
3. **Job Creation**: Processing jobs are created and queued in the database
4. **Background Processing**: Worker threads pick up jobs from the queue
5. **Progress Updates**: Real-time progress updates via AJAX polling
6. **File Delivery**: Processed files are packaged and delivered via download links

## External Dependencies

### Python Packages
- **Flask**: Web framework and core functionality
- **SQLAlchemy**: Database ORM and migrations
- **PyPDF2**: PDF manipulation and processing
- **Pillow**: Image processing for OCR operations
- **pytesseract**: OCR text extraction
- **python-docx**: Word document processing
- **openpyxl**: Excel file handling
- **reportlab**: PDF generation capabilities

### Frontend Libraries
- **Bootstrap 5**: UI framework and components
- **Font Awesome**: Icon library
- **Vanilla JavaScript**: No external JS frameworks

### Authentication
- **Flask-Dance**: OAuth integration
- **Flask-Login**: Session management
- **Replit Auth**: Primary authentication provider

## Deployment Strategy

### Environment Configuration
- SQLite database stored locally in `instance/pdf_tools.db`
- Session secret via `SESSION_SECRET` environment variable
- File size limits and processing constraints via app config

### File Storage
- Local filesystem storage with configurable directories
- Automatic directory creation for uploads and processed files
- Built-in cleanup mechanisms for temporary files

### Scalability Considerations
- Configurable worker thread pool (currently set to 2 workers)
- Database connection pooling with health checks
- File size and batch processing limits for resource management

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### July 03, 2025 - PayPal Premium Subscriptions

**PayPal Integration:**
- Implemented PayPal payment processing for premium subscriptions
- Added subscription management system with database models
- Created premium subscription page with pricing and features
- Integrated PayPal sandbox for development and testing

**Premium Features:**
- Unlimited file uploads and processing for premium users
- Removed file size restrictions for premium accounts
- Premium status tracking and subscription management
- Automatic premium status updates upon successful payment

**UI Enhancements:**
- Added premium navigation link with crown icon for active subscribers
- Updated tools page to show premium status and unlimited access
- Created comprehensive premium subscription page with pricing
- Added subscription management and cancellation functionality

**Technical Implementation:**
- Added Subscription model with PayPal integration
- Enhanced User model with subscription status checking
- Created PayPal payment processing routes and success handling
- Implemented subscription lifecycle management

### July 03, 2025 - Database Migration & UX Improvements

**Database Changes:**
- Switched from PostgreSQL to SQLite for local storage
- Database now stored in `instance/pdf_tools.db` for better portability
- Removed PostgreSQL dependencies and configurations

**User Experience Improvements:**
- Removed annoying pop-up alerts and replaced with elegant toast notifications
- Added comprehensive file validation with proper error messages
- Added visual loading indicators during processing operations
- Improved file display with detailed information and clear buttons
- Enhanced workflow with better user feedback and progress tracking

### July 03, 2025 - Enhanced PDF Processing & UI Improvements

**PDF Algorithm Enhancements:**
- Enhanced compression with adjustable quality settings (low/medium/high)
- Advanced OCR with multi-language support and dual output formats (txt/PDF/both)
- Improved text extraction with PyMuPDF integration for better accuracy
- Added preview functionality for uploaded PDF files
- Enhanced file information display with metadata extraction

**User Interface Improvements:**
- Redesigned landing page with cleaner, minimalist design
- Added compression quality settings interface (high/medium/maximum compression)
- Enhanced OCR interface with language selection and output format options
- Added PDF preview and file info modals for better user experience
- Improved file upload display with preview and info buttons
- Streamlined features section for better readability

**Technical Improvements:**
- Added PyMuPDF for better PDF to image conversion
- Enhanced JavaScript with preview and file info functionality
- Improved error handling and user feedback
- Added new API endpoints for file preview and metadata

**Architecture Updates:**
- Added `/preview/<file_id>` endpoint for PDF previews
- Added `/file-info/<file_id>` endpoint for detailed file information
- Enhanced PDF processing settings support in job configuration
- Improved modular JavaScript structure for better maintainability

## Changelog

- July 03, 2025. Initial setup
- July 03, 2025. Enhanced PDF processing algorithms and improved UI