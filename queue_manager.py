import json
import logging
import threading
import time
from queue import Queue
from datetime import datetime
from app import app, db
from models import ProcessingJob, JobStatus
from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.job_queue = Queue()
        self.workers = []
        self.is_running = False
        self.max_workers = 2  # Limit concurrent processing
    
    def start(self):
        """Start the queue manager and worker threads"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"Worker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Queue manager started with {self.max_workers} workers")
    
    def stop(self):
        """Stop the queue manager"""
        self.is_running = False
        logger.info("Queue manager stopped")
    
    def add_job(self, job_id):
        """Add a job to the processing queue"""
        self.job_queue.put(job_id)
        logger.info(f"Job {job_id} added to queue")
    
    def _worker(self):
        """Worker thread function that processes jobs from the queue"""
        while self.is_running:
            try:
                job_id = self.job_queue.get(timeout=1)
                self._process_job(job_id)
                self.job_queue.task_done()
            except:
                # Timeout or other exception, continue
                continue
    
    def _process_job(self, job_id):
        """Process a single job"""
        try:
            with app.app_context():
                processor = PDFProcessor(job_id)
                processor.process_job()
                logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
    
    def get_queue_status(self):
        """Get current queue status"""
        return {
            'queue_size': self.job_queue.qsize(),
            'is_running': self.is_running,
            'worker_count': len(self.workers)
        }
    
    def get_job_status(self, job_id):
        """Get status of a specific job"""
        with app.app_context():
            job = ProcessingJob.query.get(job_id)
            if not job:
                return None
            
            return {
                'id': job.id,
                'status': job.status.value,
                'progress': job.progress,
                'total_files': job.total_files,
                'processed_files': job.processed_files,
                'error_message': job.error_message,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            }
    
    def cancel_job(self, job_id):
        """Cancel a job"""
        with app.app_context():
            job = ProcessingJob.query.get(job_id)
            if job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                db.session.commit()
                return True
            return False

# Global queue manager instance
queue_manager = QueueManager()

def start_queue_manager():
    """Start the global queue manager"""
    queue_manager.start()

def get_queue_manager():
    """Get the global queue manager instance"""
    return queue_manager
