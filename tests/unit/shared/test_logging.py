"""Unit tests for logging module."""

import pytest
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch

from src.shared.logging import (
    get_logger,
    configure_logging,
    MetricsCollector,
    Timer,
    JSONFormatter,
    ContextFilter,
    LogContext,
    get_request_id,
    get_trace_id,
    set_request_id,
    set_trace_id,
    get_metrics_collector,
    reset_metrics_collector,
)


class TestContextVariables:
    """Tests for context variables."""
    
    def test_request_id(self):
        """Test request ID context."""
        assert get_request_id() is None
        
        set_request_id("req-123")
        assert get_request_id() == "req-123"
    
    def test_trace_id(self):
        """Test trace ID context."""
        assert get_trace_id() is None
        
        set_trace_id("trace-456")
        assert get_trace_id() == "trace-456"


class TestJSONFormatter:
    """Tests for JSONFormatter."""
    
    def test_format_basic(self):
        """Test basic log formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_format_with_context(self):
        """Test formatting with context."""
        set_request_id("req-abc")
        set_trace_id("trace-xyz")
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["request_id"] == "req-abc"
        assert data["trace_id"] == "trace-xyz"
        
        # Cleanup
        set_request_id(None)
        set_trace_id(None)
    
    def test_format_with_exception(self):
        """Test formatting with exception."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except:
            import sys
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestContextFilter:
    """Tests for ContextFilter."""
    
    def test_filter_adds_context(self):
        """Test filter adds context to record."""
        set_request_id("req-123")
        
        filter = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        result = filter.filter(record)
        assert result is True
        assert record.request_id == "req-123"
        
        # Cleanup
        set_request_id(None)


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def setup_method(self):
        """Reset collector before each test."""
        reset_metrics_collector()
    
    def teardown_method(self):
        """Reset collector after each test."""
        reset_metrics_collector()
    
    def test_record_metric(self):
        """Test recording a metric."""
        collector = MetricsCollector()
        collector.record("test_metric", 42.0, {"tag": "value"})
        
        metrics = collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].name == "dsearch.test_metric"
        assert metrics[0].value == 42.0
        assert metrics[0].tags["tag"] == "value"
    
    def test_increment_counter(self):
        """Test incrementing counter."""
        collector = MetricsCollector()
        
        collector.increment("requests", 1.0, {"method": "GET"})
        collector.increment("requests", 1.0, {"method": "GET"})
        
        counters = collector.get_counters()
        key = 'dsearch.requests:{"method": "GET"}'
        assert counters[key] == 2.0
    
    def test_gauge(self):
        """Test setting gauge."""
        collector = MetricsCollector()
        collector.gauge("active_connections", 5.0)
        
        gauges = collector.get_gauges()
        assert len(gauges) == 1
    
    def test_timer_context(self):
        """Test timer context manager."""
        collector = MetricsCollector()
        
        with collector.timer("operation") as timer:
            timer.tags = {"type": "test"}
            # Simulate work
            import time
            time.sleep(0.01)
        
        metrics = collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].name == "dsearch.operation"
        assert metrics[0].value >= 0.01
    
    def test_timer_elapsed(self):
        """Test timer elapsed method."""
        collector = MetricsCollector()
        
        with collector.timer("test") as timer:
            import time
            time.sleep(0.01)
            elapsed = timer.elapsed()
            assert elapsed >= 0.01
    
    def test_clear(self):
        """Test clearing metrics."""
        collector = MetricsCollector()
        collector.record("metric", 1.0)
        collector.increment("counter", 1.0)
        collector.gauge("gauge", 1.0)
        
        collector.clear()
        
        assert len(collector.get_metrics()) == 0
        assert len(collector.get_counters()) == 0
        assert len(collector.get_gauges()) == 0
    
    def test_export_json(self):
        """Test JSON export."""
        collector = MetricsCollector()
        collector.record("test", 42.0)
        
        json_output = collector.export_json()
        data = json.loads(json_output)
        
        assert len(data) == 1
        assert data[0]["name"] == "dsearch.test"
        assert data[0]["value"] == 42.0
    
    def test_export_prometheus(self):
        """Test Prometheus export."""
        collector = MetricsCollector()
        collector.record("test_metric", 42.0, {"env": "prod"})
        
        prom_output = collector.export_prometheus()
        
        assert "# TYPE dsearch.test_metric gauge" in prom_output
        assert "dsearch.test_metric" in prom_output
        assert 'env="prod"' in prom_output


class TestTimer:
    """Tests for Timer class."""
    
    def test_timer_records_duration(self):
        """Test timer records duration."""
        collector = MetricsCollector()
        
        with Timer(collector, "test_op"):
            import time
            time.sleep(0.01)
        
        metrics = collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].value >= 0.01
    
    def test_timer_with_tags(self):
        """Test timer with tags."""
        collector = MetricsCollector()
        
        with Timer(collector, "op", {"type": "db"}) as timer:
            pass
        
        metrics = collector.get_metrics()
        assert metrics[0].tags["type"] == "db"


class TestLogContext:
    """Tests for LogContext."""
    
    def test_context_manager(self):
        """Test context manager sets and resets."""
        assert get_request_id() is None
        
        with LogContext(request_id="req-123"):
            assert get_request_id() == "req-123"
        
        assert get_request_id() is None
    
    def test_nested_context(self):
        """Test nested contexts."""
        with LogContext(request_id="outer"):
            assert get_request_id() == "outer"
            
            with LogContext(request_id="inner"):
                assert get_request_id() == "inner"
            
            assert get_request_id() == "outer"


class TestGlobalMetrics:
    """Tests for global metrics functions."""
    
    def setup_method(self):
        """Reset before each test."""
        reset_metrics_collector()
    
    def teardown_method(self):
        """Reset after each test."""
        reset_metrics_collector()
    
    def test_get_metrics_collector(self):
        """Test get_metrics_collector creates singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
    
    def test_reset_metrics_collector(self):
        """Test reset creates new instance."""
        collector1 = get_metrics_collector()
        reset_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is not collector2
