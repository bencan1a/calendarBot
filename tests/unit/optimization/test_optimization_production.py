"""Optimized unit tests for calendarbot.optimization.production module data classes."""

import logging
import re
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from calendarbot.optimization.production import (
    OptimizationRule,
    OptimizationType,
    ProductionLogFilter,
)


class TestOptimizationRuleCore:
    """Test core OptimizationRule functionality not covered elsewhere."""

    def test_unique_rule_ids_generated(self):
        """Test each rule gets a unique ID by default."""
        rule1 = OptimizationRule()
        rule2 = OptimizationRule()

        assert rule1.rule_id != rule2.rule_id
        # Both should be valid UUIDs
        assert uuid.UUID(rule1.rule_id)
        assert uuid.UUID(rule2.rule_id)

    def test_matches_with_invalid_regex_pattern(self):
        """Test matches method handles invalid regex patterns gracefully."""
        rule = OptimizationRule(logger_pattern=r"[invalid regex")
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should raise re.error for invalid regex
        with pytest.raises(re.error):
            rule.matches(record)

    @pytest.mark.parametrize(
        "logger_name,pattern,expected",
        [
            ("calendarbot.main", r"calendarbot\..*", True),
            ("calendarbot.utils.logging", r"calendarbot\.utils\..*", True),
            ("third_party.module", r"calendarbot\..*", False),
            ("requests.adapters", r"(requests|urllib3)\..*", True),
            ("urllib3.connectionpool", r"(requests|urllib3)\..*", True),
            ("aiohttp.client", r"(requests|urllib3)\..*", False),
        ],
    )
    def test_matches_logger_patterns(self, logger_name, pattern, expected):
        """Test matches method with various logger name patterns."""
        rule = OptimizationRule(logger_pattern=pattern)
        record = logging.LogRecord(
            name=logger_name,
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is expected

    @pytest.mark.parametrize(
        "level,threshold,expected",
        [
            (logging.DEBUG, logging.DEBUG, True),
            (logging.INFO, logging.DEBUG, True),
            (logging.WARNING, logging.INFO, True),
            (logging.ERROR, logging.WARNING, True),
            (logging.CRITICAL, logging.ERROR, True),
            (logging.DEBUG, logging.INFO, False),
            (logging.INFO, logging.WARNING, False),
            (logging.WARNING, logging.ERROR, False),
        ],
    )
    def test_matches_level_thresholds(self, level, threshold, expected):
        """Test matches method with various level thresholds."""
        rule = OptimizationRule(level_threshold=threshold)
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is expected


class TestProductionLogFilterInitialization:
    """Test ProductionLogFilter initialization - optimized for speed."""

    def test_initialization_with_empty_rules(self):
        """Test ProductionLogFilter initialization with empty rules list."""
        log_filter = ProductionLogFilter([])

        assert log_filter.rules == []
        assert log_filter.settings is None
        assert isinstance(log_filter.message_counts, dict)
        assert isinstance(log_filter.last_reset, datetime)
        assert log_filter.reset_interval.total_seconds() == 300  # 5 minutes
        assert log_filter.filtered_count == 0
        assert log_filter.total_count == 0

    def test_rules_sorting_by_priority(self):
        """Test rules are properly sorted by priority in descending order."""
        rules = [
            OptimizationRule(name="Low Priority", priority=1),
            OptimizationRule(name="High Priority", priority=100),
            OptimizationRule(name="Medium Priority", priority=50),
            OptimizationRule(name="Zero Priority", priority=0),
        ]

        log_filter = ProductionLogFilter(rules)

        # Check sorting order (highest to lowest priority)
        priorities = [rule.priority for rule in log_filter.rules]
        assert priorities == [100, 50, 1, 0]

    def test_message_counts_initialization(self):
        """Test message_counts is properly initialized as defaultdict."""
        log_filter = ProductionLogFilter([OptimizationRule()])

        # Should return 0 for non-existent keys (defaultdict behavior)
        assert log_filter.message_counts["non_existent_key"] == 0

        # Should allow setting values
        log_filter.message_counts["test_key"] = 5
        assert log_filter.message_counts["test_key"] == 5

    @patch("calendarbot.optimization.production.datetime")
    def test_last_reset_timestamp(self, mock_datetime):
        """Test last_reset is set to current UTC time on initialization."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        log_filter = ProductionLogFilter([OptimizationRule()])

        mock_datetime.now.assert_called_with(timezone.utc)
        assert log_filter.last_reset == fixed_time

    def test_inheritance_from_logging_filter(self):
        """Test ProductionLogFilter inherits from logging.Filter."""
        log_filter = ProductionLogFilter([OptimizationRule()])

        assert isinstance(log_filter, logging.Filter)
        assert hasattr(log_filter, "filter")  # Has filter method from base class

    def test_initialization_preserves_rule_objects(self):
        """Test initialization preserves original rule objects."""
        original_rule = OptimizationRule(
            name="Original Rule", optimization_type=OptimizationType.DEBUG_REMOVAL, priority=42
        )

        log_filter = ProductionLogFilter([original_rule])

        # Should be the same object, not a copy
        assert log_filter.rules[0] is original_rule
        assert log_filter.rules[0].name == "Original Rule"
        assert log_filter.rules[0].optimization_type == OptimizationType.DEBUG_REMOVAL
        assert log_filter.rules[0].priority == 42
