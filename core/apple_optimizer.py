"""
Apple Silicon optimizations for Kite Connect Data Manager
Hardcoded for personal Apple Silicon Mac use
"""

import os
import psutil
from typing import Dict, Any

class AppleSiliconOptimizer:
    """Hardware-specific optimizations for Apple Silicon"""
    
    def __init__(self):
        # Get actual system memory
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        self.cpu_count = os.cpu_count() or 8
        
    def get_optimal_settings(self) -> Dict[str, Any]:
        """Get optimal settings for Apple Silicon"""
        
        return {
            # Performance
            'max_workers': 8,  # Good for M1/M2/M3
            'chunk_size': 1000,
            'memory_limit_mb': int(self.memory_gb * 0.6 * 1024),  # 60% of RAM
            
            # Apple Silicon specific
            'use_high_performance_cores': True,
            'memory_mapping_size': 268435456,  # 256MB
            'cache_size': 20000,  # 80MB cache
            'temp_store': 'MEMORY',
            'mmap_threshold': 64 * 1024,  # 64KB
        }
    
    def configure_environment(self):
        """Set environment variables for Apple Silicon optimization"""
        
        # Optimize for Apple Silicon
        os.environ['OPENBLAS_NUM_THREADS'] = str(self.cpu_count)
        os.environ['MKL_NUM_THREADS'] = str(self.cpu_count)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(self.cpu_count)
        os.environ['NUMEXPR_NUM_THREADS'] = str(self.cpu_count)
        
        # Use Accelerate framework (Apple's optimized math library)
        os.environ['BLAS'] = 'Accelerate'
        os.environ['LAPACK'] = 'Accelerate'
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for display in UI"""
        
        return {
            'architecture': 'Apple Silicon',
            'cpu_count': self.cpu_count,
            'memory_gb': round(self.memory_gb, 2),
            'optimal_workers': 8,
            'cache_size_mb': 80
        }

# Global optimizer instance
optimizer = AppleSiliconOptimizer()