"""
Unit tests for performance monitoring utilities.

These tests verify that the PerformanceMetrics class correctly tracks
timing information for operations with minimal overhead.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from calendarbot.display.epaper.utils.performance import PerformanceMetrics


class TestPerformanceMetrics:
    """Test suite for PerformanceMetrics class."""

    def test_init_when_created_then_empty_dictionaries(self) -> None:
        """Test initialization creates empty dictionaries."""
        metrics = PerformanceMetrics()
        
        assert hasattr(metrics, "_operation_timers")
        assert hasattr(metrics, "_operation_results")
        assert len(metrics._operation_timers) == 0
        assert len(metrics._operation_results) == 0

    def test_start_operation_when_called_then_stores_start_time(self) -> None:
        """Test start_operation stores the start time."""
        metrics = PerformanceMetrics()
        
        with patch('time.time', return_value=1000.0):
            metrics.start_operation("test_op")
            
            assert "test_op" in metrics._operation_timers
            assert metrics._operation_timers["test_op"] == 1000000.0  # Converted to ms

    def test_end_operation_when_operation_exists_then_returns_duration(self) -> None:
        """Test end_operation calculates and returns duration."""
        metrics = PerformanceMetrics()
        
        # Mock time.time to return predictable values
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1001.0]  # Start time, end time
            
            metrics.start_operation("test_op")
            duration = metrics.end_operation("test_op")
            
            assert duration == 1000.0  # 1001 - 1000 seconds = 1 second = 1000 ms
            assert "test_op" in metrics._operation_results
            assert metrics._operation_results["test_op"] == 1000.0
            assert "test_op" not in metrics._operation_timers  # Timer should be removed

    def test_end_operation_when_operation_not_started_then_raises_key_error(self) -> None:
        """Test end_operation raises KeyError for non-existent operation."""
        metrics = PerformanceMetrics()
        
        with pytest.raises(KeyError):
            metrics.end_operation("nonexistent_op")

    def test_get_operation_time_when_operation_exists_then_returns_duration(self) -> None:
        """Test get_operation_time returns the correct duration."""
        metrics = PerformanceMetrics()
        
        # Set up a completed operation
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1002.0]  # Start time, end time
            
            metrics.start_operation("test_op")
            metrics.end_operation("test_op")
            
            duration = metrics.get_operation_time("test_op")
            assert duration == 2000.0  # 1002 - 1000 seconds = 2 seconds = 2000 ms

    def test_get_operation_time_when_operation_not_exists_then_returns_none(self) -> None:
        """Test get_operation_time returns None for non-existent operation."""
        metrics = PerformanceMetrics()
        
        duration = metrics.get_operation_time("nonexistent_op")
        assert duration is None

    def test_reset_when_called_then_clears_all_data(self) -> None:
        """Test reset clears all stored data."""
        metrics = PerformanceMetrics()
        
        # Set up some operations
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1001.0, 1002.0, 1003.0]
            
            metrics.start_operation("op1")
            metrics.end_operation("op1")
            metrics.start_operation("op2")
            
            # Reset should clear both completed and in-progress operations
            metrics.reset()
            
            assert len(metrics._operation_timers) == 0
            assert len(metrics._operation_results) == 0

    def test_get_summary_when_multiple_operations_then_returns_all_results(self) -> None:
        """Test get_summary returns all operation results."""
        metrics = PerformanceMetrics()
        
        # Set up multiple operations
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1001.0, 1002.0, 1004.0]
            
            metrics.start_operation("op1")
            metrics.end_operation("op1")
            metrics.start_operation("op2")
            metrics.end_operation("op2")
            
            summary = metrics.get_summary()
            
            assert len(summary) == 2
            assert summary["op1"] == 1000.0  # 1001 - 1000 seconds = 1 second = 1000 ms
            assert summary["op2"] == 2000.0  # 1004 - 1002 seconds = 2 seconds = 2000 ms
            
            # Verify it's a copy, not the original
            summary["new_op"] = 3000.0
            assert "new_op" not in metrics._operation_results

    def test_real_timing_when_actual_operation_then_reasonable_values(self) -> None:
        """Test with real timing to ensure reasonable values."""
        metrics = PerformanceMetrics()
        
        metrics.start_operation("sleep_op")
        time.sleep(0.01)  # Sleep for 10ms
        duration = metrics.end_operation("sleep_op")
        
        # Duration should be at least 10ms, but allow some overhead
        assert duration >= 10.0
        # Shouldn't be unreasonably high (add some margin for slow test environments)
        assert duration < 100.0