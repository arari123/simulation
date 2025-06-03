import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "backend_server.log")

class LineCountRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler that rotates based on line count"""
    
    def __init__(self, filename, max_lines=200, *args, **kwargs):
        self.max_lines = max_lines
        self.line_count = 0
        # Remove the log file if it exists (fresh start)
        if os.path.exists(filename):
            os.remove(filename)
        super().__init__(filename, *args, **kwargs)
        
    def emit(self, record):
        """Emit a record, checking line count"""
        super().emit(record)
        self.line_count += 1
        
        if self.line_count >= self.max_lines:
            self.doRollover()
            
    def doRollover(self):
        """Do a rollover - in our case, truncate the file"""
        self.stream.close()
        # Truncate the file to keep only the last 100 lines (half of max_lines)
        with open(self.baseFilename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(self.baseFilename, 'w', encoding='utf-8') as f:
            # Keep the last half of max_lines
            f.writelines(lines[-(self.max_lines//2):])
        self.line_count = self.max_lines // 2
        self.stream = self._open()

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
    if os.path.exists(LOG_FILE):
        # Close all file handlers first
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)
        
        # Remove the log file
        try:
            os.remove(LOG_FILE)
        except Exception as e:
            logging.error(f"Error removing log file: {e}")
    
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
    
    # Create file handler with line count rotation
    file_handler = LineCountRotatingFileHandler(
        LOG_FILE,
        max_lines=200,
        maxBytes=0,  # Disable size-based rotation
        backupCount=0  # No backup files
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure uvicorn access logs to also go to our file
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers = []
    uvicorn_logger.addHandler(file_handler)
    uvicorn_logger.addHandler(console_handler)
    
    # Configure uvicorn error logs
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = []
    uvicorn_error_logger.addHandler(file_handler)
    uvicorn_error_logger.addHandler(console_handler)
    
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
        logger.setLevel(logging.DEBUG)
        logger.handlers = []
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
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
    logging.info(f"Maximum lines: 200 (auto-rotation enabled)")
    logging.info(f"=" * 80)