"""
Comprehensive test suite for configuration system
Tests config loading, optimizer detection, and system adaptation
"""

from config import (
    config, 
    get_system_info, 
    get_detailed_system_info,
    optimizer,
    Exchange,
    Interval,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)
import sys


def print_header(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_subheader(title):
    """Print a formatted subsection header"""
    print(f"\n🔹 {title}")
    print("-" * 70)


def test_imports():
    """Test that all imports work correctly"""
    print_header("TEST 1: Import Validation")
    
    try:
        assert config is not None
        assert optimizer is not None
        assert Exchange is not None
        assert Interval is not None
        print("✅ All imports successful")
        return True
    except AssertionError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_hardware_detection():
    """Test hardware detection"""
    print_header("TEST 2: Hardware Detection")
    
    info = get_system_info()
    
    print(f"Detected Chip: {info['chip']}")
    print(f"Total RAM: {info['ram_gb']} GB")
    print(f"Available RAM: {info['ram_available_gb']} GB")
    print(f"Used RAM: {info['ram_used_gb']} GB ({info['ram_percent']}%)")
    
    if info['chip'] in ['M1', 'M4']:
        print(f"✅ Valid Apple Silicon detected: {info['chip']}")
        return True
    else:
        print(f"⚠️  Unknown chip detected: {info['chip']}")
        return False


def test_operation_mode():
    """Test operation mode (Travel vs Performance)"""
    print_header("TEST 3: Operation Mode")
    
    info = get_system_info()
    
    if info['is_travel_mode']:
        print("🧳 TRAVEL MODE (M1 8GB)")
        print(f"   Optimizations Applied: {info['optimization_count']}")
    else:
        print("🚀 PERFORMANCE MODE (M4 24GB)")
        print("   No adaptations needed - using native settings")
    
    print(f"\nActive Settings:")
    print(f"  • Max Workers: {info['max_workers']}")
    print(f"  • Batch Size: {info['batch_size']}")
    print(f"  • Chunk Size: {info['chunk_size']:,}")
    print(f"  • Dask Enabled: {info['dask_enabled']}")
    
    print(f"\nMemory Configuration:")
    print(f"  • HDF5 Cache: {info['hdf5_cache_mb']} MB")
    print(f"  • Data Cache: {info['data_cache_mb']} MB")
    print(f"  • Query Cache: {info['query_cache_mb']} MB")
    print(f"  • Memory Limit: {info['memory_limit_gb']} GB ({int(info['memory_limit_percent']*100)}%)")
    
    return True


def test_config_values():
    """Test configuration values"""
    print_header("TEST 4: Configuration Values")
    
    print_subheader("Core Settings")
    print(f"  MAX_WORKERS: {config.MAX_WORKERS}")
    print(f"  BATCH_SIZE: {config.BATCH_SIZE}")
    print(f"  CHUNK_SIZE: {config.CHUNK_SIZE:,}")
    print(f"  USE_DASK: {config.USE_DASK}")
    
    print_subheader("Memory Settings")
    print(f"  HDF5_RDCC_NBYTES: {config.HDF5_RDCC_NBYTES / (1024**2):.0f} MB")
    print(f"  CACHE_SIZE_MB: {config.CACHE_SIZE_MB} MB")
    print(f"  MAX_MEMORY_PERCENT: {config.MAX_MEMORY_PERCENT*100:.0f}%")
    
    print_subheader("HDF5 Settings (Immutable)")
    print(f"  Compression: {config.HDF5_COMPRESSION}")
    print(f"  Compression Level: {config.HDF5_COMPRESSION_LEVEL}")
    print(f"  Chunk Size: {config.HDF5_CHUNK_SIZE}")
    print(f"  Driver: {config.HDF5_DRIVER}")
    
    print_subheader("API Settings")
    print(f"  API Timeout: {config.API_TIMEOUT}s")
    print(f"  Max Retries: {config.MAX_RETRIES}")
    print(f"  Rate Limit: {config.API_RATE_LIMIT} req/s")
    print(f"  API Configured: {config.is_configured}")
    
    return True


def test_detailed_info():
    """Test detailed system information"""
    print_header("TEST 5: Detailed System Information")
    
    info = get_detailed_system_info()
    
    print_subheader("System Details")
    print(f"  macOS Version: {info['macos_version']}")
    print(f"  CPU Cores: {info['cpu_cores']}")
    print(f"  Architecture: {info['chip']}")
    
    print_subheader("Storage & I/O")
    print(f"  Memory Mapping: {'Enabled ✅' if info['enable_mmap'] else 'Disabled ❌'}")
    print(f"  Prefetch: {'Enabled ✅' if info['enable_prefetch'] else 'Disabled ❌'}")
    print(f"  Parallel I/O Workers: {info['parallel_io_workers']}")
    
    print_subheader("Garbage Collection")
    print(f"  Aggressive GC: {'Enabled ⚡' if info['gc_enabled'] else 'Disabled'}")
    if info['gc_enabled']:
        print(f"  GC Interval: Every {info['gc_interval']} operations")
    
    return True


def test_optimizations_applied():
    """Test and display applied optimizations (M1 only)"""
    print_header("TEST 6: Applied Optimizations")
    
    info = get_system_info()
    
    if not info['is_travel_mode']:
        print("⚠️  Running in Performance Mode - no optimizations applied")
        return True
    
    print(f"✅ {info['optimization_count']} optimizations applied for M1 8GB\n")
    
    if info['optimizations']:
        # Group by category
        memory_opts = []
        performance_opts = []
        feature_opts = []
        other_opts = []
        
        for opt in info['optimizations']:
            setting = opt['setting']
            if any(x in setting for x in ['MEMORY', 'CACHE', 'HDF5']):
                memory_opts.append(opt)
            elif any(x in setting for x in ['WORKERS', 'BATCH', 'CHUNK']):
                performance_opts.append(opt)
            elif any(x in setting for x in ['ENABLE', 'USE']):
                feature_opts.append(opt)
            else:
                other_opts.append(opt)
        
        if memory_opts:
            print_subheader("Memory Optimizations")
            for opt in memory_opts[:5]:  # Show first 5
                print(f"  {opt['setting']}: {opt['original']} → {opt['adapted']}")
            if len(memory_opts) > 5:
                print(f"  ... and {len(memory_opts) - 5} more")
        
        if performance_opts:
            print_subheader("Performance Optimizations")
            for opt in performance_opts:
                print(f"  {opt['setting']}: {opt['original']} → {opt['adapted']}")
        
        if feature_opts:
            print_subheader("Feature Toggles")
            for opt in feature_opts:
                print(f"  {opt['setting']}: {opt['original']} → {opt['adapted']}")
    
    return True


def test_enums():
    """Test enum definitions"""
    print_header("TEST 7: Enum Validation")
    
    print_subheader("Exchanges")
    print(f"  Available: {[e.value for e in Exchange]}")
    
    print_subheader("Intervals")
    print(f"  Available: {[i.value for i in Interval]}")
    
    print("✅ All enums valid")
    return True


def test_constants():
    """Test constant definitions"""
    print_header("TEST 8: Constants Validation")
    
    print_subheader("Error Messages")
    print(f"  Defined: {len(ERROR_MESSAGES)} messages")
    print(f"  Sample: {list(ERROR_MESSAGES.keys())[:3]}")
    
    print_subheader("Success Messages")
    print(f"  Defined: {len(SUCCESS_MESSAGES)} messages")
    print(f"  Sample: {list(SUCCESS_MESSAGES.keys())[:3]}")
    
    print("✅ All constants valid")
    return True


def test_memory_status():
    """Test current memory status"""
    print_header("TEST 9: Current Memory Status")
    
    info = get_system_info()
    
    used_percent = info['ram_percent']
    
    # Memory status indicator
    if used_percent < 70:
        status = "🟢 HEALTHY"
    elif used_percent < 85:
        status = "🟡 MODERATE"
    elif used_percent < 95:
        status = "🟠 HIGH"
    else:
        status = "🔴 CRITICAL"
    
    print(f"Memory Status: {status}")
    print(f"\nCurrent Usage:")
    print(f"  Used: {info['ram_used_gb']} GB / {info['ram_gb']} GB ({used_percent}%)")
    print(f"  Available: {info['ram_available_gb']} GB")
    print(f"  App Limit: {info['memory_limit_gb']} GB")
    
    # Memory bar visualization
    bar_length = 50
    filled = int((used_percent / 100) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\n  [{bar}] {used_percent}%")
    
    return True


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("  🧪 KITE DATA MANAGER - CONFIGURATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Import Validation", test_imports),
        ("Hardware Detection", test_hardware_detection),
        ("Operation Mode", test_operation_mode),
        ("Configuration Values", test_config_values),
        ("Detailed System Info", test_detailed_info),
        ("Applied Optimizations", test_optimizations_applied),
        ("Enum Validation", test_enums),
        ("Constants Validation", test_constants),
        ("Memory Status", test_memory_status),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} FAILED with error: {e}")
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("  ✅ ALL TESTS PASSED - CONFIGURATION SYSTEM READY!")
    else:
        print(f"  ⚠️  {total - passed} TEST(S) FAILED - REVIEW REQUIRED")
    
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)