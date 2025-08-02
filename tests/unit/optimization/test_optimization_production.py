"""Unit tests for calendarbot.optimization.production module data classes and enums."""

import logging
import re
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.optimization.production import (
    OptimizationRule,
    OptimizationType,
    ProductionLogFilter,
)


class TestOptimizationType:
    """Test OptimizationType enum functionality."""

    def test_enum_values_exist(self):
        """Test all expected enum values are defined."""
        assert OptimizationType.VOLUME_REDUCTION.value == "volume_reduction"
        assert OptimizationType.LEVEL_ADJUSTMENT.value == "level_adjustment"
        assert OptimizationType.DEBUG_REMOVAL.value == "debug_removal"
        assert OptimizationType.FREQUENCY_LIMITING.value == "frequency_limiting"
        assert OptimizationType.CONDITIONAL_LOGGING.value == "conditional_logging"
        assert OptimizationType.PERFORMANCE_FILTERING.value == "performance_filtering"
        assert OptimizationType.CONTENT_OPTIMIZATION.value == "content_optimization"
        assert OptimizationType.HANDLER_OPTIMIZATION.value == "handler_optimization"

    def test_enum_value_access(self):
        """Test enum values can be accessed by name."""
        opt_type = OptimizationType.VOLUME_REDUCTION
        assert opt_type.value == "volume_reduction"
        assert str(opt_type) == "OptimizationType.VOLUME_REDUCTION"

    def test_enum_iteration(self):
        """Test enum can be iterated over."""
        enum_values = list(OptimizationType)
        assert len(enum_values) == 8
        assert OptimizationType.VOLUME_REDUCTION in enum_values
        assert OptimizationType.HANDLER_OPTIMIZATION in enum_values

    def test_enum_comparison(self):
        """Test enum values can be compared."""
        opt1 = OptimizationType.VOLUME_REDUCTION
        opt2 = OptimizationType.VOLUME_REDUCTION
        opt3 = OptimizationType.DEBUG_REMOVAL

        assert opt1 == opt2
        assert opt1 != opt3

    def test_enum_from_string_value(self):
        """Test creating enum from string value."""
        opt_type = OptimizationType("volume_reduction")
        assert opt_type == OptimizationType.VOLUME_REDUCTION

    def test_invalid_enum_value_raises_error(self):
        """Test invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            OptimizationType("invalid_optimization_type")


class TestOptimizationRule:
    """Test OptimizationRule dataclass functionality."""

    def test_default_initialization(self):
        """Test OptimizationRule with default values."""
        rule = OptimizationRule()

        assert rule.rule_id is not None
        assert isinstance(rule.rule_id, str)
        assert rule.name == ""
        assert rule.optimization_type == OptimizationType.VOLUME_REDUCTION
        assert rule.description == ""
        assert rule.logger_pattern is None
        assert rule.level_threshold is None
        assert rule.message_pattern is None
        assert rule.frequency_limit is None
        assert rule.target_level is None
        assert rule.suppress is False
        assert rule.rate_limit is None
        assert rule.condition is None
        assert rule.priority == 0
        assert rule.enabled is True
        assert rule.production_only is True
        assert rule.estimated_reduction == 0.0

    def test_initialization_with_custom_values(self):
        """Test OptimizationRule with custom values."""
        rule = OptimizationRule(
            rule_id="custom-rule-id",
            name="Test Rule",
            optimization_type=OptimizationType.DEBUG_REMOVAL,
            description="Test description",
            logger_pattern=r"test\.logger",
            level_threshold=logging.DEBUG,
            message_pattern=r"test message",
            frequency_limit=10,
            target_level=logging.WARNING,
            suppress=True,
            rate_limit=5,
            condition="test_condition",
            priority=100,
            enabled=False,
            production_only=False,
            estimated_reduction=0.5,
        )

        assert rule.rule_id == "custom-rule-id"
        assert rule.name == "Test Rule"
        assert rule.optimization_type == OptimizationType.DEBUG_REMOVAL
        assert rule.description == "Test description"
        assert rule.logger_pattern == r"test\.logger"
        assert rule.level_threshold == logging.DEBUG
        assert rule.message_pattern == r"test message"
        assert rule.frequency_limit == 10
        assert rule.target_level == logging.WARNING
        assert rule.suppress is True
        assert rule.rate_limit == 5
        assert rule.condition == "test_condition"
        assert rule.priority == 100
        assert rule.enabled is False
        assert rule.production_only is False
        assert rule.estimated_reduction == 0.5

    def test_unique_rule_ids_generated(self):
        """Test each rule gets a unique ID by default."""
        rule1 = OptimizationRule()
        rule2 = OptimizationRule()

        assert rule1.rule_id != rule2.rule_id
        # Both should be valid UUIDs
        assert uuid.UUID(rule1.rule_id)
        assert uuid.UUID(rule2.rule_id)

    def test_matches_with_no_patterns(self):
        """Test matches method with no filtering patterns."""
        rule = OptimizationRule()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should match everything when no patterns are specified
        assert rule.matches(record) is True

    def test_matches_with_logger_pattern_match(self):
        """Test matches method with matching logger pattern."""
        rule = OptimizationRule(logger_pattern=r"test\..*")
        record = logging.LogRecord(
            name="test.module.submodule",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is True

    def test_matches_with_logger_pattern_no_match(self):
        """Test matches method with non-matching logger pattern."""
        rule = OptimizationRule(logger_pattern=r"other\..*")
        record = logging.LogRecord(
            name="test.module.submodule",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is False

    def test_matches_with_level_threshold_match(self):
        """Test matches method with matching level threshold."""
        rule = OptimizationRule(level_threshold=logging.INFO)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,  # WARNING > INFO
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is True

    def test_matches_with_level_threshold_no_match(self):
        """Test matches method with non-matching level threshold."""
        rule = OptimizationRule(level_threshold=logging.WARNING)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,  # INFO < WARNING
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is False

    def test_matches_with_message_pattern_match(self):
        """Test matches method with matching message pattern."""
        rule = OptimizationRule(message_pattern=r"error.*occurred")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="error has occurred in module",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is True

    def test_matches_with_message_pattern_no_match(self):
        """Test matches method with non-matching message pattern."""
        rule = OptimizationRule(message_pattern=r"error.*occurred")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="success message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is False

    def test_matches_with_formatted_message(self):
        """Test matches method with formatted log message."""
        rule = OptimizationRule(message_pattern=r"Processing item \d+")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing item %d",
            args=(42,),
            exc_info=None,
        )

        assert rule.matches(record) is True

    def test_matches_with_multiple_criteria_all_match(self):
        """Test matches method with multiple criteria that all match."""
        rule = OptimizationRule(
            logger_pattern=r"test\..*",
            level_threshold=logging.INFO,
            message_pattern=r"test.*message",
        )
        record = logging.LogRecord(
            name="test.module",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="test log message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is True

    def test_matches_with_multiple_criteria_partial_match(self):
        """Test matches method with multiple criteria where only some match."""
        rule = OptimizationRule(
            logger_pattern=r"test\..*",
            level_threshold=logging.WARNING,  # This won't match
            message_pattern=r"test.*message",
        )
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,  # INFO < WARNING
            pathname="",
            lineno=0,
            msg="test log message",
            args=(),
            exc_info=None,
        )

        assert rule.matches(record) is False

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


class TestProductionLogFilterBasicInitialization:
    """Test basic ProductionLogFilter initialization without complex processing."""

    def test_initialization_with_empty_rules(self):
        """Test ProductionLogFilter initialization with empty rules list."""
        rules = []
        log_filter = ProductionLogFilter(rules)

        assert log_filter.rules == []
        assert log_filter.settings is None
        assert isinstance(log_filter.message_counts, dict)
        assert isinstance(log_filter.last_reset, datetime)
        assert log_filter.reset_interval.total_seconds() == 300  # 5 minutes
        assert log_filter.filtered_count == 0
        assert log_filter.total_count == 0

    def test_initialization_with_single_rule(self):
        """Test ProductionLogFilter initialization with single rule."""
        rule = OptimizationRule(name="Test Rule", priority=50)
        rules = [rule]
        log_filter = ProductionLogFilter(rules)

        assert len(log_filter.rules) == 1
        assert log_filter.rules[0] == rule

    def test_initialization_with_multiple_rules(self):
        """Test ProductionLogFilter initialization with multiple rules."""
        rule1 = OptimizationRule(name="Rule 1", priority=10)
        rule2 = OptimizationRule(name="Rule 2", priority=50)
        rule3 = OptimizationRule(name="Rule 3", priority=30)
        rules = [rule1, rule2, rule3]

        log_filter = ProductionLogFilter(rules)

        assert len(log_filter.rules) == 3
        # Rules should be sorted by priority in descending order
        assert log_filter.rules[0].priority == 50  # rule2
        assert log_filter.rules[1].priority == 30  # rule3
        assert log_filter.rules[2].priority == 10  # rule1

    def test_initialization_with_settings(self):
        """Test ProductionLogFilter initialization with settings object."""
        mock_settings = MagicMock()
        mock_settings.logging.production_mode = True

        rules = [OptimizationRule(name="Test Rule")]
        log_filter = ProductionLogFilter(rules, settings=mock_settings)

        assert log_filter.settings == mock_settings

    def test_rules_sorting_by_priority(self):
        """Test rules are properly sorted by priority in descending order."""
        rules = [
            OptimizationRule(name="Low Priority", priority=1),
            OptimizationRule(name="High Priority", priority=100),
            OptimizationRule(name="Medium Priority", priority=50),
            OptimizationRule(name="Zero Priority", priority=0),
            OptimizationRule(name="Negative Priority", priority=-10),
        ]

        log_filter = ProductionLogFilter(rules)

        # Check sorting order (highest to lowest priority)
        priorities = [rule.priority for rule in log_filter.rules]
        assert priorities == [100, 50, 1, 0, -10]

    def test_message_counts_initialization(self):
        """Test message_counts is properly initialized as defaultdict."""
        rules = [OptimizationRule()]
        log_filter = ProductionLogFilter(rules)

        # Should return 0 for non-existent keys (defaultdict behavior)
        assert log_filter.message_counts["non_existent_key"] == 0

        # Should allow setting values
        log_filter.message_counts["test_key"] = 5
        assert log_filter.message_counts["test_key"] == 5

    def test_reset_interval_default_value(self):
        """Test default reset interval is 5 minutes."""
        rules = [OptimizationRule()]
        log_filter = ProductionLogFilter(rules)

        assert log_filter.reset_interval.total_seconds() == 300.0  # 5 minutes

    def test_counter_initialization(self):
        """Test performance counters are initialized to zero."""
        rules = [OptimizationRule()]
        log_filter = ProductionLogFilter(rules)

        assert log_filter.filtered_count == 0
        assert log_filter.total_count == 0

    @patch("calendarbot.optimization.production.datetime")
    def test_last_reset_timestamp(self, mock_datetime):
        """Test last_reset is set to current UTC time on initialization."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        rules = [OptimizationRule()]
        log_filter = ProductionLogFilter(rules)

        mock_datetime.now.assert_called_with(timezone.utc)
        assert log_filter.last_reset == fixed_time

    def test_inheritance_from_logging_filter(self):
        """Test ProductionLogFilter inherits from logging.Filter."""
        rules = [OptimizationRule()]
        log_filter = ProductionLogFilter(rules)

        assert isinstance(log_filter, logging.Filter)
        assert hasattr(log_filter, "filter")  # Has filter method from base class

    def test_initialization_preserves_rule_objects(self):
        """Test initialization preserves original rule objects."""
        original_rule = OptimizationRule(
            name="Original Rule", optimization_type=OptimizationType.DEBUG_REMOVAL, priority=42
        )
        rules = [original_rule]

        log_filter = ProductionLogFilter(rules)

        # Should be the same object, not a copy
        assert log_filter.rules[0] is original_rule
        assert log_filter.rules[0].name == "Original Rule"
        assert log_filter.rules[0].optimization_type == OptimizationType.DEBUG_REMOVAL
        assert log_filter.rules[0].priority == 42

    def test_empty_rules_list_handling(self):
        """Test handling of empty rules list doesn't cause errors."""
        log_filter = ProductionLogFilter([])

        # Should initialize normally with empty rules
        assert log_filter.rules == []
        assert hasattr(log_filter, "message_counts")
        assert hasattr(log_filter, "last_reset")
        assert hasattr(log_filter, "filtered_count")
        assert hasattr(log_filter, "total_count")

    def test_rule_priority_edge_cases(self):
        """Test rule sorting with edge case priority values."""
        rules = [
            OptimizationRule(name="Float Priority", priority=10.5),  # Will be converted to int
            OptimizationRule(name="Zero Priority", priority=0),
            OptimizationRule(name="Large Priority", priority=999999),
            OptimizationRule(name="Negative Priority", priority=-100),
        ]

        log_filter = ProductionLogFilter(rules)

        # Should handle all cases without error
        assert len(log_filter.rules) == 4
        # Large priority should be first
        assert log_filter.rules[0].name == "Large Priority"
        # Negative priority should be last
        assert log_filter.rules[-1].name == "Negative Priority"
