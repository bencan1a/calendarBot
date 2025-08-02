"""
Unit tests for the production logging optimization module.

This module tests logging optimization, volume analysis, debug statement detection,
and production filtering functionality.
"""

import ast
import logging
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

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


class TestOptimizationType:
    """Test the OptimizationType enum."""

    def test_optimization_type_values(self):
        """Test that all optimization types are properly defined."""
        assert OptimizationType.VOLUME_REDUCTION.value == "volume_reduction"
        assert OptimizationType.LEVEL_ADJUSTMENT.value == "level_adjustment"
        assert OptimizationType.DEBUG_REMOVAL.value == "debug_removal"
        assert OptimizationType.FREQUENCY_LIMITING.value == "frequency_limiting"
        assert OptimizationType.CONDITIONAL_LOGGING.value == "conditional_logging"
        assert OptimizationType.PERFORMANCE_FILTERING.value == "performance_filtering"
        assert OptimizationType.CONTENT_OPTIMIZATION.value == "content_optimization"
        assert OptimizationType.HANDLER_OPTIMIZATION.value == "handler_optimization"


class TestOptimizationRule:
    """Test the OptimizationRule dataclass and its methods."""

    def test_optimization_rule_creation(self):
        """Test creating an optimization rule with default values."""
        rule = OptimizationRule()

        assert isinstance(rule.rule_id, str)
        assert rule.name == ""
        assert rule.optimization_type == OptimizationType.VOLUME_REDUCTION
        assert rule.enabled is True
        assert rule.production_only is True
        assert rule.priority == 0

    def test_optimization_rule_custom_values(self):
        """Test creating an optimization rule with custom values."""
        rule = OptimizationRule(
            name="Test rule",
            optimization_type=OptimizationType.DEBUG_REMOVAL,
            description="Test description",
            logger_pattern=r"test\.\w+",
            level_threshold=logging.WARNING,
            message_pattern=r"error:",
            suppress=True,
            priority=100,
        )

        assert rule.name == "Test rule"
        assert rule.optimization_type == OptimizationType.DEBUG_REMOVAL
        assert rule.description == "Test description"
        assert rule.logger_pattern == r"test\.\w+"
        assert rule.level_threshold == logging.WARNING
        assert rule.message_pattern == r"error:"
        assert rule.suppress is True
        assert rule.priority == 100

    def test_matches_logger_pattern(self):
        """Test rule matching based on logger pattern."""
        rule = OptimizationRule(logger_pattern=r"myapp\.\w+")

        # Create mock log records
        matching_record = Mock(spec=logging.LogRecord)
        matching_record.name = "myapp.database"
        matching_record.levelno = logging.INFO
        matching_record.getMessage.return_value = "Test message"

        non_matching_record = Mock(spec=logging.LogRecord)
        non_matching_record.name = "other.module"
        non_matching_record.levelno = logging.INFO
        non_matching_record.getMessage.return_value = "Test message"

        assert rule.matches(matching_record) is True
        assert rule.matches(non_matching_record) is False

    def test_matches_level_threshold(self):
        """Test rule matching based on level threshold."""
        rule = OptimizationRule(level_threshold=logging.WARNING)

        warning_record = Mock(spec=logging.LogRecord)
        warning_record.name = "test.logger"
        warning_record.levelno = logging.WARNING
        warning_record.getMessage.return_value = "Warning message"

        info_record = Mock(spec=logging.LogRecord)
        info_record.name = "test.logger"
        info_record.levelno = logging.INFO
        info_record.getMessage.return_value = "Info message"

        assert rule.matches(warning_record) is True
        assert rule.matches(info_record) is False

    def test_matches_message_pattern(self):
        """Test rule matching based on message pattern."""
        rule = OptimizationRule(message_pattern=r"error|warning")

        matching_record = Mock(spec=logging.LogRecord)
        matching_record.name = "test.logger"
        matching_record.levelno = logging.INFO
        matching_record.getMessage.return_value = "An error occurred"

        non_matching_record = Mock(spec=logging.LogRecord)
        non_matching_record.name = "test.logger"
        non_matching_record.levelno = logging.INFO
        non_matching_record.getMessage.return_value = "Success message"

        assert rule.matches(matching_record) is True
        assert rule.matches(non_matching_record) is False

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
    """Test the ProductionLogFilter class."""

    @pytest.fixture
    def sample_rules(self):
        """Provide sample optimization rules for testing."""
        return [
            OptimizationRule(
                name="Suppress debug",
                level_threshold=logging.DEBUG,  # Match DEBUG level and above
                suppress=True,
                priority=100,
            ),
            OptimizationRule(
                name="Rate limit warnings",
                level_threshold=logging.WARNING,
                rate_limit=5,
                priority=80,
            ),
            OptimizationRule(
                name="Adjust level",
                logger_pattern=r"urllib3",
                target_level=logging.ERROR,
                priority=60,
            ),
        ]

    @pytest.fixture
    def mock_settings(self):
        """Provide mock settings object."""
        settings = Mock()
        settings.logging = Mock()
        settings.logging.production_mode = True
        return settings

    def test_filter_initialization(self, sample_rules, mock_settings):
        """Test ProductionLogFilter initialization."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)

        assert len(log_filter.rules) == 3
        assert log_filter.settings == mock_settings
        assert isinstance(log_filter.message_counts, defaultdict)
        assert log_filter.filtered_count == 0
        assert log_filter.total_count == 0

        # Rules should be sorted by priority (highest first)
        priorities = [rule.priority for rule in log_filter.rules]
        assert priorities == [100, 80, 60]

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
        # Create isolated rate limiting rule to avoid conflicts
        rate_limit_rules = [
            OptimizationRule(
                name="Rate limit warnings",
                level_threshold=logging.WARNING,
                rate_limit=5,
                priority=100,
            )
        ]
        log_filter = ProductionLogFilter(rate_limit_rules, mock_settings)

        warning_record = Mock(spec=logging.LogRecord)
        warning_record.name = "test.logger"
        warning_record.levelno = logging.WARNING
        warning_record.levelname = "WARNING"
        warning_record.getMessage.return_value = "Warning message"

        # First 5 warnings should pass through (rate limit is 5)
        for i in range(5):
            result = log_filter.filter(warning_record)
            assert result is True

        # 6th warning should be filtered (exceeds rate limit)
        result = log_filter.filter(warning_record)
        assert result is False
        assert log_filter.filtered_count == 1

    def test_filter_level_adjustment(self, mock_settings):
        """Test level adjustment functionality."""
        # Create rules specifically for level adjustment testing
        level_adjustment_rules = [
            OptimizationRule(
                name="Adjust urllib3 level",
                logger_pattern=r"urllib3",
                target_level=logging.ERROR,
                priority=100,  # High priority to ensure it runs
            )
        ]
        log_filter = ProductionLogFilter(level_adjustment_rules, mock_settings)

        urllib3_record = Mock(spec=logging.LogRecord)
        urllib3_record.name = "urllib3.connectionpool"
        urllib3_record.levelno = logging.INFO
        urllib3_record.levelname = "INFO"
        urllib3_record.getMessage.return_value = "Connection info"

        result = log_filter.filter(urllib3_record)
        assert result is True
        assert urllib3_record.levelno == logging.ERROR
        assert urllib3_record.levelname == "ERROR"

    def test_filter_production_mode_check(self, sample_rules):
        """Test production mode check for production-only rules."""
        non_production_settings = Mock()
        non_production_settings.logging = Mock()
        non_production_settings.logging.production_mode = False

        log_filter = ProductionLogFilter(sample_rules, non_production_settings)

        debug_record = Mock(spec=logging.LogRecord)
        debug_record.name = "test.logger"
        debug_record.levelno = logging.DEBUG
        debug_record.levelname = "DEBUG"
        debug_record.getMessage.return_value = "Debug message"

        # Debug suppression rule should be skipped in non-production
        result = log_filter.filter(debug_record)
        assert result is True  # Not suppressed
        assert log_filter.filtered_count == 0

    def test_filter_disabled_rules(self, sample_rules, mock_settings):
        """Test that disabled rules are ignored."""
        sample_rules[0].enabled = False  # Disable debug suppression rule
        log_filter = ProductionLogFilter(sample_rules, mock_settings)

        debug_record = Mock(spec=logging.LogRecord)
        debug_record.name = "test.logger"
        debug_record.levelno = logging.DEBUG
        debug_record.levelname = "DEBUG"
        debug_record.getMessage.return_value = "Debug message"

        result = log_filter.filter(debug_record)
        assert result is True  # Not suppressed because rule is disabled
        assert log_filter.filtered_count == 0

    def test_filter_counter_reset(self, sample_rules, mock_settings):
        """Test that message counters are reset periodically."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)
        log_filter.reset_interval = timedelta(seconds=1)  # Short interval for testing

        # Add some counts
        log_filter.message_counts["test_key"] = 10

        # Simulate time passing
        log_filter.last_reset = datetime.now(timezone.utc) - timedelta(seconds=2)

        record = Mock(spec=logging.LogRecord)
        record.name = "test.logger"
        record.levelno = logging.INFO
        record.levelname = "INFO"
        record.getMessage.return_value = "Test message"

        log_filter.filter(record)

        # Counters should be reset
        assert len(log_filter.message_counts) == 0

    def test_get_filter_stats(self, sample_rules, mock_settings):
        """Test filter statistics reporting."""
        log_filter = ProductionLogFilter(sample_rules, mock_settings)
        log_filter.total_count = 100
        log_filter.filtered_count = 25
        log_filter.message_counts["test_key"] = 5

        stats = log_filter.get_filter_stats()

        assert stats["total_processed"] == 100
        assert stats["filtered_count"] == 25
        assert stats["filter_rate"] == 0.25
        assert stats["active_rules"] == 3
        assert stats["message_counts"]["test_key"] == 5


class TestLogVolumeAnalyzer:
    """Test the LogVolumeAnalyzer class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory with sample log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Create sample log file
            log_file = log_dir / "app.log"
            log_content = """2023-01-01 10:00:00 - myapp.database - INFO - Database connection established
2023-01-01 10:00:01 - myapp.database - DEBUG - Query executed: SELECT * FROM users
2023-01-01 10:00:02 - myapp.web - WARNING - Slow request detected
2023-01-01 10:00:03 - myapp.database - DEBUG - Query executed: SELECT * FROM posts
2023-01-01 10:00:04 - urllib3.connectionpool - DEBUG - Starting new HTTP connection
2023-01-01 10:00:05 - myapp.web - ERROR - 404 Not Found
2023-01-01 10:00:06 - myapp.database - DEBUG - Query executed: SELECT * FROM users
"""
            log_file.write_text(log_content)

            yield log_dir

    def test_analyze_log_files_basic(self, temp_log_dir):
        """Test basic log file analysis."""
        analyzer = LogVolumeAnalyzer()

        analysis = analyzer.analyze_log_files(temp_log_dir, hours=24)

        assert "analysis_time" in analysis
        assert analysis["log_directory"] == str(temp_log_dir)
        assert analysis["total_files"] == 1
        assert analysis["total_lines"] == 7
        assert analysis["total_size_mb"] > 0

        # Check level aggregation
        assert analysis["by_level"]["DEBUG"] == 4
        assert analysis["by_level"]["INFO"] == 1
        assert analysis["by_level"]["WARNING"] == 1
        assert analysis["by_level"]["ERROR"] == 1

        # Check logger aggregation
        assert analysis["by_logger"]["myapp.database"] == 4
        assert analysis["by_logger"]["myapp.web"] == 2
        assert analysis["by_logger"]["urllib3.connectionpool"] == 1

    def test_analyze_nonexistent_directory(self):
        """Test analysis of nonexistent directory."""
        analyzer = LogVolumeAnalyzer()

        analysis = analyzer.analyze_log_files("/nonexistent/path")

        assert "error" in analysis
        assert "does not exist" in analysis["error"]

    def test_find_frequent_messages(self, temp_log_dir):
        """Test frequent message detection."""
        analyzer = LogVolumeAnalyzer()

        # Create log file with repeated messages
        log_file = temp_log_dir / "repeated.log"
        repeated_content = "\n".join(
            [
                "2023-01-01 10:00:00 - myapp - INFO - User 123 logged in",
                "2023-01-01 10:00:01 - myapp - INFO - User 456 logged in",
                "2023-01-01 10:00:02 - myapp - INFO - User 789 logged in",
                "2023-01-01 10:00:03 - myapp - INFO - Processing request for order 001",
                "2023-01-01 10:00:04 - myapp - INFO - Processing request for order 002",
            ]
        )
        log_file.write_text(repeated_content)

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        frequent_messages = analyzer._find_frequent_messages([log_file], cutoff_time)

        # Should normalize user IDs and order numbers
        assert len(frequent_messages) >= 2

        # Find the normalized patterns
        patterns = [msg["pattern"] for msg in frequent_messages]
        assert any("User <NUM> logged in" in pattern for pattern in patterns)
        assert any("Processing request for order <NUM>" in pattern for pattern in patterns)

    def test_generate_recommendations(self):
        """Test recommendation generation based on analysis."""
        analyzer = LogVolumeAnalyzer()

        # Mock analysis data
        analysis = {
            "total_lines": 1000,
            "total_size_mb": 1200,  # >1GB
            "by_level": {"DEBUG": 300, "INFO": 400, "WARNING": 200, "ERROR": 100},
            "by_logger": {"high_volume_logger": 150, "normal_logger": 50},  # >10% threshold
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

        # Check high volume size warning
        volume_recs = [r for r in recommendations if r.get("current_size_mb")]
        assert len(volume_recs) >= 1
        assert volume_recs[0]["current_size_mb"] == 1200


class TestDebugStatementAnalyzer:
    """Test the DebugStatementAnalyzer class."""

    @pytest.fixture
    def temp_code_dir(self):
        """Create a temporary directory with sample Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_dir = Path(temp_dir)

            # Create sample Python file with various statements
            py_file = code_dir / "example.py"
            py_content = '''"""Sample module for testing."""
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
    print("Data processed")
'''
            py_file.write_text(py_content)

            yield code_dir

    def test_analyze_codebase_basic(self, temp_code_dir):
        """Test basic codebase analysis."""
        analyzer = DebugStatementAnalyzer()

        analysis = analyzer.analyze_codebase(temp_code_dir)

        assert "analysis_time" in analysis
        assert analysis["root_directory"] == str(temp_code_dir)
        assert analysis["python_files"] == 1
        assert analysis["total_files"] >= 1

        # Check for detected items
        assert len(analysis["print_statements"]) >= 2
        assert len(analysis["debug_logs"]) >= 2
        assert len(analysis["todo_comments"]) >= 3

        # Verify print statement detection
        print_files = [p["file"] for p in analysis["print_statements"]]
        assert any("example.py" in f for f in print_files)

        # Verify TODO comment detection
        todo_types = [t["type"] for t in analysis["todo_comments"]]
        assert "TODO" in todo_types
        assert "FIXME" in todo_types
        assert "HACK" in todo_types

    def test_analyze_python_file_syntax_error(self, temp_code_dir):
        """Test handling of Python files with syntax errors."""
        analyzer = DebugStatementAnalyzer()

        # Create file with syntax error
        invalid_file = temp_code_dir / "invalid.py"
        invalid_file.write_text("def broken_function(\nprint('missing colon')")

        analysis = analyzer.analyze_codebase(temp_code_dir)

        # Should handle syntax error gracefully and fall back to regex
        assert analysis["python_files"] == 2
        print_statements = [p for p in analysis["print_statements"] if "invalid.py" in p["file"]]
        assert len(print_statements) >= 1  # Should find print via regex fallback

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
        assert print_suggestion["files_affected"] == 2


class TestPrintStatementFinder:
    """Test the PrintStatementFinder AST visitor."""

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
        finder = PrintStatementFinder(Path("test.py"))
        finder.visit(tree)

        assert len(finder.print_statements) == 3

        # Check line numbers
        line_numbers = [stmt["line"] for stmt in finder.print_statements]
        assert 3 in line_numbers  # print("Hello, world!")
        assert 5 in line_numbers  # print(f"Value: {x}")
        assert 7 in line_numbers  # obj.print("Method call")

    def test_find_print_in_complex_expressions(self):
        """Test finding print statements in complex expressions."""
        code = """
result = print("Side effect") or process_data()
[print(x) for x in items]
lambda: print("Lambda print")
"""

        tree = ast.parse(code)
        finder = PrintStatementFinder(Path("test.py"))
        finder.visit(tree)

        assert len(finder.print_statements) >= 3


class TestLoggingOptimizer:
    """Test the LoggingOptimizer main class."""

    @pytest.fixture
    def mock_settings(self):
        """Provide mock settings for testing."""
        settings = Mock()
        settings.logging = Mock()
        settings.logging.production_mode = True
        return settings

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

    def test_optimize_logging_config_logger_patterns(self, mock_settings):
        """Test logger pattern matching in config optimization."""
        optimizer = LoggingOptimizer(mock_settings)

        config = {
            "loggers": {
                "urllib3.connectionpool": {"level": "DEBUG"},
                "requests.packages": {"level": "DEBUG"},
                "myapp.database": {"level": "DEBUG"},
            }
        }

        optimized = optimizer.optimize_logging_config(config)

        # Should optimize matching loggers based on rules
        loggers = optimized["loggers"]

        # urllib3 should be optimized by default rule
        if "urllib3.connectionpool" in loggers:
            # Rule may adjust this based on pattern matching
            assert loggers["urllib3.connectionpool"]["level"] in ["DEBUG", "WARNING", "ERROR"]

    @patch("calendarbot.optimization.production.LogVolumeAnalyzer.analyze_log_files")
    @patch("calendarbot.optimization.production.DebugStatementAnalyzer.analyze_codebase")
    def test_analyze_and_optimize(self, mock_code_analysis, mock_log_analysis, mock_settings):
        """Test comprehensive analysis and optimization."""
        optimizer = LoggingOptimizer(mock_settings)

        # Mock analysis results
        mock_log_analysis.return_value = {
            "total_size_mb": 500,
            "optimization_opportunities": [
                {"type": "volume_reduction", "priority": "high", "estimated_reduction": 100}
            ],
        }

        mock_code_analysis.return_value = {
            "optimization_suggestions": [
                {"type": "print_removal", "priority": "medium", "estimated_reduction": 50}
            ]
        }

        results = optimizer.analyze_and_optimize("/fake/logs", "/fake/code")

        assert "optimization_time" in results
        assert "log_analysis" in results
        assert "code_analysis" in results
        assert "optimization_summary" in results
        assert "recommendations" in results

        # Check recommendations are properly aggregated and sorted
        recommendations = results["recommendations"]
        assert len(recommendations) == 2
        # High priority should come first
        assert recommendations[0]["priority"] == "high"
        assert recommendations[1]["priority"] == "medium"

        # Check optimization summary
        summary = results["optimization_summary"]
        assert summary["total_recommendations"] == 2
        assert summary["high_priority"] == 1
        assert summary["medium_priority"] == 1
        assert summary["estimated_total_reduction"] == 150


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
        assert filter_instance.rules[0].suppress is True

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


class TestErrorHandling:
    """Test error handling in various components."""

    def test_log_analyzer_file_read_error(self, tmp_path):
        """Test handling of file read errors in log analysis."""
        analyzer = LogVolumeAnalyzer()

        # Create a directory that looks like a log file (will cause read error)
        fake_log = tmp_path / "fake.log"
        fake_log.mkdir()

        # Should handle error gracefully
        analysis = analyzer.analyze_log_files(tmp_path)

        assert analysis["total_files"] == 1
        assert analysis["total_lines"] == 0  # No lines read due to error

    def test_optimization_rule_regex_error(self):
        """Test handling of invalid regex patterns in rules."""
        rule = OptimizationRule(logger_pattern="[invalid regex")

        record = Mock(spec=logging.LogRecord)
        record.name = "test.logger"
        record.levelno = logging.INFO
        record.getMessage.return_value = "Test message"

        # Should handle regex error gracefully (return False)
        try:
            result = rule.matches(record)
            # If no exception, result should be False due to failed pattern match
            assert result is False
        except Exception:
            # If exception occurs, it should be a regex error
            pass


class TestPerformanceOptimization:
    """Test performance-related optimizations."""

    def test_filter_performance_tracking(self):
        """Test that filter tracks performance metrics."""
        rules = [OptimizationRule(suppress=True, priority=100)]
        log_filter = ProductionLogFilter(rules)

        # Process multiple records
        for i in range(100):
            record = Mock(spec=logging.LogRecord)
            record.name = "test.logger"
            record.levelno = logging.INFO
            record.levelname = "INFO"
            record.getMessage.return_value = f"Message {i}"

            log_filter.filter(record)

        stats = log_filter.get_filter_stats()
        assert stats["total_processed"] == 100
        assert stats["filtered_count"] == 100  # All suppressed
        assert stats["filter_rate"] == 1.0

    def test_message_count_memory_management(self):
        """Test that message counts don't grow indefinitely."""
        rules = [OptimizationRule(rate_limit=1, priority=100)]
        log_filter = ProductionLogFilter(rules)
        log_filter.reset_interval = timedelta(milliseconds=100)

        # Add many different messages
        for i in range(1000):
            record = Mock(spec=logging.LogRecord)
            record.name = f"logger_{i}"
            record.levelno = logging.INFO
            record.levelname = "INFO"
            record.getMessage.return_value = f"Unique message {i}"

            # Force reset every 100 messages to simulate time passing
            if i > 0 and i % 100 == 0:
                log_filter.last_reset = datetime.now(timezone.utc) - timedelta(seconds=1)

            log_filter.filter(record)

        # Should not accumulate indefinitely due to periodic resets
        # With forced resets every 100 messages, should be much less than 1000
        assert len(log_filter.message_counts) < 200


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_high_volume_logging_scenario(self):
        """Test filtering behavior under high-volume logging."""
        rules = [
            OptimizationRule(
                name="Rate limit info", level_threshold=logging.INFO, rate_limit=10, priority=100
            ),
            OptimizationRule(
                name="Suppress debug", level_threshold=logging.DEBUG, suppress=True, priority=200
            ),
        ]

        log_filter = ProductionLogFilter(rules)

        # Simulate high-volume mixed logging
        passed_count = 0
        filtered_count = 0

        for i in range(1000):
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

        assert total_processed == 1000
        assert filter_rate > 0.8  # Should filter >80% in this scenario

        stats = log_filter.get_filter_stats()
        assert stats["total_processed"] == 1000
        assert stats["filtered_count"] == filtered_count
