"""
Logging and metrics infrastructure for Open Dsearch.

Provides structured logging with JSON output support,
context propagation, and metrics collection.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from functools import wraps


# Context variables for request tracking
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return _request_id.get()


def get_trace_id() -> Optional[str]:
    """Get current trace ID from context."""
    return _trace_id.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    _request_id.set(request_id)


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context."""
    _trace_id.set(trace_id)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request/trace IDs
        request_id = get_request_id()
        trace_id = get_trace_id()
        if request_id:
            log_data["request_id"] = request_id
        if trace_id:
            log_data["trace_id"] = trace_id
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "message"
            ):
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ContextFilter(logging.Filter):
    """Filter that adds context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to record."""
        record.request_id = get_request_id()
        record.trace_id = get_trace_id()
        return True


def configure_logging(
    level: str = "INFO",
    format_type: str = "text",
    output: Optional[Path] = None
) -> None:
    """
    Configure logging for Open Dsearch.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: 'text' or 'json'
        output: Optional file path for log output
    """
    handlers: List[logging.Handler] = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    
    # File handler
    if output:
        file_handler = logging.FileHandler(output)
        handlers.append(file_handler)
    
    # Configure formatters
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Apply to handlers
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger with context support."""
    return logging.getLogger(name)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class MetricsCollector:
    """Collects and exports metrics."""
    
    def __init__(self, prefix: str = "dsearch"):
        """Initialize collector."""
        self.prefix = prefix
        self._metrics: List[MetricPoint] = []
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._logger = get_logger(__name__)
    
    def _full_name(self, name: str) -> str:
        """Get full metric name with prefix."""
        return f"{self.prefix}.{name}"
    
    def record(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value."""
        point = MetricPoint(
            name=self._full_name(name),
            value=value,
            tags=tags or {}
        )
        self._metrics.append(point)
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        full_name = self._full_name(name)
        key = f"{full_name}:{json.dumps(tags or {}, sort_keys=True)}"
        
        if key not in self._counters:
            self._counters[key] = 0.0
        
        self._counters[key] += value
        
        # Also record as point
        self.record(name, self._counters[key], tags)
    
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        full_name = self._full_name(name)
        key = f"{full_name}:{json.dumps(tags or {}, sort_keys=True)}"
        self._gauges[key] = value
        self.record(name, value, tags)
    
    def timer(self, name: str) -> "Timer":
        """Create a timer context manager."""
        return Timer(self, name)
    
    def get_metrics(self) -> List[MetricPoint]:
        """Get all recorded metrics."""
        return list(self._metrics)
    
    def get_counters(self) -> Dict[str, float]:
        """Get all counter values."""
        return dict(self._counters)
    
    def get_gauges(self) -> Dict[str, float]:
        """Get all gauge values."""
        return dict(self._gauges)
    
    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
    
    def export_json(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(
            [m.to_dict() for m in self._metrics],
            default=str,
            indent=2
        )
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Group by metric name
        by_name: Dict[str, List[MetricPoint]] = {}
        for point in self._metrics:
            if point.name not in by_name:
                by_name[point.name] = []
            by_name[point.name].append(point)
        
        for name, points in by_name.items():
            # Metric type (assume gauge for simplicity)
            lines.append(f"# TYPE {name} gauge")
            
            for point in points:
                tag_str = ",".join(
                    f'{k}="{v}"' for k, v in point.tags.items()
                )
                if tag_str:
                    lines.append(f'{name}{{{tag_str}}} {point.value}')
                else:
                    lines.append(f'{name} {point.value}')
        
        return "\n".join(lines)
    
    def log_summary(self) -> None:
        """Log a summary of metrics."""
        if not self._metrics:
            return
        
        summary = {
            "total_metrics": len(self._metrics),
            "unique_names": len(set(m.name for m in self._metrics)),
            "counters": len(self._counters),
            "gauges": len(self._gauges),
        }
        
        self._logger.info(f"Metrics summary: {summary}")


class Timer:
    """Context manager for timing operations."""
    
    def __init__(
        self,
        collector: MetricsCollector,
        name: str,
        tags: Optional[Dict[str, str]] = None
    ):
        """Initialize timer."""
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    def __enter__(self) -> "Timer":
        """Start timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timer and record."""
        if self.start_time is not None:
            self.duration = time.time() - self.start_time
            self.collector.record(self.name, self.duration, self.tags)
    
    def elapsed(self) -> Optional[float]:
        """Get elapsed time without stopping."""
        if self.start_time is None:
            return None
        return time.time() - self.start_time


def timed(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to time function execution.
    
    Args:
        metric_name: Name of the timing metric
        tags: Optional tags
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            with collector.timer(metric_name) as timer:
                timer.tags = tags or {}
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset global metrics collector."""
    global _metrics_collector
    _metrics_collector = None


class LogContext:
    """Context manager for temporary log context."""
    
    def __init__(self, **kwargs):
        """Initialize with context values."""
        self.context = kwargs
        self.tokens = {}
    
    def __enter__(self):
        """Set context values."""
        if "request_id" in self.context:
            self.tokens["request_id"] = _request_id.set(
                self.context["request_id"]
            )
        if "trace_id" in self.context:
            self.tokens["trace_id"] = _trace_id.set(
                self.context["trace_id"]
            )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context values."""
        for var_name, token in self.tokens.items():
            if var_name == "request_id":
                _request_id.reset(token)
            elif var_name == "trace_id":
                _trace_id.reset(token)