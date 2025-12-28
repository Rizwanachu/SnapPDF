# PDF Tools Application

## Overview

This is a Flask-based web application providing comprehensive PDF processing tools. The application features user authentication, a job queue system, and a modern Bootstrap-based UI.

## Deployment on Vercel

This project is configured for deployment on Vercel using the `@vercel/python` runtime.

### Configuration Files
- `vercel.json`: Configuration for Vercel builds and routes.
- `requirements.txt`: Python dependencies for the Vercel environment.
- `main.py`: Entry point for Vercel (exposes `app`).

### Database and Storage
- **Database**: Uses SQLite. For Vercel, the database is initialized in `/tmp/pdf_tools.db`. Note that `/tmp` is ephemeral and will be reset between function cold starts.
- **File Processing**: Background processing uses threading. On Vercel (Serverless Functions), long-running background threads may be terminated when the request ends.

### Important Notes for Vercel
- Serverless functions have execution time limits.
- The filesystem is read-only except for `/tmp`.
- For production use on Vercel, consider using an external database (PostgreSQL) and object storage (Amazon S3 or Replit Object Storage) for persistent files.

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python main.py`
