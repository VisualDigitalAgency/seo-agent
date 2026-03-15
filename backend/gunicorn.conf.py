"""
Gunicorn configuration for SEO Agent backend.
Optimized for FastAPI with Uvicorn workers.
"""

import os
import multiprocessing

# Bind to the port provided by the platform (Railway, Render, etc.)
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Use Uvicorn workers for async FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers: (2 * CPU cores) + 1, capped for memory constraints
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)

# Timeout for worker processes (in seconds)
# Increased for long-running pipeline operations
timeout = int(os.environ.get("WORKER_TIMEOUT", "300"))

# Keep workers alive for this many seconds after receiving SIGTERM
graceful_timeout = 120

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Access and error logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr

# Log level
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Preload the application before forking workers (reduces memory usage)
# Set to False if you have issues with database connections or similar
preload_app = False

# Worker connections (for async workers, this is the max concurrent connections)
worker_connections = 1000

# Keep-alive connections
keepalive = 5

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Gunicorn master process starting")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Gunicorn reloading workers")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Gunicorn shutting down")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("Worker received INT/QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")

def pre_request(worker, req):
    """Called just before a worker processes a request."""
    pass

def post_request(worker, req, environ, resp):
    """Called after a worker processes a request."""
    pass

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker {worker.pid} exited")
