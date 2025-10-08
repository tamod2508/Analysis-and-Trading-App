"""
Performance Metrics Collection

Collects and reports performance metrics for operations in the application.
Useful for profiling, optimization, and monitoring.
"""

import time
import statistics
from contextlib import contextmanager
from collections import defaultdict
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation"""
    operation_name: str
    execution_times: List[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    last_executed: Optional[datetime] = None

    @property
    def total_count(self) -> int:
        """Total number of executions"""
        return self.success_count + self.error_count

    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    @property
    def avg_time(self) -> float:
        """Average execution time"""
        if not self.execution_times:
            return 0.0
        return statistics.mean(self.execution_times)

    @property
    def median_time(self) -> float:
        """Median execution time"""
        if not self.execution_times:
            return 0.0
        return statistics.median(self.execution_times)

    @property
    def min_time(self) -> float:
        """Minimum execution time"""
        if not self.execution_times:
            return 0.0
        return min(self.execution_times)

    @property
    def max_time(self) -> float:
        """Maximum execution time"""
        if not self.execution_times:
            return 0.0
        return max(self.execution_times)

    @property
    def stddev_time(self) -> float:
        """Standard deviation of execution times"""
        if len(self.execution_times) < 2:
            return 0.0
        return statistics.stdev(self.execution_times)

    def get_stats(self) -> Dict[str, Any]:
        """Get complete statistics for this operation"""
        return {
            'operation': self.operation_name,
            'count': self.total_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': round(self.success_rate, 2),
            'avg_time': round(self.avg_time, 4),
            'median_time': round(self.median_time, 4),
            'min_time': round(self.min_time, 4),
            'max_time': round(self.max_time, 4),
            'stddev_time': round(self.stddev_time, 4),
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
        }


class PerformanceMetrics:
    """
    Collect and report performance metrics

    Usage:
        metrics = PerformanceMetrics()

        # Method 1: Context manager
        with metrics.measure('save_ohlcv'):
            manager.save_ohlcv(...)

        # Method 2: Decorator
        @metrics.tracked('fetch_data')
        def fetch_data():
            ...

        # Get statistics
        stats = metrics.get_stats('save_ohlcv')
        all_stats = metrics.get_all_stats()
    """

    def __init__(self):
        self.metrics: Dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics(operation_name="")
        )
        self.enabled = True

    @contextmanager
    def measure(self, operation: str, log: bool = False):
        """
        Measure execution time of an operation

        Args:
            operation: Name of the operation
            log: Whether to log the execution time

        Usage:
            with metrics.measure('save_data'):
                save_data(...)
        """
        if not self.enabled:
            yield
            return

        # Initialize metric if not exists
        if operation not in self.metrics:
            self.metrics[operation] = OperationMetrics(operation_name=operation)

        metric = self.metrics[operation]
        start_time = time.time()
        error_occurred = False

        try:
            yield
            metric.success_count += 1
        except Exception as e:
            metric.error_count += 1
            error_occurred = True
            raise
        finally:
            elapsed = time.time() - start_time
            metric.execution_times.append(elapsed)
            metric.last_executed = datetime.now()

            if log:
                status = "ERROR" if error_occurred else "SUCCESS"
                logger.info(
                    f"[{status}] {operation}: {elapsed:.4f}s "
                    f"(avg: {metric.avg_time:.4f}s, count: {metric.total_count})"
                )

    def tracked(self, operation: str, log: bool = False):
        """
        Decorator to track function execution time

        Args:
            operation: Name of the operation
            log: Whether to log the execution time

        Usage:
            @metrics.tracked('fetch_data')
            def fetch_data():
                ...
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                with self.measure(operation, log=log):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def record_success(self, operation: str, execution_time: float) -> None:
        """Manually record a successful operation"""
        if not self.enabled:
            return

        if operation not in self.metrics:
            self.metrics[operation] = OperationMetrics(operation_name=operation)

        metric = self.metrics[operation]
        metric.success_count += 1
        metric.execution_times.append(execution_time)
        metric.last_executed = datetime.now()

    def record_error(self, operation: str) -> None:
        """Manually record a failed operation"""
        if not self.enabled:
            return

        if operation not in self.metrics:
            self.metrics[operation] = OperationMetrics(operation_name=operation)

        metric = self.metrics[operation]
        metric.error_count += 1
        metric.last_executed = datetime.now()

    def get_stats(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific operation

        Args:
            operation: Name of the operation

        Returns:
            Dict with statistics or None if operation not found
        """
        if operation not in self.metrics:
            return None

        return self.metrics[operation].get_stats()

    def get_all_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all operations

        Returns:
            List of dicts with statistics for each operation
        """
        return [metric.get_stats() for metric in self.metrics.values()]

    def get_summary(self) -> str:
        """
        Get human-readable summary of all metrics

        Returns:
            Formatted string summary
        """
        if not self.metrics:
            return "No metrics collected yet."

        lines = ["Performance Metrics Summary", "=" * 80]

        # Sort by average execution time (slowest first)
        sorted_metrics = sorted(
            self.metrics.values(),
            key=lambda m: m.avg_time,
            reverse=True
        )

        for metric in sorted_metrics:
            stats = metric.get_stats()
            lines.append(
                f"\n{stats['operation']}:\n"
                f"  Count: {stats['count']} (Success: {stats['success_count']}, "
                f"Errors: {stats['error_count']})\n"
                f"  Success Rate: {stats['success_rate']}%\n"
                f"  Time: avg={stats['avg_time']}s, median={stats['median_time']}s, "
                f"min={stats['min_time']}s, max={stats['max_time']}s\n"
                f"  Std Dev: {stats['stddev_time']}s\n"
                f"  Last Executed: {stats['last_executed']}"
            )

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def reset(self, operation: Optional[str] = None) -> None:
        """
        Reset metrics

        Args:
            operation: Name of specific operation to reset. If None, reset all.
        """
        if operation is None:
            self.metrics.clear()
            logger.info("All metrics reset")
        elif operation in self.metrics:
            del self.metrics[operation]
            logger.info(f"Metrics reset for: {operation}")

    def enable(self) -> None:
        """Enable metrics collection"""
        self.enabled = True
        logger.info("Metrics collection enabled")

    def disable(self) -> None:
        """Disable metrics collection"""
        self.enabled = False
        logger.info("Metrics collection disabled")


# Global metrics instance (can be imported and used across modules)
global_metrics = PerformanceMetrics()
