"""
Maximum performance for 24GB RAM
"""

import os
import psutil
import subprocess
import platform
from typing import Dict, Any, Optional
from config.settings import config

class AppleSiliconOptimizer:
    """OPtimizer to detect apple core and settings and optimize"""
    def __init__(self):
        self.is_apple_silicon = self._detect_apple_silicon()
        self.chip_generation = self._detect_chip_generation()
        self.cpu_count = os.cpu_count() or 10
        self.performance_cores = self._get_performance_cores()
        self.efficiency_cores = self._get_efficiency_cores()
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        self.is_extreme_mode = self.memory_gb >= 24 and self.is_apple_silicon
        
    def _detect_apple_silicon(self) -> bool:
        """Detect Apple Silicon architecture"""
        try:
            result = subprocess.run(
                ['uname', '-m'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return result.stdout.strip() == 'arm64'
        except Exception:
            return platform.machine() == 'arm64'
    
    def _detect_chip_generation(self) -> str:
        """Detect specific Apple Silicon chip (M1/M2/M3/M4)"""
        if not self.is_apple_silicon:
            return "Not Apple Silicon"
        
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            chip_name = result.stdout.strip()
            
            if 'M4' in chip_name:
                return "M4"
            elif 'M3' in chip_name:
                return "M3"
            elif 'M2' in chip_name:
                return "M2"
            elif 'M1' in chip_name:
                return "M1"
            else:
                return "Apple Silicon (Unknown)"
        except Exception:
            return "Apple Silicon"
    
    def _get_performance_cores(self) -> int:
        if self.chip_generation == "M4":
            return 4
        elif self.chip_generation == "M3":
            return 4
        elif self.chip_generation == "M2":
            return 4
        else:
            return self.cpu_count // 2
    
    def _get_efficiency_cores(self) -> int:
        if self.chip_generation == "M4":
            return 6
        elif self.chip_generation == "M3":
            return 4
        elif self.chip_generation == "M2":
            return 4
        else:
            return self.cpu_count // 2
    
    def get_optimal_settings(self) -> Dict[str, Any]:
        chip_multipliers = {
            "M4": 1.3, 
            "M3": 1.2,
            "M2": 1.1,
            "M1": 1.0,
        }
        
        multiplier = chip_multipliers.get(self.chip_generation, 1.0)
        
        available_ram_gb = self.memory_gb
        usable_ram_gb = available_ram_gb * config.MAX_MEMORY_PERCENT
        
        settings = {
            'max_workers': config.MAX_WORKERS,
            'chunk_size': config.CHUNK_SIZE,
            'batch_size': config.BATCH_SIZE,
            'memory_limit_mb': int(usable_ram_gb * 1024),
            
            'chip_generation': self.chip_generation,
            'chip_multiplier': multiplier,
            'use_high_performance_cores': True,
            'performance_cores': self.performance_cores,
            'efficiency_cores': self.efficiency_cores,
            
            'cache_size': config.HDF5_CACHE_SIZE,
            'hdf5_cache_mb': config.HDF5_RDCC_NBYTES / (1024**2),
            'data_cache_gb': config.CACHE_SIZE_MB / 1024,
            'query_cache_gb': config.QUERY_CACHE_SIZE_MB / 1024 if hasattr(config, 'QUERY_CACHE_SIZE_MB') else 2,
            
            'total_ram_gb': available_ram_gb,
            'usable_ram_gb': usable_ram_gb,
            'memory_percent_used': config.MAX_MEMORY_PERCENT * 100,
            
            'temp_store': 'MEMORY',
            'use_mmap': config.ENABLE_MMAP if hasattr(config, 'ENABLE_MMAP') else True,
            'parallel_io': config.ENABLE_PARALLEL_IO if hasattr(config, 'ENABLE_PARALLEL_IO') else True,
            
            'extreme_mode': self.is_extreme_mode,
            'turbo_mode': config.TURBO_MODE if hasattr(config, 'TURBO_MODE') else True,
            'fast_mode': config.FAST_MODE if hasattr(config, 'FAST_MODE') else True,
        }
        
        return settings
    
    def configure_environment(self):    
        if not self.is_apple_silicon:
            return
        
        thread_count = str(self.cpu_count)
        os.environ['OPENBLAS_NUM_THREADS'] = thread_count
        os.environ['MKL_NUM_THREADS'] = thread_count
        os.environ['VECLIB_MAXIMUM_THREADS'] = thread_count
        os.environ['NUMEXPR_NUM_THREADS'] = thread_count
        os.environ['OMP_NUM_THREADS'] = thread_count
        os.environ['NUMBA_NUM_THREADS'] = thread_count

        os.environ['BLAS'] = 'Accelerate'
        os.environ['LAPACK'] = 'Accelerate'
        
        os.environ['OMP_PROC_BIND'] = 'true'
        os.environ['OMP_PLACES'] = 'cores'
        os.environ['OMP_SCHEDULE'] = 'dynamic'
        
        os.environ['MALLOC_ARENA_MAX'] = '4'
        os.environ['MALLOC_MMAP_THRESHOLD_'] = '131072'
        os.environ['MALLOC_TRIM_THRESHOLD_'] = '131072'
        
        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        if self.chip_generation == "M4":
            os.environ['M4_OPTIMIZED'] = '1'
            os.environ['APPLE_SILICON_GEN'] = '4'
    
    def get_system_info(self) -> Dict[str, Any]:
        
        try:
            macos_version = subprocess.run(
                ['sw_vers', '-productVersion'], 
                capture_output=True, 
                text=True,
                timeout=5
            ).stdout.strip()
        except:
            macos_version = "Unknown"
        
        try:
            chip_name = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
        except:
            chip_name = f"Apple {self.chip_generation}" if self.is_apple_silicon else "Intel"
        
        # Get CPU frequency (if available)
        try:
            cpu_freq = subprocess.run(
                ['sysctl', '-n', 'hw.cpufrequency_max'],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()
            cpu_freq_ghz = int(cpu_freq) / 1e9 if cpu_freq else 0
        except:
            cpu_freq_ghz = 0
        
        mem = psutil.virtual_memory()
        
        return {
            'architecture': 'Apple Silicon' if self.is_apple_silicon else 'Intel',
            'chip': chip_name,
            'chip_generation': self.chip_generation,
            'cpu_count': self.cpu_count,
            'performance_cores': self.performance_cores,
            'efficiency_cores': self.efficiency_cores,
            'cpu_freq_ghz': round(cpu_freq_ghz, 2) if cpu_freq_ghz > 0 else "N/A",
            'memory_gb': round(self.memory_gb, 2),
            'memory_available_gb': round(mem.available / (1024**3), 2),
            'memory_used_gb': round(mem.used / (1024**3), 2),
            'memory_percent': mem.percent,
            'macos_version': macos_version,
            'optimal_workers': config.MAX_WORKERS,
            'batch_size': config.BATCH_SIZE,
            'hdf5_cache_gb': config.HDF5_RDCC_NBYTES / (1024**3),
            'data_cache_gb': config.CACHE_SIZE_MB / 1024,
            'extreme_mode': self.is_extreme_mode,
        }
    
    def check_optimization_status(self) -> Dict[str, bool]:
        """Comprehensive optimization status check"""
        
        checks = {
            'apple_silicon_detected': self.is_apple_silicon,
            'm4_chip_detected': self.chip_generation == "M4",
            'sufficient_memory': self.memory_gb >= 24,
            'accelerate_framework': os.environ.get('BLAS') == 'Accelerate',
            'threading_configured': os.environ.get('VECLIB_MAXIMUM_THREADS') is not None,
            'extreme_mode_enabled': self.is_extreme_mode,
            'config_loaded': config.is_configured or True,
            'dask_enabled': config.USE_DASK if hasattr(config, 'USE_DASK') else False,
            'turbo_mode': config.TURBO_MODE if hasattr(config, 'TURBO_MODE') else False,
            'memory_mapping': config.ENABLE_MMAP if hasattr(config, 'ENABLE_MMAP') else False,
            'parallel_io': config.ENABLE_PARALLEL_IO if hasattr(config, 'ENABLE_PARALLEL_IO') else False,
        }
        
        return checks
    
    def print_optimization_report(self):
        """Print EXTREME optimization report"""
        
        info = self.get_system_info()
        checks = self.check_optimization_status()
        settings = self.get_optimal_settings()
        
        print("Optimizaton Report")
        
        print("\n SYSTEM INFORMATION:")
        print(f"  Chip: {info['chip']}")
        print(f"  Generation: {info['chip_generation']}")
        print(f"  Architecture: {info['architecture']}")
        print(f"  Total Cores: {info['cpu_count']} ({info['performance_cores']}P + {info['efficiency_cores']}E)")
        if info['cpu_freq_ghz'] != "N/A":
            print(f"  Max Frequency: {info['cpu_freq_ghz']} GHz")
        print(f"  macOS: {info['macos_version']}")
        
        print("\nMEMORY CONFIGURATION:")
        print(f"  Total RAM: {info['memory_gb']:.1f} GB")
        print(f"  Available: {info['memory_available_gb']:.1f} GB")
        print(f"  Used: {info['memory_used_gb']:.1f} GB ({info['memory_percent']:.1f}%)")
        print(f"  Max Usage: {settings['memory_percent_used']:.0f}% (~{settings['usable_ram_gb']:.1f} GB)")

# Global optimizer instance
optimizer = AppleSiliconOptimizer()

# Auto-configure on import
optimizer.configure_environment()

# Print optimization report on import (can be disabled)
if os.getenv('SHOW_OPTIMIZATION_REPORT', '1') == '1':
    optimizer.print_optimization_report()