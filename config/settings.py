"""
Application configuration settings
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
import psutil

# Load environment variables
load_dotenv()


@dataclass
class AppConfig:

    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    BACKUP_DIR: Path = DATA_DIR / "backups"
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    LOGS_DIR: Path = BASE_DIR / "logs"

    HDF5_FILE: Path = DATA_DIR / "kite_data.h5"
    HDF5_COMPRESSION: str = "blosc:lz4"  # Fast compression
    HDF5_COMPRESSION_LEVEL: int = 5  # Balanced compression level

    HDF5_CACHE_SIZE: int = 100000  # Pages (~400MB cache)
    HDF5_RDCC_NBYTES: int = 2147483648  # 2GB read cache
    HDF5_RDCC_NSLOTS: int = 200003
    HDF5_RDCC_W0: float = 0.85  # preemption
    HDF5_CHUNK_SIZE: tuple = (10000,)

    # HDF5 Driver settings
    HDF5_DRIVER: str = "sec2"
    HDF5_SIEVE_BUF_SIZE: int = 524288  # 512KB sieve buffer
    HDF5_META_BLOCK_SIZE: int = 2097152  # 2MB metadata block

    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")
    REDIRECT_URL: str = "http://127.0.0.1:8501"

    # Rate limiting
    API_RATE_LIMIT: int = 3  # Kite API hard limit
    API_TIMEOUT: int = 60  # Generous timeout
    MAX_RETRIES: int = 7  # Aggressive retry strategy
    RETRY_DELAY: int = 2  # Quick retry
    RETRY_BACKOFF: float = 1.3  # Gentler backoff

    BATCH_SIZE: int = 500
    BATCH_PAUSE_SECONDS: int = 0.5
    BATCH_MEMORY_CHECK: bool = True
    BATCH_GC_INTERVAL: int = 200

    SHOW_PROGRESS_EVERY: int = 100
    LOG_PROGRESS_EVERY: int = 500

    # Historical data
    MAX_HISTORICAL_RECORDS_PER_REQUEST: int = 1000
    HISTORICAL_DATA_CHUNK_DAYS: int = 1095

    DEFAULT_START_DATE: str = "2015-01-01"
    DEFAULT_END_DATE: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d")
    )
    DEFAULT_INTERVAL: str = "day"

    INTERVALS: list = field(
        default_factory=lambda: [
            "minute",
            "3minute",
            "5minute",
            "10minute",
            "15minute",
            "30minute",
            "60minute",
            "day",
        ]
    )

    PAGE_TITLE: str = "Kite Data Manager"
    PAGE_ICON: str = None
    LAYOUT: str = "wide"
    INITIAL_SIDEBAR_STATE: str = "expanded"

    CHUNK_SIZE: int = 50000
    MAX_WORKERS: int = 12
    CACHE_SIZE_MB: int = 6144

    USE_MULTIPROCESSING: bool = True
    MULTIPROCESSING_METHOD: str = "spawn"

    PANDAS_COMPUTE_THREADS: int = 12  # Over-provision for better scheduling
    NUMPY_THREADS: int = 12

    MAX_MEMORY_PERCENT: float = 0.87  # Use 87% of RAM

    # Memory monitoring
    ENABLE_MEMORY_MONITORING: bool = True
    MEMORY_CHECK_INTERVAL: int = 120  # Check every 2 minutes
    MEMORY_WARNING_THRESHOLD: float = 0.93
    MEMORY_CRITICAL_THRESHOLD: float = 0.97

    # Chunked processing
    USE_CHUNKED_PROCESSING: bool = True
    CHUNK_READ_SIZE: int = 500000

    USE_DASK: bool = True
    DASK_WORKERS: int = 10
    DASK_THREADS_PER_WORKER: int = 2
    DASK_MEMORY_LIMIT: str = "20GB"

    ENABLE_AGGRESSIVE_GC: bool = False
    GC_INTERVAL: int = 1000  # Very rare GC

    AUTO_BACKUP: bool = True
    BACKUP_BEFORE_FETCH: bool = True
    MAX_BACKUPS: int = 3
    BACKUP_COMPRESSION: bool = False
    BACKUP_ASYNC: bool = True
    BACKUP_WORKERS: int = 3  # Parallel backup

    STREAMLIT_CACHE_TTL: int = 7200  # 2 hours
    STREAMLIT_CACHE_MAX_ENTRIES: int = 500

    ENABLE_DATA_CACHE: bool = True
    DATA_CACHE_SIZE_MB: int = 8192
    DATA_CACHE_EVICTION: str = "LRU"

    ENABLE_QUERY_CACHE: bool = True
    QUERY_CACHE_SIZE_MB: int = 2048  # 2GB query cache

    # Enable memory mapping for large files
    ENABLE_MMAP: bool = True
    MMAP_THRESHOLD_MB: int = 100  # Use mmap for files > 100MB

    # Pre-fetch and pre-load
    ENABLE_PREFETCH: bool = True
    PREFETCH_WORKERS: int = 4

    # Parallel I/O
    ENABLE_PARALLEL_IO: bool = True
    PARALLEL_IO_WORKERS: int = 8

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Path = LOGS_DIR / "app.log"
    LOG_MAX_BYTES: int = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT: int = 10

    LOG_PERFORMANCE: bool = True
    LOG_MEMORY_USAGE: bool = True
    LOG_DETAILED_METRICS: bool = True

    def __post_init__(self):

        # Create directories
        directories = [
            self.DATA_DIR,
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
        # Thread configuration
        os.environ["OMP_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["OPENBLAS_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["MKL_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["VECLIB_MAXIMUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["NUMEXPR_NUM_THREADS"] = str(self.NUMPY_THREADS)
        os.environ["NUMBA_NUM_THREADS"] = str(self.NUMPY_THREADS)

        # Apple Accelerate framework
        os.environ["BLAS"] = "Accelerate"
        os.environ["LAPACK"] = "Accelerate"

        # Memory optimization
        os.environ["PANDAS_MEMORY_EFFICIENT"] = "0"  # Prioritize speed
        os.environ["PYTHONHASHSEED"] = "0"  # Consistent hashing

        # NumPy optimizations
        os.environ["NPY_PROMOTION_STATE"] = "weak"
        os.environ["NPY_DISABLE_OPTIMIZATION"] = "0"

        # Parallel processing
        os.environ["JOBLIB_MULTIPROCESSING"] = "1"
        os.environ["LOKY_MAX_CPU_COUNT"] = str(self.MAX_WORKERS)

    def _configure_system_limits(self):
        """Set system-level optimizations"""
        try:
            import resource

            # Increase file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (8192, 8192))
        except:
            pass

    def _log_system_info(self):
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = os.cpu_count()

    @property
    def hdf5_path(self) -> str:
        return str(self.HDF5_FILE)

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


# Global config instance
config = AppConfig()
