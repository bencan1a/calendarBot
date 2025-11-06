"""
Optimized unit tests for the production logging optimization module.

Focuses on core functionality: logging optimization, volume analysis,
debug statement detection, and production filtering.
"""

import ast
import logging
from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from calendarbot.optimization.production import (
    DebugStatementAnalyzer,
    LoggingOptimizer,
    LogVolumeAnalyzer,
    OptimizationRule,
    OptimizationType,
    PrintStatementFinder,
    ProductionLogFilter,
    analyze_log_volume,
    create_production_filter,
    optimize_logging_config,
)


@pytest.fixture
def mock_log_data():
    """Mock log file content for testing."""
    return """2023-01-01 10:00:00 - myapp.database - INFO - Database connection established
2023-01-01 10:00:01 - myapp.database - DEBUG - Query executed: SELECT * FROM users
2023-01-01 10:00:02 - myapp.web - WARNING - Slow request detected
2023-01-01 10:00:03 - myapp.database - DEBUG - Query executed: SELECT * FROM posts
2023-01-01 10:00:04 - urllib3.connectionpool - DEBUG - Starting new HTTP connection
2023-01-01 10:00:05 - myapp.web - ERROR - 404 Not Found
2023-01-01 10:00:06 - myapp.database - DEBUG - Query executed: SELECT * FROM users"""


@pytest.fixture
def mock_python_code():
    """Mock Python code for testing."""
    return '''"""Sample module for testing."""
import logging

logger = logging.getLogger(__name__)

def main():
    print("Starting application")  # TODO: Replace with logging
    logger.info("Application started")
    logger.debug("Debug information")

    try:
        process_data()
    except Exception as e:
        print(f"Error: {e}")  # FIXME: Use proper logging
        logger.error("Processing failed", exc_info=True)

def process_data():
    # HACK: Quick fix for data processing
    logger.debug("Processing data...")
    print("Data processed")'''


@pytest.fixture
def sample_rules():
    """Provide optimized sample rules for testing."""
    return [
        OptimizationRule(
            name="Suppress debug",
            level_threshold=logging.DEBUG,
            suppress=True,
            priority=100,
        ),
        OptimizationRule(
            name="Rate limit warnings",
            level_threshold=logging.WARNING,
            rate_limit=5,
            priority=80,
        ),
    ]


@pytest.fixture
def mock_settings():
    """Provide mock settings object."""
    settings = Mock()
    settings.logging = Mock()
    settings.logging.production_mode = True
    return settings


class TestOptimizationRule:
    """Test OptimizationRule core functionality."""

    def test_optimization_rule_creation(self):
        """Test creating an optimization rule with default values."""
        rule = OptimizationRule()

        assert isinstance(rule.rule_id, str)
        assert rule.name == ""
        assert rule.optimization_type == OptimizationType.VOLUME_REDUCTION
        assert rule.enabled is True
        assert rule.production_only is True
        assert rule.priority == 0

    def test_matches_all_criteria(self):
        """Test rule matching when all criteria must be met."""
        rule = OptimizationRule(
            logger_pattern=r"myapp\.\w+",
            level_threshold=logging.WARNING,
            message_pattern=r"database",
        )

        full_match_record = Mock(spec=logging.LogRecord)
        full_match_record.name = "myapp.database"
        full_match_record.levelno = logging.ERROR
        full_match_record.getMessage.return_value = "database connection error"

        partial_match_record = Mock(spec=logging.LogRecord)
        partial_match_record.name = "myapp.database"
        partial_match_record.levelno = logging.INFO  # Below threshold
        partial_match_record.getMessage.return_value = "database connection error"

        assert rule.matches(full_match_record) is True
        assert rule.matches(partial_match_record) is False


class TestProductionLogFilter:
    """Test ProductionLogFilter core functionality."""

    def test_filter_initialization(self, sample_rules, mock_settings):
        """Test ProductionLogFilter initialization."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)

        assert len(log_filter.rules) == 2
        assert log_filter.settings == mock_settings
        assert isinstance(log_filter.message_counts, defaultdict)
        assert log_filter.filtered_count == 0
        assert log_filter.total_count == 0

        # Rules should be sorted by priority (highest first)
        priorities = [rule.priority for rule in log_filter.rules]
        assert priorities == [100, 80]

    def test_filter_suppression_rule(self, sample_rules, mock_settings):
        """Test log suppression based on rules."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)

        debug_record = Mock(spec=logging.LogRecord)
        debug_record.name = "test.logger"
        debug_record.levelno = logging.DEBUG
        debug_record.levelname = "DEBUG"
        debug_record.getMessage.return_value = "Debug message"

        # Debug record should be suppressed
        result = log_filter.filter(debug_record)
        assert result is False
        assert log_filter.filtered_count == 1
        assert log_filter.total_count == 1

    def test_filter_rate_limiting(self, mock_settings):
        """Test rate limiting functionality."""
        rate_limit_rules = [
            OptimizationRule(
                name="Rate limit warnings",
                level_threshold=logging.WARNING,
                rate_limit=3,  # Reduced for faster testing
                priority=100,
            )
        ]
        log_filter = ProductionLogFilter(rate_limit_rules, mock_settings)

        warning_record = Mock(spec=logging.LogRecord)
        warning_record.name = "test.logger"
        warning_record.levelno = logging.WARNING
        warning_record.levelname = "WARNING"
        warning_record.getMessage.return_value = "Warning message"

        # First 3 warnings should pass through
        for i in range(3):
            result = log_filter.filter(warning_record)
            assert result is True

        # 4th warning should be filtered
        result = log_filter.filter(warning_record)
        assert result is False
        assert log_filter.filtered_count == 1

    def test_get_filter_stats(self, sample_rules, mock_settings):
        """Test filter statistics reporting."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)
        log_filter.total_count = 100
        log_filter.filtered_count = 25

        stats = log_filter.get_filter_stats()

        assert stats["total_processed"] == 100
        assert stats["filtered_count"] == 25
        assert stats["filter_rate"] == 0.25
        assert stats["active_rules"] == 2


class TestLogVolumeAnalyzer:
    """Test LogVolumeAnalyzer with mocked file operations."""

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_dir")
    def test_analyze_log_files_basic(self, mock_is_dir, mock_exists, mock_glob, mock_log_data):
        """Test basic log file analysis with mocked file I/O."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_glob.return_value = [Path("tests/fixtures/app.log")]

        # Mock file operations
        with (
            patch("pathlib.Path.open", mock_open(read_data=mock_log_data)) as mock_file,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_stat.return_value.st_size = len(mock_log_data)
            mock_stat.return_value.st_mtime = 1234567890.0

            analyzer = LogVolumeAnalyzer()
            analysis = analyzer.analyze_log_files("tests/fixtures/logs", hours=24)

        assert "analysis_time" in analysis
        assert analysis["log_directory"] == "tests/fixtures/logs"
        assert analysis["total_files"] == 1
        assert analysis["total_lines"] == 7
        assert analysis["total_size_mb"] > 0

        # Check level aggregation
        assert analysis["by_level"]["DEBUG"] == 4
        assert analysis["by_level"]["INFO"] == 1
        assert analysis["by_level"]["WARNING"] == 1
        assert analysis["by_level"]["ERROR"] == 1

    def test_analyze_nonexistent_directory(self):
        """Test analysis of nonexistent directory."""
        analyzer = LogVolumeAnalyzer()

        analysis = analyzer.analyze_log_files("/nonexistent/path")

        assert "error" in analysis
        assert "does not exist" in analysis["error"]

    def test_generate_recommendations(self):
        """Test recommendation generation based on analysis."""
        analyzer = LogVolumeAnalyzer()

        # Mock analysis data
        analysis = {
            "total_lines": 1000,
            "total_size_mb": 1200,  # >1GB
            "by_level": {"DEBUG": 300, "INFO": 400, "WARNING": 200, "ERROR": 100},
            "by_logger": {"high_volume_logger": 150, "normal_logger": 50},
            "frequent_messages": [
                {"pattern": "Frequent message", "count": 200, "estimated_reduction": 150}
            ],
        }

        recommendations = analyzer._generate_recommendations(analysis)

        # Should have multiple types of recommendations
        recommendation_types = [r["type"] for r in recommendations]
        assert "volume_reduction" in recommendation_types
        assert "level_adjustment" in recommendation_types
        assert "frequency_limiting" in recommendation_types


class TestDebugStatementAnalyzer:
    """Test DebugStatementAnalyzer with mocked file operations."""

    @patch("pathlib.Path.rglob")
    def test_analyze_codebase_basic(self, mock_rglob, mock_python_code):
        """Test basic codebase analysis with mocked file I/O."""
        mock_rglob.return_value = [Path("tests/fixtures/example.py")]

        with patch("pathlib.Path.open", mock_open(read_data=mock_python_code)):
            analyzer = DebugStatementAnalyzer()
            analysis = analyzer.analyze_codebase("/fake/code")

        assert "analysis_time" in analysis
        assert analysis["root_directory"] == "/fake/code"
        assert analysis["python_files"] == 1

        # Check for detected items
        assert len(analysis["print_statements"]) >= 2
        assert len(analysis["debug_logs"]) >= 2
        assert len(analysis["todo_comments"]) >= 3

    def test_generate_code_suggestions(self):
        """Test code optimization suggestion generation."""
        analyzer = DebugStatementAnalyzer()

        # Mock analysis data
        analysis = {
            "print_statements": [
                {"file": "/app/module1.py", "line": 10},
                {"file": "/app/module2.py", "line": 20},
                {"file": "/site-packages/lib.py", "line": 5},  # Should be excluded
            ],
            "debug_logs": [
                {"file": "/app/module1.py", "line": 15},
                {"file": "/app/module1.py", "line": 25},
            ],
            "todo_comments": [
                {"file": "/app/module1.py", "type": "TODO"},
                {"file": "/app/module2.py", "type": "FIXME"},
            ],
        }

        suggestions = analyzer._generate_code_suggestions(analysis)

        # Should generate different types of suggestions
        suggestion_types = [s["type"] for s in suggestions]
        assert "print_removal" in suggestion_types
        assert "debug_review" in suggestion_types
        assert "technical_debt" in suggestion_types

        # Print removal should exclude third-party files
        print_suggestion = next(s for s in suggestions if s["type"] == "print_removal")
        assert print_suggestion["count"] == 2  # Excludes site-packages


class TestPrintStatementFinder:
    """Test PrintStatementFinder AST visitor."""

    def test_find_print_statements(self):
        """Test finding print statements in AST."""
        code = """
def example():
    print("Hello, world!")
    x = 5
    print(f"Value: {x}")
    logger.info("Not a print")
    obj.print("Method call")
"""

        tree = ast.parse(code)
        finder = PrintStatementFinder(Path("tests/fixtures/test.py"))
        finder.visit(tree)

        assert len(finder.print_statements) == 3

        # Check line numbers
        line_numbers = [stmt["line"] for stmt in finder.print_statements]
        assert 3 in line_numbers  # print("Hello, world!")
        assert 5 in line_numbers  # print(f"Value: {x}")
        assert 7 in line_numbers  # obj.print("Method call")


class TestLoggingOptimizer:
    """Test LoggingOptimizer main class."""

    def test_optimizer_initialization(self, mock_settings):
        """Test LoggingOptimizer initialization."""
        optimizer = LoggingOptimizer(mock_settings)

        assert optimizer.settings == mock_settings
        assert len(optimizer.rules) >= 4  # Default rules loaded
        assert isinstance(optimizer.volume_analyzer, LogVolumeAnalyzer)
        assert isinstance(optimizer.debug_analyzer, DebugStatementAnalyzer)

    def test_add_rule(self, mock_settings):
        """Test adding custom optimization rules."""
        optimizer = LoggingOptimizer(mock_settings)
        initial_count = len(optimizer.rules)

        custom_rule = OptimizationRule(name="Custom rule", priority=200, suppress=True)
        optimizer.add_rule(custom_rule)

        assert len(optimizer.rules) == initial_count + 1
        # Should be sorted by priority, so custom rule should be first
        assert optimizer.rules[0].name == "Custom rule"

    def test_optimize_logging_config_basic(self, mock_settings):
        """Test basic logging configuration optimization."""
        optimizer = LoggingOptimizer(mock_settings)

        config = {
            "root": {"level": "DEBUG"},
            "loggers": {"urllib3": {"level": "DEBUG"}, "myapp": {"level": "INFO"}},
            "handlers": {
                "console": {"class": "logging.StreamHandler"},
                "file": {"class": "logging.FileHandler", "filename": "app.log"},
            },
        }

        optimized = optimizer.optimize_logging_config(config)

        # Root level should be adjusted
        assert optimized["root"]["level"] == "INFO"

        # Handlers should have production filter added
        for handler_config in optimized["handlers"].values():
            assert "production_optimizer" in handler_config.get("filters", [])

        # Should add filter configuration
        assert "filters" in optimized
        assert "production_optimizer" in optimized["filters"]


class TestUtilityFunctions:
    """Test module-level utility functions."""

    def test_create_production_filter(self):
        """Test creating production filter from rule configurations."""
        rule_configs = [
            {
                "name": "Test rule",
                "optimization_type": "debug_removal",
                "suppress": True,
                "priority": 100,
                "enabled": True,
            }
        ]

        filter_instance = create_production_filter(rule_configs)

        assert isinstance(filter_instance, ProductionLogFilter)
        assert len(filter_instance.rules) == 1
        assert filter_instance.rules[0].name == "Test rule"
        assert filter_instance.rules[0].optimization_type == OptimizationType.DEBUG_REMOVAL

    def test_optimize_logging_config_function(self):
        """Test the optimize_logging_config convenience function."""
        config = {"root": {"level": "DEBUG"}}

        optimized = optimize_logging_config(config)

        assert optimized["root"]["level"] == "INFO"
        assert "filters" in optimized

    @patch("calendarbot.optimization.production.LogVolumeAnalyzer.analyze_log_files")
    def test_analyze_log_volume_function(self, mock_analyze):
        """Test the analyze_log_volume convenience function."""
        mock_analyze.return_value = {"total_lines": 1000}

        result = analyze_log_volume("/fake/path", hours=12)

        mock_analyze.assert_called_once_with("/fake/path", 12)
        assert result["total_lines"] == 1000


class TestPerformanceOptimization:
    """Test performance-related optimizations."""

    def test_filter_performance_tracking(self):
        """Test that filter tracks performance metrics efficiently."""
        rules = [OptimizationRule(suppress=True, priority=100)]
        log_filter = ProductionLogFilter(rules)

        # Process multiple records efficiently
        for i in range(50):  # Reduced from 100 for speed
            record = Mock(spec=logging.LogRecord)
            record.name = "test.logger"
            record.levelno = logging.INFO
            record.levelname = "INFO"
            record.getMessage.return_value = f"Message {i}"

            log_filter.filter(record)

        stats = log_filter.get_filter_stats()
        assert stats["total_processed"] == 50
        assert stats["filtered_count"] == 50  # All suppressed
        assert stats["filter_rate"] == 1.0

    def test_high_volume_logging_scenario(self):
        """Test filtering behavior under high-volume logging."""
        rules = [
            OptimizationRule(
                name="Rate limit info", level_threshold=logging.INFO, rate_limit=5, priority=100
            ),
            OptimizationRule(
                name="Suppress debug", level_threshold=logging.DEBUG, suppress=True, priority=200
            ),
        ]

        log_filter = ProductionLogFilter(rules)

        # Simulate mixed logging - reduced volume for speed
        passed_count = 0
        filtered_count = 0

        for i in range(100):  # Reduced from 1000
            if i % 10 == 0:
                # Debug record (should be suppressed)
                record = Mock(spec=logging.LogRecord)
                record.name = "app.debug"
                record.levelno = logging.DEBUG
                record.levelname = "DEBUG"
                record.getMessage.return_value = f"Debug {i}"
            else:
                # Info record (should be rate limited)
                record = Mock(spec=logging.LogRecord)
                record.name = "app.info"
                record.levelno = logging.INFO
                record.levelname = "INFO"
                record.getMessage.return_value = "Repeated info message"

            if log_filter.filter(record):
                passed_count += 1
            else:
                filtered_count += 1

        # Should filter significant portion of logs
        total_processed = passed_count + filtered_count
        filter_rate = filtered_count / total_processed

        assert total_processed == 100
        assert filter_rate > 0.8  # Should filter >80% in this scenario
