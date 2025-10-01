"""
Application configuration settings for Kite Connect Data Manager
Optimized for Apple M1 with 8GB RAM
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psutil

# Load environment variables
load_dotenv()

@dataclass
class AppConfig:
    """Main application configuration - M1 8GB Optimized"""
    
    # ============================================================================
    # PATHS
    # ============================================================================
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    BACKUP_DIR: Path = DATA_DIR / "backups"
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # ============================================================================
    # HDF5 DATABASE SETTINGS - M1 8GB OPTIMIZED
    # ============================================================================
    HDF5_FILE: Path = DATA_DIR / "kite_data.h5"
    HDF5_COMPRESSION: str = "gzip"
    HDF5_COMPRESSION_LEVEL: int = 4  # Sweet spot for M1
    
    # HDF5 Performance (Optimized for 8GB RAM)
    HDF5_CACHE_SIZE: int = 15000  # Pages (≈60MB cache)
    HDF5_RDCC_NBYTES: int = 209715200  # 200MB read cache
    HDF5_RDCC_NSLOTS: int = 15013  # Prime number for hash slots
    HDF5_RDCC_W0: float = 0.75  # Preemption policy
    HDF5_CHUNK_SIZE: tuple = (1000,)  # Rows per chunk
    
    # HDF5 Driver settings
    HDF5_DRIVER: str = "sec2"  # Standard file driver
    HDF5_SIEVE_BUF_SIZE: int = 65536  # 64KB sieve buffer
    
    # ============================================================================
    # KITE CONNECT API SETTINGS
    # ============================================================================
    KITE_API_KEY: str = os.getenv('KITE_API_KEY', '')
    KITE_API_SECRET: str = os.getenv('KITE_API_SECRET', '')
    KITE_ACCESS_TOKEN: str = os.getenv('KITE_ACCESS_TOKEN', '')
    REDIRECT_URL: str = "http://127.0.0.1:8501"
    
    # ============================================================================
    # API RATE LIMITING & BATCH PROCESSING
    # ============================================================================
    
    # Rate limiting (FIXED by Kite API)
    API_RATE_LIMIT: int = 3  # Maximum 3 requests per second
    API_TIMEOUT: int = 30  # Timeout for each request
    MAX_RETRIES: int = 3  # Retry failed requests
    RETRY_DELAY: int = 5  # Wait 5 seconds before retry
    RETRY_BACKOFF: float = 1.5  # Exponential backoff multiplier
    
    # Batch processing (FIXED for M1 8GB)
    BATCH_SIZE: int = 150  # Optimal for M1 8GB
    BATCH_PAUSE_SECONDS: int = 2  # Pause between batches
    BATCH_MEMORY_CHECK: bool = True  # Check memory before each batch
    BATCH_GC_INTERVAL: int = 50  # Run garbage collection every 50 instruments
    
    # Progress reporting
    SHOW_PROGRESS_EVERY: int = 10  # Update UI every 10 instruments
    LOG_PROGRESS_EVERY: int = 50  # Log progress every 50 instruments
    
    # Historical data specifics
    MAX_HISTORICAL_RECORDS_PER_REQUEST: int = 1000  # Kite API limit
    HISTORICAL_DATA_CHUNK_DAYS: int = 365  # Fetch 1 year at a time
    
    # ============================================================================
    # DATA FETCHING SETTINGS
    # ============================================================================
    DEFAULT_START_DATE: str = "2020-01-01"
    DEFAULT_END_DATE: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    DEFAULT_INTERVAL: str = "day"
    
    # Use field with default_factory for mutable types
    INTERVALS: list = field(default_factory=lambda: [
        "minute", "3minute", "5minute", "10minute", "15minute",
        "30minute", "60minute", "day"
    ])
    
    # ============================================================================
    # STREAMLIT UI SETTINGS
    # ============================================================================
    PAGE_TITLE: str = "Kite Data Manager"
    PAGE_ICON: str = "📊"
    LAYOUT: str = "wide"
    INITIAL_SIDEBAR_STATE: str = "expanded"
    
    # ============================================================================
    # PERFORMANCE SETTINGS - M1 8GB OPTIMIZED
    # ============================================================================
    CHUNK_SIZE: int = 1000  # Records per chunk
    MAX_WORKERS: int = 6  # Parallel workers for M1 8GB
    CACHE_SIZE_MB: int = 384  # Memory cache
    
    # Thread settings
    USE_MULTIPROCESSING: bool = True
    MULTIPROCESSING_METHOD: str = "spawn"  # Best for macOS
    
    # Pandas/NumPy threads
    PANDAS_COMPUTE_THREADS: int = 6
    NUMPY_THREADS: int = 6
    
    # ============================================================================
    # MEMORY MANAGEMENT
    # ============================================================================
    MAX_MEMORY_PERCENT: float = 0.70  # Use 70% of RAM max
    
    # Memory monitoring
    ENABLE_MEMORY_MONITORING: bool = True
    MEMORY_CHECK_INTERVAL: int = 30  # Seconds
    MEMORY_WARNING_THRESHOLD: float = 0.85  # Warn at 85%
    MEMORY_CRITICAL_THRESHOLD: float = 0.95  # Critical at 95%
    
    # Chunked processing
    USE_CHUNKED_PROCESSING: bool = True
    CHUNK_READ_SIZE: int = 50000  # Rows
    
    # Disable Dask (too memory-hungry for 8GB)
    USE_DASK: bool = False
    
    # ============================================================================
    # GARBAGE COLLECTION
    # ============================================================================
    ENABLE_AGGRESSIVE_GC: bool = True
    GC_INTERVAL: int = 100  # Run GC every 100 operations
    
    # ============================================================================
    # BACKUP SETTINGS
    # ============================================================================
    AUTO_BACKUP: bool = True
    BACKUP_BEFORE_FETCH: bool = True
    MAX_BACKUPS: int = 5
    BACKUP_COMPRESSION: bool = True
    BACKUP_ASYNC: bool = False
    
    # ============================================================================
    # CACHING SETTINGS
    # ============================================================================
    # Streamlit caching
    STREAMLIT_CACHE_TTL: int = 1800  # 30 minutes
    STREAMLIT_CACHE_MAX_ENTRIES: int = 50
    
    # Data caching
    ENABLE_DATA_CACHE: bool = True
    DATA_CACHE_SIZE_MB: int = 256
    DATA_CACHE_EVICTION: str = "LRU"
    
    # ============================================================================
    # LOGGING SETTINGS
    # ============================================================================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE: Path = LOGS_DIR / 'app.log'
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    LOG_PERFORMANCE: bool = True
    LOG_MEMORY_USAGE: bool = True
    
    def __post_init__(self):
        """Initialize computed values and create directories"""
        
        # Create all required directories
        directories = [
            self.DATA_DIR,
            self.BACKUP_DIR,
            self.EXPORTS_DIR / "csv",
            self.EXPORTS_DIR / "reports",
            self.EXPORTS_DIR / "charts",
            self.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configure numerical libraries for M1
        self._configure_numerical_libraries()
        
        # Log system info
        self._log_system_info()
    
    def _configure_numerical_libraries(self):
        """Configure NumPy, Pandas for M1"""
        # Set thread counts
        os.environ['OMP_NUM_THREADS'] = str(self.NUMPY_THREADS)
        os.environ['OPENBLAS_NUM_THREADS'] = str(self.NUMPY_THREADS)
        os.environ['MKL_NUM_THREADS'] = str(self.NUMPY_THREADS)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(self.NUMPY_THREADS)
        os.environ['NUMEXPR_NUM_THREADS'] = str(self.NUMPY_THREADS)
        
        # Use Apple's Accelerate framework
        os.environ['BLAS'] = 'Accelerate'
        os.environ['LAPACK'] = 'Accelerate'
        
        # Pandas memory optimization
        os.environ['PANDAS_MEMORY_EFFICIENT'] = '1'
    
    def _log_system_info(self):
        """Log system information on startup"""
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = os.cpu_count()
        
        print("=" * 60)
        print("🚀 Kite Data Manager - System Information")
        print("=" * 60)
        print(f"Architecture: Apple M1")
        print(f"CPU Cores: {cpu_count}")
        print(f"Total RAM: {ram_gb:.1f} GB")
        print(f"Available RAM: {psutil.virtual_memory().available / (1024**3):.1f} GB")
        print(f"Configuration: Optimized for M1 8GB")
        print(f"Max Workers: {self.MAX_WORKERS}")
        print(f"Batch Size: {self.BATCH_SIZE}")
        print(f"HDF5 Cache: {self.HDF5_RDCC_NBYTES / (1024**2):.0f} MB")
        print(f"Data Cache: {self.CACHE_SIZE_MB} MB")
        print("=" * 60)
    
    @property
    def hdf5_path(self) -> str:
        """Get HDF5 database path as string"""
        return str(self.HDF5_FILE)
    
    @property
    def is_configured(self) -> bool:
        """Check if API credentials are configured"""
        return bool(self.KITE_API_KEY and self.KITE_API_SECRET)
    
    @property
    def available_memory_mb(self) -> float:
        """Get currently available memory in MB"""
        return psutil.virtual_memory().available / (1024**2)
    
    @property
    def memory_usage_percent(self) -> float:
        """Get current memory usage percentage"""
        return psutil.virtual_memory().percent
    
    def check_memory_available(self, required_mb: int) -> bool:
        """Check if enough memory is available for operation"""
        return self.available_memory_mb >= required_mb
    
    def get_backup_path(self, timestamp: str = None) -> Path:
        """Generate backup file path with timestamp"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.BACKUP_DIR / f"kite_data_backup_{timestamp}.h5"
    
    def get_hdf5_options(self) -> dict:
        """Get HDF5 file opening options"""
        return {
            'rdcc_nbytes': self.HDF5_RDCC_NBYTES,
            'rdcc_nslots': self.HDF5_RDCC_NSLOTS,
            'rdcc_w0': self.HDF5_RDCC_W0,
            'driver': self.HDF5_DRIVER,
        }

# Global config instance
config = AppConfig()