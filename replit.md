# SnapPDF - Production Deployment Guide

## Overview
SnapPDF is a comprehensive Flask-based PDF processing platform with user authentication, job queue system, premium subscriptions, and 29 PDF manipulation tools.

**Status**: Ready for Vercel deployment with PostgreSQL support

## Deployment on Vercel

### Configuration Files
- `vercel.json`: Vercel build and routing configuration
- `requirements.txt`: Python dependencies
- `.env.example`: Required environment variables template
- `main.py`: Application entry point (exports `app`)

### Database & Persistence
- **Production (Vercel)**: PostgreSQL via `DATABASE_URL` environment variable
- **Local Development**: SQLite in `/tmp/pdf_tools.db`
- **Tables Created Automatically**: SQLAlchemy creates all tables on startup
- **Connection Pooling**: Configured for serverless environment (pool_recycle=300, pool_pre_ping=True)

### File Storage
- **Upload Directory**: `/tmp/uploads` - temporary storage for user uploads
- **Processed Directory**: `/tmp/processed` - temporary storage for processed files
- **Temp Directory**: `/tmp/temp` - temporary working directory
- **Note**: Vercel filesystem is ephemeral except `/tmp` is write-enabled per function invocation
- **For Production**: Consider implementing external storage (AWS S3, Replit Object Storage)

### Environment Variables Required
```
DATABASE_URL=postgresql://...        # Production only
SESSION_SECRET=<strong-random-key>    # MUST change from default
PAYPAL_CLIENT_ID=<optional>
PAYPAL_CLIENT_SECRET=<optional>
```

See `.env.example` for all available options.

## Features

### Authentication & User Management
- User registration with email validation
- Secure login/logout with Flask-Login
- Password hashing using Werkzeug
- User profiles with premium tier tracking

### PDF Processing Tools (29 tools)
- **Organize**: Merge, Split, Extract Images, Remove Pages, Extract Pages, Organize
- **Optimize**: Compress, Repair, OCR
- **Convert to PDF**: JPG, Word, PowerPoint, Excel, HTML
- **Convert from PDF**: JPG, Word, PowerPoint, Excel, PDF/A
- **Edit**: Rotate, Add Page Numbers, Watermark, Crop, Edit
- **Security**: Unlock, Protect, Sign, Redact, Compare

### Job Queue System
- Background processing with threading (2 workers)
- Job status tracking (Pending → Processing → Completed/Failed/Cancelled)
- Progress monitoring (0-100%)
- Job history and real-time updates

### Premium Subscription
- Tier enforcement (free vs premium limits)
- Free users: 3 files per batch, 5MB file size limit
- Premium users: 100 files per batch, 100MB file size limit
- $4.99/month subscription with 30-day auto-renewal
- Subscription management (activate/cancel)

### File Processing
- Multi-file batch uploads with validation
- File preview generation (first page as PNG)
- Detailed metadata extraction
- ZIP download for multiple files
- Secure filename generation and cleanup

## Local Development

### Setup
```bash
pip install -r requirements.txt
```

### Run
```bash
python main.py
```

Or with Gunicorn:
```bash
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

### Environment (local)
- Uses SQLite by default
- No DATABASE_URL needed
- Set SESSION_SECRET for security

## Production Deployment (Vercel)

### Prerequisites
1. Create PostgreSQL database (Neon, AWS RDS, etc.)
2. Get DATABASE_URL connection string
3. Generate strong SESSION_SECRET

### Deploy
```bash
vercel deploy
```

### Configure Environment Variables on Vercel
Set these in Vercel project settings:
- `DATABASE_URL` (PostgreSQL)
- `SESSION_SECRET` (strong random string)
- Optional: `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`

### Post-Deployment
- Database tables are created automatically on first request
- All routes work with URL refresh (vercel.json configured)
- File uploads/downloads work via `/tmp` directory
- Job queue processes in background

## Architecture

### Tech Stack
- **Framework**: Flask 3.1.2
- **Database ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL (production), SQLite (local)
- **Authentication**: Flask-Login + Werkzeug security
- **Forms**: Flask-WTF + WTForms
- **PDF Processing**: PyMuPDF, PyPDF2, reportlab
- **File Upload**: Werkzeug file utilities
- **Job Queue**: Threading-based with progress tracking

### Key Files
- `app.py` - Flask app initialization, database config, directory setup
- `main.py` - Entry point for Vercel
- `models.py` - Database models (User, ProcessingJob, FileUpload, Subscription)
- `routes.py` - All HTTP endpoints
- `forms.py` - Registration and login forms
- `queue_manager.py` - Background job processing
- `pdf_processor.py` - PDF conversion logic
- `utils.py` - Helper functions (file validation, cleanup, formatting)

### Database Models
- **User**: User accounts, authentication, premium status
- **ProcessingJob**: Job tracking (status, progress, input/output files)
- **FileUpload**: Uploaded file metadata
- **Subscription**: Premium subscriptions with expiry
- **OAuth**: OAuth provider integration (if enabled)

## Security

### Implemented
- Password hashing with Werkzeug (using default bcrypt)
- CSRF protection via Flask-WTF
- Email validation on registration
- File type validation (PDF, JPG, DOCX, PPTX, XLSX, HTML only)
- Path traversal prevention with secure_filename
- File size limits enforcement
- Database query parameterization (SQLAlchemy)
- Session security with SECRET_KEY

### Recommendations for Production
- Use HTTPS only (Vercel provides automatically)
- Rotate SESSION_SECRET regularly
- Monitor job queue for stuck jobs
- Implement rate limiting on uploads/processing
- Add request logging and monitoring
- Regular database backups
- Consider CDN for static files

## Monitoring & Troubleshooting

### Local Testing
```bash
# Check database connection
python -c "from app import db, app; print(app.config['SQLALCHEMY_DATABASE_URI'])"

# View logs
tail -f logs/app.log
```

### Vercel Logs
```bash
vercel logs
```

### Common Issues
1. **Database Connection**: Ensure DATABASE_URL is set and PostgreSQL is accessible
2. **Cold Starts**: Database connections reset between requests; pool_pre_ping handles this
3. **File Storage**: Use `/tmp` but remember ephemeral; implement S3/Object Storage for permanent files
4. **Job Queue**: Threading works but not ideal for serverless; consider external queue service for scale

## Future Improvements
- Move to external job queue (Redis, Celery) for serverless
- Implement S3/Object Storage for permanent file persistence
- Add request rate limiting
- Implement API rate limiting with JWT
- Add email notifications for job completion
- Implement webhook notifications
- Add support for more file formats
- Implement real-time progress updates via WebSockets

## Support & Debugging
- Enable Flask debug logging: `app.logger.setLevel(logging.DEBUG)`
- Check `/tmp` for upload/processed file storage
- Monitor job queue status via `/api/queue/status` endpoint
- Review database tables with: `SELECT * FROM processing_jobs;`

---
**Last Updated**: December 29, 2025
**Version**: 1.0.0 Production-Ready
