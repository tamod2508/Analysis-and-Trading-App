"""
Runtime configuration adapter for M1 8GB
Automatically scales down M4-optimized settings when running on M1
"""

import psutil
import subprocess
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import BaseConfig


class ConfigOptimizer:
    """Adapts M4 24GB config for M1 8GB at runtime"""
    
    IMMUTABLE_SETTINGS = {
        'HDF5_COMPRESSION',
        'HDF5_COMPRESSION_LEVEL',
        'HDF5_DRIVER',
        'DEFAULT_INTERVAL',
        'REDIRECT_URL',
    }

    def __init__(self):
        self.chip = self._detect_chip()
        self.ram_gb = psutil.virtual_memory().total / (1024**3)
        self.is_m1_8gb = self._is_m1()
        self.optimizations_applied = []
        self._using_native_settings = not self.is_m1_8gb

    def _detect_chip(self) -> str:
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            chip_name = result.stdout.strip()

            if 'M4' in chip_name:
                return 'M4'
            elif 'M1' in chip_name:
                return 'M1'
            else:
                return 'Unknown'
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            # sysctl not available or failed
            return 'Unknown'
        except Exception as e:
            # Unexpected error
            return 'Unknown'

    def _is_m1(self) -> bool:
        return self.chip == 'M1' and self.ram_gb <= 10

    def optimize_config(self, config: 'BaseConfig') -> 'BaseConfig':
        """
        Optimize config for current hardware (returns modified config)

        Args:
            config: Base configuration object

        Returns:
            Optimized configuration object (same instance, modified)
        """
        if not self.is_m1_8gb:
            return config

        return self._apply_m1_settings(config)

    def _apply_m1_settings(self, config: 'BaseConfig') -> 'BaseConfig':
        
        profile = {
            'MAX_WORKERS': 6,
            'BATCH_SIZE': 150,

            'HDF5_RDCC_NBYTES': 314572800,
            'HDF5_CACHE_SIZE': 20000,
            'HDF5_RDCC_NSLOTS': 20011,
            'CACHE_SIZE_MB': 512,
            'DATA_CACHE_SIZE_MB': 768,
            'QUERY_CACHE_SIZE_MB': 256,
            'MAX_MEMORY_PERCENT': 0.75,

            'USE_DASK': False,
            'ENABLE_MMAP': True,
            'MMAP_THRESHOLD_MB': 50,
            'ENABLE_PREFETCH': True,
            'PREFETCH_WORKERS': 2,
            'BACKUP_ASYNC': False,
            'ENABLE_PARALLEL_IO': True,
            'PARALLEL_IO_WORKERS': 4,

            'ENABLE_AGGRESSIVE_GC': True,
            'GC_INTERVAL': 150,
            'BATCH_GC_INTERVAL': 50,

            'PANDAS_COMPUTE_THREADS': 6,
            'NUMPY_THREADS': 6,
            'DASK_WORKERS': 3,
            'BACKUP_WORKERS': 2,

            'BATCH_PAUSE_SECONDS': 2,
            'SHOW_PROGRESS_EVERY': 20,
            'LOG_PROGRESS_EVERY': 100,

            'MEMORY_CHECK_INTERVAL': 60,
            'MEMORY_WARNING_THRESHOLD': 0.88,
            'MEMORY_CRITICAL_THRESHOLD': 0.90,

            'STREAMLIT_CACHE_TTL': 3600,
            'STREAMLIT_CACHE_MAX_ENTRIES': 100,

            'MAX_RETRIES': 5,
            'RETRY_DELAY': 3,
            'API_TIMEOUT': 45,

            'DATA_CACHE_EVICTION': 'LRU',
            'ENABLE_DATA_CACHE': True,
            'ENABLE_QUERY_CACHE': True,
        }

        applied = 0
        skipped = []
        
        for key, value in profile.items():
            if key in self.IMMUTABLE_SETTINGS:
                skipped.append(key)
                continue
            
            if hasattr(config, key):
                original = getattr(config, key)
                setattr(config, key, value)
                
                # Track what changed
                if original != value:
                    self.optimizations_applied.append({
                        'setting': key,
                        'original': original,
                        'adapted': value
                    })
                applied += 1

        self._apply_m1_environment_optimizations()

        # Store metadata for UI
        self.applied_count = applied
        self.skipped_count = len(skipped)
        self.skipped_settings = skipped

        return config

    def _apply_m1_environment_optimizations(self):
        import os

        os.environ['OMP_NUM_THREADS'] = '6'
        os.environ['OPENBLAS_NUM_THREADS'] = '6'
        os.environ['MKL_NUM_THREADS'] = '6'
        os.environ['VECLIB_MAXIMUM_THREADS'] = '6'
        os.environ['NUMEXPR_NUM_THREADS'] = '6'
        os.environ['NUMBA_NUM_THREADS'] = '6'

        os.environ['BLAS'] = 'Accelerate'
        os.environ['LAPACK'] = 'Accelerate'

        os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
        os.environ['MALLOC_ARENA_MAX'] = '2'
        os.environ['MALLOC_MMAP_THRESHOLD_'] = '65536'

        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['PYTHONUNBUFFERED'] = '1'

        os.environ['NPY_PROMOTION_STATE'] = 'weak'
        os.environ['NPY_DISABLE_OPTIMIZATION'] = '0'

        os.environ['PANDAS_MEMORY_EFFICIENT'] = '1'

        os.environ['OMP_PROC_BIND'] = 'true'
        os.environ['OMP_PLACES'] = 'cores'
        os.environ['OMP_SCHEDULE'] = 'dynamic'

        os.environ['APPLE_SILICON_M1'] = '1'
        os.environ['APPLE_SILICON_GEN'] = '1'

    def get_info(self, config: 'BaseConfig') -> Dict[str, Any]:
        """Get system and configuration info"""
        mem = psutil.virtual_memory()

        return {
            'chip': self.chip,
            'ram_gb': round(self.ram_gb, 1),
            'ram_available_gb': round(mem.available / (1024**3), 1),
            'ram_used_gb': round(mem.used / (1024**3), 1),
            'ram_percent': round(mem.percent, 1),
            'is_travel_mode': self.is_m1_8gb,
            'max_workers': config.MAX_WORKERS,
            'batch_size': config.BATCH_SIZE,
            'cache_mb': config.CACHE_SIZE_MB,
            'hdf5_cache_mb': round(config.HDF5_RDCC_NBYTES / (1024**2)),
            'data_cache_mb': config.DATA_CACHE_SIZE_MB,
            'query_cache_mb': config.QUERY_CACHE_SIZE_MB,
            'dask_enabled': config.USE_DASK,
            'memory_limit_percent': config.MAX_MEMORY_PERCENT,
            'memory_limit_gb': round(self.ram_gb * config.MAX_MEMORY_PERCENT, 1),
            'optimization_count': len(self.optimizations_applied) if self.is_m1_8gb else 0,
            'optimizations': self.optimizations_applied if self.is_m1_8gb else [],
        }
    
    def get_detailed_info(self, config: 'BaseConfig') -> Dict[str, Any]:
        """Get detailed system and config info for UI"""
        import os

        try:
            macos_version = subprocess.run(
                ['sw_vers', '-productVersion'],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            macos_version = "Unknown"
        except Exception as e:
            macos_version = "Unknown"

        cpu_count = os.cpu_count()

        return {
            **self.get_info(config),
            'macos_version': macos_version,
            'cpu_cores': cpu_count,
            'compression': config.HDF5_COMPRESSION,
            'compression_level': config.HDF5_COMPRESSION_LEVEL,
            'api_timeout': config.API_TIMEOUT,
            'max_retries': config.MAX_RETRIES,
            'enable_mmap': config.ENABLE_MMAP,
            'enable_prefetch': config.ENABLE_PREFETCH,
            'parallel_io_workers': config.PARALLEL_IO_WORKERS,
            'gc_enabled': config.ENABLE_AGGRESSIVE_GC,
            'gc_interval': config.GC_INTERVAL,
        }


# Global optimizer instance (no longer auto-applies optimizations)
optimizer = ConfigOptimizer()


def get_system_info() -> Dict[str, Any]:
    """Get system info using global config (for backward compatibility)"""
    from .settings import config
    return optimizer.get_info(config)


def get_detailed_system_info() -> Dict[str, Any]:
    """Get detailed system info using global config (for backward compatibility)"""
    from .settings import config
    return optimizer.get_detailed_info(config)