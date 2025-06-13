import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
# In Cloud Run, we'll log to console only
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None
if IS_CLOUD_RUN:
    LOG_DIR = "/tmp/logs"  # Use /tmp in Cloud Run
else:
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    # If we can't create directory, use /tmp
    LOG_DIR = "/tmp"

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "backend_server.log")

class LineCountRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler that rotates based on line count"""
    
    def __init__(self, filename, max_lines=200, backupCount=5, *args, **kwargs):
        self.max_lines = max_lines
        self.line_count = 0
        # Set backup count for rotation
        kwargs['backupCount'] = backupCount
        # Remove existing log files for fresh start
        if os.path.exists(filename):
            os.remove(filename)
        # Remove existing backup files
        for i in range(1, backupCount + 1):
            backup_file = self.rotation_filename(filename + f".{i}")
            if os.path.exists(backup_file):
                os.remove(backup_file)
        super().__init__(filename, maxBytes=0, *args, **kwargs)
        # Set custom namer and rotator
        self.namer = self.custom_namer
        self.rotator = self.custom_rotator
        
    def custom_namer(self, default_name):
        """Custom namer to change log.1 to log_1.log format"""
        # default_name is like 'backend_server.log.1'
        if default_name.endswith('.log'):
            return default_name
        
        parts = default_name.split('.')
        if len(parts) >= 3 and parts[-2] == 'log':
            # backend_server.log.1 -> backend_server_1.log
            number = parts[-1]
            base_name = '.'.join(parts[:-2])  # backend_server
            return f"{base_name}_{number}.log"
        return default_name
    
    def custom_rotator(self, source, dest):
        """Custom rotator to handle the new naming scheme"""
        # Convert dest name using our custom namer
        dest = self.custom_namer(dest)
        if os.path.exists(source):
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(source, dest)
        
    def emit(self, record):
        """Emit a record, checking line count"""
        super().emit(record)
        self.line_count += 1
        
        if self.line_count >= self.max_lines:
            self.doRollover()
            
    def doRollover(self):
        """Do a rollover - rotate to backup files"""
        self.stream.close()
        self.stream = None
        # Rotate the files
        super().doRollover()
        self.line_count = 0
        self.stream = self._open()
        
    def rotation_filename(self, default_name):
        """Helper method to get rotation filename"""
        return self.custom_namer(default_name)

class PrintToLoggerInterceptor:
    """Intercepts print statements and redirects them to logger"""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self.buffer = []
        
    def write(self, message):
        # Skip empty messages and newlines
        if message.strip():
            self.logger.log(self.level, message.strip())
            
    def flush(self):
        pass

def reset_log_file():
    """Reset the log file - used when simulation is reset"""
    # Close all file handlers first
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
    
    # Remove main log file
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
        except Exception as e:
            logging.error(f"Error removing log file: {e}")
    
    # Remove backup log files with new naming scheme
    for i in range(1, 6):  # Remove up to 5 backup files
        # Extract base name without extension
        base_name = LOG_FILE.rsplit('.', 1)[0]  # backend_server
        backup_file = f"{base_name}_{i}.log"
        if os.path.exists(backup_file):
            try:
                os.remove(backup_file)
            except Exception as e:
                logging.error(f"Error removing backup file {backup_file}: {e}")
    
    # Re-setup logging
    setup_logging()
    logging.info("Log file reset due to simulation reset")

def setup_logging():
    """Configure logging for the backend server"""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    handlers = [console_handler]
    
    # Only add file handler if not in Cloud Run
    if not IS_CLOUD_RUN:
        try:
            # Create file handler with line count rotation
            file_handler = LineCountRotatingFileHandler(
                LOG_FILE,
                max_lines=200,
                backupCount=5  # Keep 5 backup files
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)  # DEBUG -> INFO로 변경
            handlers.append(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # DEBUG -> INFO로 변경하여 불필요한 로그 제거
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure uvicorn access logs to also go to our file
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers = []
    for handler in handlers:
        uvicorn_logger.addHandler(handler)
    
    # Configure uvicorn error logs
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = []
    for handler in handlers:
        uvicorn_error_logger.addHandler(handler)
    
    # Configure app loggers
    app_loggers = [
        "app.simulation_engine",
        "app.simulation_engine_v2",
        "app.core.entity_manager",
        "app.core.signal_manager",
        "app.core.pipe_manager",
        "app.core.source_manager",
        "app.core.action_executor",
        "app.core.block_processor"
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)  # DEBUG -> INFO로 변경
        logger.handlers = []
        for handler in handlers:
            logger.addHandler(handler)
        logger.propagate = False  # Prevent duplicate logs
    
    # Intercept print statements and redirect to logger
    import sys
    print_logger = logging.getLogger("console.print")
    print_logger.setLevel(logging.INFO)
    sys.stdout = PrintToLoggerInterceptor(print_logger, logging.INFO)
    
    # Log startup message
    logging.info(f"=" * 80)
    logging.info(f"Backend server started at {datetime.now()}")
    logging.info(f"Log file: {LOG_FILE}")
    logging.info(f"Maximum lines: 200 per file, 5 backup files")
    logging.info(f"=" * 80)