# DocumentToolkit - PDF Processing Application

## Overview

DocumentToolkit is a Flask-based web application that provides comprehensive PDF processing capabilities. The application allows users to upload PDF files and perform various operations including text extraction, metadata extraction, page splitting, and PDF merging. It features a modern Bootstrap-based UI with dark theme support and comprehensive error handling.

## System Architecture

The application follows a traditional Flask MVC pattern with clear separation of concerns:

### Backend Architecture
- **Flask Framework**: Core web framework providing routing, templating, and request handling
- **Modular Design**: Separate modules for different functionalities (routes, utilities, validation)
- **File Processing**: Dedicated PDF processing utilities using PyPDF2 and pdfplumber libraries
- **Error Handling**: Comprehensive error handling with custom error pages and flash messaging

### Frontend Architecture
- **Bootstrap 5**: Modern responsive UI framework with dark theme support
- **Vanilla JavaScript**: Client-side functionality for form handling and user interactions
- **Font Awesome**: Icon library for enhanced UI elements
- **Custom CSS**: Additional styling for PDF-specific UI components

## Key Components

### Core Application (`app.py`)
- Flask application initialization and configuration
- File upload limits (50MB maximum)
- Directory structure creation for uploads and temporary files
- Global error handlers for common HTTP errors

### Routing Layer (`routes.py`)
- Main application routes and request handling
- File upload processing and validation
- PDF operation dispatching
- Response formatting and file serving

### PDF Processing (`utils/pdf_processor.py`)
- Text extraction using multiple libraries (pdfplumber, PyPDF2)
- Metadata extraction from PDF files
- Page splitting functionality
- PDF merging capabilities
- Safety limits for large files (1000 pages max, 1MB text limit)

### File Validation (`utils/file_validator.py`)
- Comprehensive file validation including:
  - File type validation (PDF only)
  - MIME type checking
  - PDF signature verification
  - File size limits (100 bytes minimum, 50MB maximum)
  - Filename sanitization

### Template System
- **Base Template**: Common layout with navigation and Bootstrap integration
- **Index Template**: Main upload interface with operation selection
- **Result Template**: Results display with formatted output

## Data Flow

1. **File Upload**: User selects PDF file(s) and operation type
2. **Validation**: File validator checks file integrity, type, and size
3. **Storage**: Valid files are saved to upload directory with secure filenames
4. **Processing**: PDF processor performs requested operation
5. **Results**: Processed results are displayed or offered for download
6. **Cleanup**: Temporary files are managed through client-side cleanup functionality

## External Dependencies

### Python Libraries
- **Flask**: Web framework and templating
- **PyPDF2**: PDF manipulation and text extraction
- **pdfplumber**: Advanced PDF text extraction with layout awareness
- **Werkzeug**: Security utilities for file handling

### Frontend Dependencies
- **Bootstrap 5**: UI framework (CDN)
- **Font Awesome**: Icon library (CDN)
- **Custom CSS/JS**: Application-specific styling and functionality

## Deployment Strategy

The application is configured for development and production environments:

### Development
- Debug mode enabled
- Local file storage in `uploads/` and `temp/` directories
- Environment-based configuration using `SESSION_SECRET`

### Production Considerations
- File size limits enforced at application level
- Secure filename handling
- Error logging configured
- Session management with configurable secret key

## Changelog

- July 03, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.