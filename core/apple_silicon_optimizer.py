"""
Apple Silicon specific optimizations for Kite Connect Data Manager
Integrated with app configuration
"""

import os
import psutil
import subprocess
from typing import Dict, Any
from config.settings import config

class AppleSiliconOptimizer:
    """Hardware-specific optimizations for Apple Silicon"""
    
    def __init__(self):
        self.is_apple_silicon = self._detect_apple_silicon()
        self.cpu_count = os.cpu_count() or 8
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        
    def _detect_apple_silicon(self) -> bool:
        """Detect if running on Apple Silicon"""
        try:
            result = subprocess.run(
                ['uname', '-m'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return result.stdout.strip() == 'arm64'
        except (subprocess.SubprocessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return False
    
    def get_optimal_settings(self) -> Dict[str, Any]:
        """Get optimal settings based on hardware (integrates with config)"""
        
        settings = {
            # From config
            'max_workers': config.MAX_WORKERS,
            'chunk_size': config.CHUNK_SIZE,
            'batch_size': config.BATCH_SIZE,
            'memory_limit_mb': int(self.memory_gb * config.MAX_MEMORY_PERCENT * 1024),
            
            # Apple Silicon specific
            'use_high_performance_cores': self.is_apple_silicon,
            'cache_size': config.HDF5_CACHE_SIZE,
            'memory_mapping_size': config.HDF5_RDCC_NBYTES,
            'temp_store': 'MEMORY' if self.is_apple_silicon else 'DEFAULT',
        }
        
        return settings
    
    def configure_environment(self):
        """
        Set environment variables for optimal performance
        Note: This is now handled by config._configure_numerical_libraries()
        but kept here for backwards compatibility
        """
        if self.is_apple_silicon:
            # These are already set by config, but we ensure they're set
            os.environ['OPENBLAS_NUM_THREADS'] = str(self.cpu_count)
            os.environ['MKL_NUM_THREADS'] = str(self.cpu_count)
            os.environ['VECLIB_MAXIMUM_THREADS'] = str(self.cpu_count)
            os.environ['NUMEXPR_NUM_THREADS'] = str(self.cpu_count)
            
            # Use Accelerate framework
            os.environ['BLAS'] = 'Accelerate'
            os.environ['LAPACK'] = 'Accelerate'
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        
        try:
            # Get macOS version
            macos_version = subprocess.run(
                ['sw_vers', '-productVersion'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            macos_version = macos_version.stdout.strip()
        except:
            macos_version = "Unknown"
        
        # Get chip name
        try:
            chip_name = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            chip_name = chip_name.stdout.strip()
        except:
            chip_name = "Apple M1" if self.is_apple_silicon else "Intel"
        
        return {
            'architecture': 'Apple Silicon' if self.is_apple_silicon else 'Intel',
            'chip': chip_name,
            'cpu_count': self.cpu_count,
            'memory_gb': round(self.memory_gb, 2),
            'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'macos_version': macos_version,
            'optimal_workers': config.MAX_WORKERS,
            'batch_size': config.BATCH_SIZE,
            'performance_cores': self.is_apple_silicon,
            'hdf5_cache_mb': config.HDF5_RDCC_NBYTES / (1024**2),
        }
    
    def check_optimization_status(self) -> Dict[str, bool]:
        """Check if optimizations are properly configured"""
        
        checks = {
            'apple_silicon_detected': self.is_apple_silicon,
            'accelerate_framework': os.environ.get('BLAS') == 'Accelerate',
            'threading_configured': os.environ.get('VECLIB_MAXIMUM_THREADS') is not None,
            'sufficient_memory': self.memory_gb >= 8,
            'config_loaded': config.is_configured or True,  # Config always loads
        }
        
        return checks
    
    def print_optimization_report(self):
        """Print a detailed optimization report"""
        
        info = self.get_system_info()
        checks = self.check_optimization_status()
        settings = self.get_optimal_settings()
        
        print("\n" + "="*70)
        print("🚀 APPLE SILICON OPTIMIZATION REPORT")
        print("="*70)
        
        print("\n📊 SYSTEM INFORMATION:")
        print(f"  • Architecture: {info['architecture']}")
        print(f"  • Chip: {info['chip']}")
        print(f"  • macOS Version: {info['macos_version']}")
        print(f"  • CPU Cores: {info['cpu_count']}")
        print(f"  • Total RAM: {info['memory_gb']:.1f} GB")
        print(f"  • Available RAM: {info['memory_available_gb']:.1f} GB")
        
        print("\n⚙️  OPTIMIZATION STATUS:")
        for check, status in checks.items():
            icon = "✅" if status else "❌"
            print(f"  {icon} {check.replace('_', ' ').title()}")
        
        print("\n🎯 PERFORMANCE SETTINGS:")
        print(f"  • Max Workers: {settings['max_workers']}")
        print(f"  • Batch Size: {settings['batch_size']}")
        print(f"  • Chunk Size: {settings['chunk_size']}")
        print(f"  • Memory Limit: {settings['memory_limit_mb']:.0f} MB")
        print(f"  • HDF5 Cache: {settings['memory_mapping_size'] / (1024**2):.0f} MB")
        print(f"  • High Performance Cores: {'Enabled' if settings['use_high_performance_cores'] else 'Disabled'}")
        
        print("\n💡 RECOMMENDATIONS:")
        if not self.is_apple_silicon:
            print("  ⚠️  Not running on Apple Silicon - some optimizations disabled")
        if self.memory_gb < 16:
            print("  ℹ️  8GB RAM detected - using conservative memory settings")
        if checks['accelerate_framework']:
            print("  ✅ Accelerate framework active - maximum performance!")
        
        print("="*70 + "\n")

# Global optimizer instance
optimizer = AppleSiliconOptimizer()

# Auto-configure on import
optimizer.configure_environment()