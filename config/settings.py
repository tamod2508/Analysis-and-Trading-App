"""
Application configuration settings
"""

import os
import logging
import logging.config
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
import psutil
from .constants import Interval, HDF5_STORAGE_CHUNKS, CompressionType

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger(__name__)


def configure_logging_from_yaml(config_path: Path = None) -> bool:
    """
    Configure logging from YAML file

    Args:
        config_path: Path to logging config YAML file. If None, uses default.

    Returns:
        bool: True if loaded successfully, False otherwise
    """
    if config_path is None:
        config_path = Path(__file__).parent / "logging_config.yaml"

    if not config_path.exists():
        logger.warning(f"Logging config file not found: {config_path}")
        return False

    try:
        import yaml
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        logging.config.dictConfig(config_dict)
        logger.info(f"Logging configured from: {config_path}")
        return True
    except ImportError:
        logger.warning("PyYAML not installed. Using default logging configuration.")
        return False
    except Exception as e:
        logger.error(f"Error loading logging config: {e}")
        return False


@dataclass
class BaseConfig:
    """Base configuration shared across all environments"""

    # Directory paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    BACKUP_DIR: Path = DATA_DIR / "backups"
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # HDF5 settings
    HDF5_DIR: Path = DATA_DIR / "hdf5"
    HDF5_FILE_PATTERN: str = "{segment}.h5"
    HDF5_COMPRESSION: str = CompressionType.BLOSC_LZ4.value
    HDF5_COMPRESSION_LEVEL: int = 5
    HDF5_CACHE_SIZE: int = 100000
    HDF5_RDCC_NSLOTS: int = 200003
    HDF5_RDCC_W0: float = 0.85
    HDF5_DRIVER: str = "sec2"
    HDF5_SIEVE_BUF_SIZE: int = 524288
    HDF5_META_BLOCK_SIZE: int = 2097152

    # Kite API credentials
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")
    REDIRECT_URL: str = "http://127.0.0.1:8501"

    # Rate limiting (common across environments)
    # As per Kite Connect API documentation: 3 requests per second
    KITE_API_RATE_LIMIT_PER_SECOND: int = 3
    # Safety margin of 50ms between requests to avoid rate limit
    API_RATE_SAFETY_MARGIN_SECONDS: float = 0.05
    # API request timeout in seconds
    API_TIMEOUT_SECONDS: int = 60
    # Initial retry delay in seconds
    RETRY_DELAY_SECONDS: int = 2
    # Exponential backoff multiplier (1.3x per retry)
    RETRY_BACKOFF_MULTIPLIER: float = 1.3

    # Backward compatibility aliases
    API_RATE_LIMIT: int = KITE_API_RATE_LIMIT_PER_SECOND
    API_RATE_SAFETY_MARGIN: float = API_RATE_SAFETY_MARGIN_SECONDS
    API_TIMEOUT: int = API_TIMEOUT_SECONDS
    RETRY_DELAY: int = RETRY_DELAY_SECONDS
    RETRY_BACKOFF: float = RETRY_BACKOFF_MULTIPLIER

    # Batch processing
    BATCH_SIZE: int = 500
    BATCH_PAUSE_SECONDS: int = 0.5
    BATCH_MEMORY_CHECK: bool = True
    BATCH_GC_INTERVAL: int = 200

    # Progress reporting
    SHOW_PROGRESS_EVERY: int = 100
    LOG_PROGRESS_EVERY: int = 500

    # Historical data
    MAX_HISTORICAL_RECORDS_PER_REQUEST: int = 1000

    # API Fetch Chunks (in days)
    # When fetching large date ranges, split into chunks to avoid timeouts.
    # Larger values = fewer API calls but higher memory usage
    # Smaller values = more API calls but lower memory usage
    API_FETCH_CHUNK_DAYS: int = 1095  # ~3 years per chunk

    # DEPRECATED: Use API_FETCH_CHUNK_DAYS instead
    HISTORICAL_DATA_CHUNK_DAYS: int = API_FETCH_CHUNK_DAYS  # Backward compatibility
    DEFAULT_START_DATE: str = "2015-01-01"
    DEFAULT_END_DATE: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )
    DEFAULT_INTERVAL: str = "day"
    INTERVALS: list = field(
        default_factory=lambda: [
            "minute", "3minute", "5minute", "10minute",
            "15minute", "30minute", "60minute", "day",
        ]
    )

    # UI settings
    PAGE_TITLE: str = "Kite Data Manager"
    PAGE_ICON: str = None
    LAYOUT: str = "wide"
    INITIAL_SIDEBAR_STATE: str = "expanded"

    # Processing settings
    USE_MULTIPROCESSING: bool = True
    MULTIPROCESSING_METHOD: str = "spawn"  # Use 'spawn' for clean process state
    MAX_MEMORY_PERCENT: float = 0.87  # Use up to 87% of RAM before pausing

    # Memory monitoring
    MEMORY_CHECK_INTERVAL: int = 120  # Check memory every 120 seconds
    MEMORY_WARNING_THRESHOLD: float = 0.93  # Warn at 93% memory usage
    MEMORY_CRITICAL_THRESHOLD: float = 0.97  # Critical alert at 97% memory usage

    # Chunked processing
    USE_CHUNKED_PROCESSING: bool = True

    # Dask settings
    USE_DASK: bool = True
    DASK_WORKERS: int = 10
    DASK_THREADS_PER_WORKER: int = 2
    DASK_MEMORY_LIMIT: str = "20GB"

    # Garbage collection
    ENABLE_AGGRESSIVE_GC: bool = False
    GC_INTERVAL: int = 1000

    # Backup settings
    BACKUP_BEFORE_FETCH: bool = True
    MAX_BACKUPS: int = 3
    BACKUP_COMPRESSION: bool = False
    BACKUP_ASYNC: bool = True
    BACKUP_WORKERS: int = 3

    # Streamlit caching
    STREAMLIT_CACHE_TTL: int = 7200
    STREAMLIT_CACHE_MAX_ENTRIES: int = 500

    # Data caching
    ENABLE_DATA_CACHE: bool = True
    DATA_CACHE_SIZE_MB: int = 8192
    DATA_CACHE_EVICTION: str = "LRU"
    ENABLE_QUERY_CACHE: bool = True
    QUERY_CACHE_SIZE_MB: int = 2048

    # Memory mapping
    ENABLE_MMAP: bool = True
    MMAP_THRESHOLD_MB: int = 100

    # Pre-fetch
    ENABLE_PREFETCH: bool = True
    PREFETCH_WORKERS: int = 4

    # Parallel I/O
    ENABLE_PARALLEL_IO: bool = True
    PARALLEL_IO_WORKERS: int = 8

    # Logging
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Path = LOGS_DIR / "app.log"
    LOG_MAX_BYTES: int = 100 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 10

    # Environment-specific settings (to be overridden)
    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 7
    MAX_WORKERS: int = 12
    CACHE_SIZE_MB: int = 6144
    PANDAS_COMPUTE_THREADS: int = 12
    NUMPY_THREADS: int = 12
    HDF5_RDCC_NBYTES: int = 2147483648
    ENABLE_MEMORY_MONITORING: bool = True
    AUTO_BACKUP: bool = True
    LOG_PERFORMANCE: bool = True
    LOG_MEMORY_USAGE: bool = True
    LOG_DETAILED_METRICS: bool = True

    def __post_init__(self):

        # Create directories
        directories = [
            self.DATA_DIR,
            self.HDF5_DIR,
            self.BACKUP_DIR,
            self.EXPORTS_DIR / "csv",
            self.EXPORTS_DIR / "reports",
            self.EXPORTS_DIR / "charts",
            self.LOGS_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        self._configure_numerical_libraries()
        self._configure_system_limits()
        self._log_system_info()

    def _configure_numerical_libraries(self):
        """Configure numerical libraries with auto-detected optimal thread counts"""
        import platform

        # Auto-detect optimal thread count (use 75% of CPU cores, leave some for system)
        cpu_count = os.cpu_count() or 1
        optimal_threads = max(1, int(cpu_count * 0.75))

        # Override instance attributes with detected values if they're at default
        # This ensures auto-detection works while allowing manual override
        if self.NUMPY_THREADS == 12:  # Default value
            self.NUMPY_THREADS = optimal_threads
        if self.PANDAS_COMPUTE_THREADS == 12:
            self.PANDAS_COMPUTE_THREADS = optimal_threads
        if self.MAX_WORKERS == 12:
            self.MAX_WORKERS = optimal_threads

        # Thread configuration for numerical libraries
        os.environ["OMP_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["OPENBLAS_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["MKL_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["VECLIB_MAXIMUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["NUMEXPR_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["NUMBA_NUM_THREADS"] = str(self.NUMPY_THREADS)

        # Detect BLAS/LAPACK backend based on platform
        system = platform.system()
        if system == "Darwin":  # macOS
            os.environ["BLAS"] = "Accelerate"
            os.environ["LAPACK"] = "Accelerate"
            logger.info(f"Using Apple Accelerate framework (macOS)")
        elif system == "Linux":
            # Prefer MKL if available, otherwise OpenBLAS
            os.environ["BLAS"] = "openblas"
            os.environ["LAPACK"] = "openblas"
            logger.info(f"Using OpenBLAS (Linux)")
        elif system == "Windows":
            # Windows typically uses MKL with NumPy
            logger.info(f"Using default BLAS/LAPACK (Windows)")

        # Memory optimization
        os.environ["PANDAS_MEMORY_EFFICIENT"] = "0"  # Prioritize speed
        os.environ["PYTHONHASHSEED"] = "0"  # Consistent hashing

        # NumPy optimizations
        os.environ["NPY_PROMOTION_STATE"] = "weak"
        os.environ["NPY_DISABLE_OPTIMIZATION"] = "0"

        # Parallel processing
        os.environ["JOBLIB_MULTIPROCESSING"] = "1"
        os.environ["LOKY_MAX_CPU_COUNT"] = str(self.MAX_WORKERS)

        logger.info(f"Thread configuration: {self.NUMPY_THREADS} threads (CPU cores: {cpu_count})")

    def _configure_system_limits(self):
        """Set system-level optimizations"""
        try:
            import resource

            # Increase file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (8192, 8192))
            logger.info("File descriptor limit increased to 8192")
        except (ImportError, ValueError, OSError) as e:
            # resource module not available on Windows, or permission denied
            logger.debug(f"Could not set system limits: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error setting system limits: {e}")

    def _log_system_info(self):
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = os.cpu_count()

    @property
    def is_configured(self) -> bool:
        return bool(self.KITE_API_KEY and self.KITE_API_SECRET)

    @property
    def available_memory_mb(self) -> float:
        return psutil.virtual_memory().available / (1024**2)

    @property
    def memory_usage_percent(self) -> float:
        return psutil.virtual_memory().percent

    def check_memory_available(self, required_mb: int) -> bool:
        return self.available_memory_mb >= required_mb

    def get_backup_path(self, timestamp: str = None) -> Path:
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.BACKUP_DIR / f"kite_data_backup_{timestamp}.h5"

    def get_hdf5_options(self) -> dict:
        return {
            "rdcc_nbytes": self.HDF5_RDCC_NBYTES,
            "rdcc_nslots": self.HDF5_RDCC_NSLOTS,
            "rdcc_w0": self.HDF5_RDCC_W0,
            "driver": self.HDF5_DRIVER,
            "meta_block_size": self.HDF5_META_BLOCK_SIZE,
        }
    def get_hdf5_path(self, segment: str) -> Path:
        """Get HDF5 file path for specific segment"""
        filename = self.HDF5_FILE_PATTERN.format(segment=segment)
        return self.HDF5_DIR / filename

    @property
    def hdf5_path(self) -> str:
        """Default equity database path"""
        return str(self.get_hdf5_path('EQUITY'))

    def get_hdf5_creation_settings(self, interval: str, data_size: int = None) -> dict:
        """
        Get HDF5 dataset creation settings for specific interval

        Args:
            interval: Data interval (day, 5minute, etc.)
            data_size: Optional. Size of data to determine chunk size

        Returns:
            Dict with compression, chunks, shuffle for h5py.create_dataset()
        """

        # Convert string to Interval enum if needed
        if isinstance(interval, str):
            try:
                interval_enum = Interval(interval)
            except ValueError:
                interval_enum = Interval.DAY  # Default
        else:
            interval_enum = interval

        # Get HDF5 storage chunk size for this interval
        default_chunk_size = HDF5_STORAGE_CHUNKS.get(interval_enum, 1000)

        if data_size is not None:
            # Don't make chunks bigger than data
            # Allow minimum of 1 for single-record datasets (e.g., testing)
            chunk_size = min(default_chunk_size, max(1, data_size))
        else:
            chunk_size = default_chunk_size

        return {
            'compression': self.HDF5_COMPRESSION,
            'compression_opts': self.HDF5_COMPRESSION_LEVEL,
            'shuffle': True,  # Always use shuffle for better compression
            'chunks': (chunk_size,)
        }


@dataclass
class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    LOG_LEVEL: str = "DEBUG"
    MAX_RETRIES: int = 3
    HDF5_RDCC_NBYTES: int = 314572800  # 300MB cache (smaller for dev)
    ENABLE_MEMORY_MONITORING: bool = False
    AUTO_BACKUP: bool = True
    LOG_PERFORMANCE: bool = False
    LOG_MEMORY_USAGE: bool = False
    LOG_DETAILED_METRICS: bool = False


@dataclass
class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 7
    HDF5_RDCC_NBYTES: int = 2147483648  # 2GB cache (full size for prod)
    ENABLE_MEMORY_MONITORING: bool = True
    AUTO_BACKUP: bool = True
    LOG_PERFORMANCE: bool = True
    LOG_MEMORY_USAGE: bool = True
    LOG_DETAILED_METRICS: bool = True


@dataclass
class TestingConfig(BaseConfig):
    """Testing environment configuration"""
    LOG_LEVEL: str = "WARNING"
    MAX_RETRIES: int = 3
    HDF5_RDCC_NBYTES: int = 104857600  # 100MB cache (minimal for testing)
    ENABLE_MEMORY_MONITORING: bool = False
    AUTO_BACKUP: bool = False  # No auto-backup in tests
    LOG_PERFORMANCE: bool = False
    LOG_MEMORY_USAGE: bool = False
    LOG_DETAILED_METRICS: bool = False
    STREAMLIT_CACHE_TTL: int = 0  # No caching in tests


# Auto-select configuration based on environment
ENV = os.getenv("KITE_ENV", "development").lower()

if ENV == "production":
    base_config = ProductionConfig()
elif ENV == "testing" or ENV == "test":
    base_config = TestingConfig()
else:
    base_config = DevelopmentConfig()

# Apply hardware-specific optimizations (M1 8GB adjustments)
from .optimizer import optimizer
config = optimizer.optimize_config(base_config)

# Backward compatibility alias
AppConfig = type(config)
