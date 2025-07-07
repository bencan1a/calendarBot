"""Unit tests for calendarbot.optimization.production module."""

import ast
import logging
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

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
    """Test OptimizationType enum."""

    def test_optimization_type_values(self):
        """Test that all expected optimization types are defined."""
        expected_types = [
            "volume_reduction",
            "level_adjustment",
            "debug_removal",
            "frequency_limiting",
            "conditional_logging",
            "performance_filtering",
            "content_optimization",
            "handler_optimization",
        ]

        for expected_type in expected_types:
            assert hasattr(OptimizationType, expected_type.upper())
            assert getattr(OptimizationType, expected_type.upper()).value == expected_type


class TestOptimizationRule:
    """Test OptimizationRule dataclass."""

    def test_optimization_rule_initialization(self):
        """Test OptimizationRule initialization with default values."""
        rule = OptimizationRule()

        assert rule.rule_id is not None
        assert rule.name == ""
        assert rule.optimization_type == OptimizationType.VOLUME_REDUCTION
        assert rule.description == ""
        assert rule.logger_pattern is None
        assert rule.level_threshold is None
        assert rule.message_pattern is None
        assert rule.frequency_limit is None
        assert rule.target_level is None
        assert rule.suppress == False
        assert rule.rate_limit is None
        assert rule.condition is None
        assert rule.priority == 0
        assert rule.enabled == True
        assert rule.production_only == True
        assert rule.estimated_reduction == 0.0

    def test_optimization_rule_custom_values(self):
        """Test OptimizationRule initialization with custom values."""
        rule = OptimizationRule(
            name="Test Rule",
            optimization_type=OptimizationType.DEBUG_REMOVAL,
            description="Test description",
            logger_pattern=r"test\..*",
            level_threshold=logging.DEBUG,
            message_pattern=r"debug.*",
            frequency_limit=10,
            target_level=logging.WARNING,
            suppress=True,
            rate_limit=5,
            condition="production",
            priority=100,
            enabled=False,
            production_only=False,
            estimated_reduction=0.5,
        )

        assert rule.name == "Test Rule"
        assert rule.optimization_type == OptimizationType.DEBUG_REMOVAL
        assert rule.description == "Test description"
        assert rule.logger_pattern == r"test\..*"
        assert rule.level_threshold == logging.DEBUG
        assert rule.message_pattern == r"debug.*"
        assert rule.frequency_limit == 10
        assert rule.target_level == logging.WARNING
        assert rule.suppress == True
        assert rule.rate_limit == 5
        assert rule.condition == "production"
        assert rule.priority == 100
        assert rule.enabled == False
        assert rule.production_only == False
        assert rule.estimated_reduction == 0.5

    def test_optimization_rule_matches_logger_pattern(self):
        """Test OptimizationRule matches method with logger pattern."""
        rule = OptimizationRule(logger_pattern=r"test\..*")

        # Create mock log record
        record = Mock()
        record.name = "test.module"
        record.levelno = logging.INFO
        record.getMessage.return_value = "Test message"

        assert rule.matches(record) == True

        record.name = "other.module"
        assert rule.matches(record) == False

    def test_optimization_rule_matches_level_threshold(self):
        """Test OptimizationRule matches method with level threshold."""
        rule = OptimizationRule(level_threshold=logging.WARNING)

        record = Mock()
        record.name = "test.module"
        record.getMessage.return_value = "Test message"

        record.levelno = logging.ERROR
        assert rule.matches(record) == True

        record.levelno = logging.INFO
        assert rule.matches(record) == False

    def test_optimization_rule_matches_message_pattern(self):
        """Test OptimizationRule matches method with message pattern."""
        rule = OptimizationRule(message_pattern=r"debug.*")

        record = Mock()
        record.name = "test.module"
        record.levelno = logging.INFO

        record.getMessage.return_value = "debug information"
        assert rule.matches(record) == True

        record.getMessage.return_value = "info message"
        assert rule.matches(record) == False

    def test_optimization_rule_matches_all_criteria(self):
        """Test OptimizationRule matches method with all criteria."""
        rule = OptimizationRule(
            logger_pattern=r"test\..*", level_threshold=logging.WARNING, message_pattern=r"error.*"
        )

        record = Mock()
        record.name = "test.module"
        record.levelno = logging.ERROR
        record.getMessage.return_value = "error occurred"

        assert rule.matches(record) == True

        # Test partial match failure
        record.name = "other.module"
        assert rule.matches(record) == False


class TestProductionLogFilter:
    """Test ProductionLogFilter class."""

    @pytest.fixture
    def sample_rules(self):
        """Create sample optimization rules for testing."""
        return [
            OptimizationRule(
                name="Suppress Debug", level_threshold=logging.DEBUG, suppress=True, priority=100
            ),
            OptimizationRule(
                name="Rate Limit", logger_pattern=r"test\..*", rate_limit=5, priority=80
            ),
            OptimizationRule(
                name="Level Adjustment",
                logger_pattern=r"urllib3.*",
                target_level=logging.WARNING,
                priority=60,
            ),
        ]

    def test_production_log_filter_initialization(self, sample_rules):
        """Test ProductionLogFilter initialization."""
        filter_instance = ProductionLogFilter(sample_rules)

        assert len(filter_instance.rules) == 3
        assert filter_instance.rules[0].priority == 100  # Should be sorted by priority
        assert filter_instance.filtered_count == 0
        assert filter_instance.total_count == 0
        assert isinstance(filter_instance.message_counts, defaultdict)

    def test_production_log_filter_suppression(self, sample_rules):
        """Test ProductionLogFilter suppression rule."""
        filter_instance = ProductionLogFilter(sample_rules)

        # Create debug log record
        record = Mock()
        record.name = "test.module"
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"
        record.getMessage.return_value = "Debug message"

        # Should be suppressed
        result = filter_instance.filter(record)
        assert result == False
        assert filter_instance.filtered_count == 1
        assert filter_instance.total_count == 1

    def test_production_log_filter_rate_limiting(self, sample_rules):
        """Test ProductionLogFilter rate limiting."""
        # Create a filter with only the rate limiting rule to avoid interference
        rate_limit_rule = [rule for rule in sample_rules if rule.name == "Rate Limit"][0]
        filter_instance = ProductionLogFilter([rate_limit_rule])

        # Create test log record
        record = Mock()
        record.name = "test.module"
        record.levelno = logging.INFO
        record.levelname = "INFO"
        record.getMessage.return_value = "Repeated message"

        # First 5 messages should pass
        for i in range(5):
            result = filter_instance.filter(record)
            assert result == True

        # 6th message should be filtered
        result = filter_instance.filter(record)
        assert result == False
        assert filter_instance.filtered_count == 1

    def test_production_log_filter_level_adjustment(self, sample_rules):
        """Test ProductionLogFilter level adjustment."""
        # Create a filter with only the level adjustment rule to avoid interference
        level_adjust_rule = [rule for rule in sample_rules if rule.name == "Level Adjustment"][0]
        filter_instance = ProductionLogFilter([level_adjust_rule])

        # Create urllib3 log record
        record = Mock()
        record.name = "urllib3.connectionpool"
        record.levelno = logging.INFO
        record.levelname = "INFO"
        record.getMessage.return_value = "Connection message"

        result = filter_instance.filter(record)
        assert result == True
        assert record.levelno == logging.WARNING
        assert record.levelname == "WARNING"

    def test_production_log_filter_counter_reset(self, sample_rules):
        """Test ProductionLogFilter counter reset functionality."""
        filter_instance = ProductionLogFilter(sample_rules)

        # Set a past reset time to trigger reset
        filter_instance.last_reset = datetime.utcnow() - timedelta(minutes=10)

        record = Mock()
        record.name = "test.module"
        record.levelno = logging.INFO
        record.levelname = "INFO"
        record.getMessage.return_value = "Test message"

        filter_instance.filter(record)

        # Should have reset the counters
        assert len(filter_instance.message_counts) == 0

    def test_production_log_filter_get_filter_stats(self, sample_rules):
        """Test ProductionLogFilter get_filter_stats method."""
        filter_instance = ProductionLogFilter(sample_rules)

        # Process some records
        record = Mock()
        record.name = "test.module"
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"
        record.getMessage.return_value = "Debug message"

        filter_instance.filter(record)  # This should be suppressed

        stats = filter_instance.get_filter_stats()

        assert stats["total_processed"] == 1
        assert stats["filtered_count"] == 1
        assert stats["filter_rate"] == 1.0
        assert stats["active_rules"] == 3
        assert "message_counts" in stats


class TestLogVolumeAnalyzer:
    """Test LogVolumeAnalyzer class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory with test log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)

            # Create test log files
            log1 = log_dir / "test1.log"
            log1.write_text(
                """
2023-01-01 10:00:00,000 test.module - DEBUG - Debug message
2023-01-01 10:00:01,000 test.module - INFO - Info message
2023-01-01 10:00:02,000 urllib3.connectionpool - WARNING - Connection warning
2023-01-01 10:00:03,000 test.module - ERROR - Error message
""".strip()
            )

            log2 = log_dir / "test2.log"
            log2.write_text(
                """
2023-01-01 10:00:04,000 another.module - INFO - Another info message
2023-01-01 10:00:05,000 test.module - DEBUG - Another debug message
""".strip()
            )

            yield log_dir

    def test_log_volume_analyzer_initialization(self):
        """Test LogVolumeAnalyzer initialization."""
        analyzer = LogVolumeAnalyzer()

        assert analyzer.settings is None
        assert hasattr(analyzer, "logger")
        assert isinstance(analyzer.analysis_cache, dict)

    def test_analyze_log_files_nonexistent_directory(self):
        """Test analyze_log_files with non-existent directory."""
        analyzer = LogVolumeAnalyzer()

        result = analyzer.analyze_log_files("/nonexistent/path")

        assert "error" in result
        assert "does not exist" in result["error"]

    def test_analyze_log_files_success(self, temp_log_dir):
        """Test analyze_log_files with successful analysis."""
        analyzer = LogVolumeAnalyzer()

        result = analyzer.analyze_log_files(temp_log_dir, hours=24)

        assert "analysis_time" in result
        assert "log_directory" in result
        assert "total_files" in result
        assert "total_lines" in result
        assert "by_level" in result
        assert "by_logger" in result
        assert "frequent_messages" in result
        assert "optimization_opportunities" in result

        assert result["total_files"] == 2
        assert result["total_lines"] > 0
        assert "DEBUG" in result["by_level"]
        assert "INFO" in result["by_level"]
        assert "test.module" in result["by_logger"]

    @patch("calendarbot.optimization.production.LogVolumeAnalyzer._analyze_file")
    def test_analyze_log_files_with_file_error(self, mock_analyze_file, temp_log_dir):
        """Test analyze_log_files when file analysis fails."""
        analyzer = LogVolumeAnalyzer()
        mock_analyze_file.side_effect = Exception("File read error")

        with patch.object(analyzer.logger, "warning") as mock_warning:
            result = analyzer.analyze_log_files(temp_log_dir)

            # Should still return results even with file errors
            assert "analysis_time" in result
            mock_warning.assert_called()

    def test_generate_recommendations_high_volume_logger(self):
        """Test _generate_recommendations with high-volume logger."""
        analyzer = LogVolumeAnalyzer()

        analysis = {
            "total_lines": 1000,
            "by_logger": {"verbose.logger": 500, "normal.logger": 100},  # 50% of logs
            "by_level": {"DEBUG": 200, "INFO": 700, "WARNING": 100},
            "frequent_messages": [],
            "total_size_mb": 50,
        }

        recommendations = analyzer._generate_recommendations(analysis)

        # Should recommend volume reduction for high-volume logger
        volume_recs = [r for r in recommendations if r["type"] == "volume_reduction"]
        assert len(volume_recs) > 0
        assert any("verbose.logger" in r.get("logger", "") for r in volume_recs)

    def test_generate_recommendations_debug_optimization(self):
        """Test _generate_recommendations with high debug volume."""
        analyzer = LogVolumeAnalyzer()

        analysis = {
            "total_lines": 1000,
            "by_logger": {"test.logger": 100},
            "by_level": {"DEBUG": 300, "INFO": 600, "WARNING": 100},  # 30% debug
            "frequent_messages": [],
            "total_size_mb": 50,
        }

        recommendations = analyzer._generate_recommendations(analysis)

        # Should recommend debug level adjustment
        level_recs = [r for r in recommendations if r["type"] == "level_adjustment"]
        assert len(level_recs) > 0

    def test_generate_recommendations_frequent_messages(self):
        """Test _generate_recommendations with frequent messages."""
        analyzer = LogVolumeAnalyzer()

        analysis = {
            "total_lines": 1000,
            "by_logger": {"test.logger": 100},
            "by_level": {"INFO": 1000},
            "frequent_messages": [
                {"pattern": "Frequent message pattern", "count": 150, "estimated_reduction": 120}
            ],
            "total_size_mb": 50,
        }

        recommendations = analyzer._generate_recommendations(analysis)

        # Should recommend frequency limiting
        freq_recs = [r for r in recommendations if r["type"] == "frequency_limiting"]
        assert len(freq_recs) > 0


class TestDebugStatementAnalyzer:
    """Test DebugStatementAnalyzer class."""

    @pytest.fixture
    def temp_code_dir(self):
        """Create temporary directory with test Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_dir = Path(temp_dir)

            # Create test Python file
            test_file = code_dir / "test_module.py"
            test_file.write_text(
                """
import logging

logger = logging.getLogger(__name__)

def test_function():
    print("Debug print statement")
    logger.debug("Debug log message")
    logger.info("Info message")
    # TODO: Fix this function
    # FIXME: This is broken
    return True

def another_function():
    print(f"Another print: {42}")
    logger.debug("Another debug message")
"""
            )

            # Create another test file
            test_file2 = code_dir / "module2.py"
            test_file2.write_text(
                """
def simple_function():
    print("Simple print")
    # XXX: This needs attention
"""
            )

            yield code_dir

    def test_debug_statement_analyzer_initialization(self):
        """Test DebugStatementAnalyzer initialization."""
        analyzer = DebugStatementAnalyzer()

        assert hasattr(analyzer, "logger")

    def test_analyze_codebase_success(self, temp_code_dir):
        """Test analyze_codebase with successful analysis."""
        analyzer = DebugStatementAnalyzer()

        result = analyzer.analyze_codebase(temp_code_dir)

        assert "analysis_time" in result
        assert "root_directory" in result
        assert "total_files" in result
        assert "python_files" in result
        assert "print_statements" in result
        assert "debug_logs" in result
        assert "todo_comments" in result
        assert "optimization_suggestions" in result

        assert result["python_files"] == 2
        assert len(result["print_statements"]) > 0
        assert len(result["debug_logs"]) > 0
        assert len(result["todo_comments"]) > 0

    @patch("calendarbot.optimization.production.DebugStatementAnalyzer._analyze_python_file")
    def test_analyze_codebase_with_file_error(self, mock_analyze_file, temp_code_dir):
        """Test analyze_codebase when file analysis fails."""
        analyzer = DebugStatementAnalyzer()
        mock_analyze_file.side_effect = Exception("File analysis error")

        with patch.object(analyzer.logger, "warning") as mock_warning:
            result = analyzer.analyze_codebase(temp_code_dir)

            # Should still return results even with file errors
            assert "analysis_time" in result
            mock_warning.assert_called()

    def test_generate_code_suggestions_with_prints(self):
        """Test _generate_code_suggestions with print statements."""
        analyzer = DebugStatementAnalyzer()

        analysis = {
            "print_statements": [
                {
                    "file": "/project/test.py",
                    "line": 10,
                    "content": 'print("test")',
                    "context": "print_call",
                },
                {
                    "file": "/project/module.py",
                    "line": 5,
                    "content": 'print("debug")',
                    "context": "print_call",
                },
            ],
            "debug_logs": [],
            "todo_comments": [],
        }

        suggestions = analyzer._generate_code_suggestions(analysis)

        print_suggestions = [s for s in suggestions if s["type"] == "print_removal"]
        assert len(print_suggestions) > 0
        assert print_suggestions[0]["count"] == 2

    def test_generate_code_suggestions_with_debug_logs(self):
        """Test _generate_code_suggestions with debug logs."""
        analyzer = DebugStatementAnalyzer()

        analysis = {
            "print_statements": [],
            "debug_logs": [
                {
                    "file": "/project/test.py",
                    "line": 10,
                    "content": 'logger.debug("test")',
                    "context": "debug_logging",
                }
            ],
            "todo_comments": [],
        }

        suggestions = analyzer._generate_code_suggestions(analysis)

        debug_suggestions = [s for s in suggestions if s["type"] == "debug_review"]
        assert len(debug_suggestions) > 0

    def test_generate_code_suggestions_with_todos(self):
        """Test _generate_code_suggestions with TODO comments."""
        analyzer = DebugStatementAnalyzer()

        analysis = {
            "print_statements": [],
            "debug_logs": [],
            "todo_comments": [
                {
                    "file": "/project/test.py",
                    "line": 10,
                    "type": "TODO",
                    "content": "Fix this",
                    "full_line": "# TODO: Fix this",
                }
            ],
        }

        suggestions = analyzer._generate_code_suggestions(analysis)

        todo_suggestions = [s for s in suggestions if s["type"] == "technical_debt"]
        assert len(todo_suggestions) > 0


class TestPrintStatementFinder:
    """Test PrintStatementFinder AST visitor."""

    def test_print_statement_finder_initialization(self):
        """Test PrintStatementFinder initialization."""
        file_path = Path("/test/file.py")
        finder = PrintStatementFinder(file_path)

        assert finder.file_path == file_path
        assert finder.print_statements == []

    def test_visit_call_print_function(self):
        """Test visit_Call method with print function calls."""
        file_path = Path("/test/file.py")
        finder = PrintStatementFinder(file_path)

        # Create AST node for print() call
        code = "print('hello world')"
        tree = ast.parse(code)

        finder.visit(tree)

        assert len(finder.print_statements) == 1
        assert finder.print_statements[0]["file"] == str(file_path)
        assert finder.print_statements[0]["line"] == 1
        assert "print() call" in finder.print_statements[0]["content"]

    def test_visit_call_non_print_function(self):
        """Test visit_Call method with non-print function calls."""
        file_path = Path("/test/file.py")
        finder = PrintStatementFinder(file_path)

        # Create AST node for non-print call
        code = "len([1, 2, 3])"
        tree = ast.parse(code)

        finder.visit(tree)

        assert len(finder.print_statements) == 0


class TestLoggingOptimizer:
    """Test LoggingOptimizer class."""

    def test_logging_optimizer_initialization(self):
        """Test LoggingOptimizer initialization."""
        optimizer = LoggingOptimizer()

        assert optimizer.settings is None
        assert hasattr(optimizer, "logger")
        assert len(optimizer.rules) > 0  # Should have default rules
        assert hasattr(optimizer, "volume_analyzer")
        assert hasattr(optimizer, "debug_analyzer")

    def test_logging_optimizer_with_settings(self):
        """Test LoggingOptimizer initialization with settings."""
        mock_settings = Mock()
        optimizer = LoggingOptimizer(mock_settings)

        assert optimizer.settings == mock_settings

    def test_add_rule(self):
        """Test add_rule method."""
        optimizer = LoggingOptimizer()
        initial_count = len(optimizer.rules)

        new_rule = OptimizationRule(name="Test Rule", priority=150)

        optimizer.add_rule(new_rule)

        assert len(optimizer.rules) == initial_count + 1
        # Rules should be sorted by priority
        assert optimizer.rules[0].priority >= optimizer.rules[1].priority

    def test_optimize_logging_config_root_level(self):
        """Test optimize_logging_config with root logger level adjustment."""
        optimizer = LoggingOptimizer()

        config = {"root": {"level": "DEBUG"}, "handlers": {}, "loggers": {}}

        optimized = optimizer.optimize_logging_config(config)

        assert optimized["root"]["level"] == "INFO"

    def test_optimize_logging_config_logger_levels(self):
        """Test optimize_logging_config with logger level optimization."""
        optimizer = LoggingOptimizer()

        config = {
            "root": {"level": "INFO"},
            "handlers": {},
            "loggers": {"urllib3.connectionpool": {"level": "DEBUG"}},
        }

        optimized = optimizer.optimize_logging_config(config)

        # Should optimize urllib3 logger level based on default rules
        urllib3_config = optimized["loggers"]["urllib3.connectionpool"]
        assert urllib3_config["level"] != "DEBUG"

    def test_optimize_logging_config_handlers(self):
        """Test optimize_logging_config with handler optimization."""
        optimizer = LoggingOptimizer()

        config = {
            "root": {"level": "INFO"},
            "handlers": {"console": {"class": "logging.StreamHandler"}},
            "loggers": {},
        }

        optimized = optimizer.optimize_logging_config(config)

        # Should add production filter to handlers
        assert "filters" in optimized["handlers"]["console"]
        assert "production_optimizer" in optimized["handlers"]["console"]["filters"]
        assert "filters" in optimized
        assert "production_optimizer" in optimized["filters"]

    @patch("calendarbot.optimization.production.LogVolumeAnalyzer.analyze_log_files")
    @patch("calendarbot.optimization.production.DebugStatementAnalyzer.analyze_codebase")
    def test_analyze_and_optimize(self, mock_code_analysis, mock_log_analysis):
        """Test analyze_and_optimize method."""
        optimizer = LoggingOptimizer()

        # Mock analysis results
        mock_log_analysis.return_value = {
            "optimization_opportunities": [
                {"type": "volume_reduction", "priority": "high", "estimated_reduction": 100}
            ]
        }

        mock_code_analysis.return_value = {
            "optimization_suggestions": [
                {"type": "print_removal", "priority": "medium", "estimated_reduction": 50}
            ]
        }

        result = optimizer.analyze_and_optimize("/log/dir", "/code/dir")

        assert "optimization_time" in result
        assert "log_analysis" in result
        assert "code_analysis" in result
        assert "optimization_summary" in result
        assert "recommendations" in result

        # Should have combined recommendations
        assert len(result["recommendations"]) == 2

        # Summary should have correct stats
        summary = result["optimization_summary"]
        assert summary["total_recommendations"] == 2
        assert summary["high_priority"] == 1
        assert summary["medium_priority"] == 1
        assert summary["estimated_total_reduction"] == 150


class TestModuleFunctions:
    """Test module-level functions."""

    def test_create_production_filter(self):
        """Test create_production_filter function."""
        rule_configs = [
            {
                "name": "Test Rule",
                "optimization_type": "volume_reduction",
                "suppress": True,
                "priority": 100,
                "enabled": True,
            }
        ]

        filter_instance = create_production_filter(rule_configs)

        assert isinstance(filter_instance, ProductionLogFilter)
        assert len(filter_instance.rules) == 1
        assert filter_instance.rules[0].name == "Test Rule"
        assert filter_instance.rules[0].optimization_type == OptimizationType.VOLUME_REDUCTION

    def test_optimize_logging_config_function(self):
        """Test optimize_logging_config convenience function."""
        config = {"root": {"level": "DEBUG"}, "handlers": {}, "loggers": {}}

        optimized = optimize_logging_config(config)

        assert optimized["root"]["level"] == "INFO"

    @patch("calendarbot.optimization.production.LogVolumeAnalyzer")
    def test_analyze_log_volume_function(self, mock_analyzer_class):
        """Test analyze_log_volume convenience function."""
        mock_analyzer = Mock()
        mock_analyzer.analyze_log_files.return_value = {"test": "result"}
        mock_analyzer_class.return_value = mock_analyzer

        result = analyze_log_volume("/log/dir", hours=12)

        assert result == {"test": "result"}
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_log_files.assert_called_once_with("/log/dir", 12)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_production_filter_with_disabled_rules(self):
        """Test ProductionLogFilter with disabled rules."""
        rules = [
            OptimizationRule(name="Enabled Rule", suppress=True, enabled=True),
            OptimizationRule(name="Disabled Rule", suppress=True, enabled=False),
        ]

        filter_instance = ProductionLogFilter(rules)

        record = Mock()
        record.name = "test.module"
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"
        record.getMessage.return_value = "Test message"

        # Only enabled rule should be applied
        result = filter_instance.filter(record)
        assert result == False  # Should be suppressed by enabled rule

    def test_optimization_rule_matches_empty_patterns(self):
        """Test OptimizationRule matches with None/empty patterns."""
        rule = OptimizationRule()  # All patterns are None

        record = Mock()
        record.name = "any.module"
        record.levelno = logging.INFO
        record.getMessage.return_value = "Any message"

        # Should match when no patterns are specified
        assert rule.matches(record) == True

    @patch("builtins.open", side_effect=IOError("File read error"))
    def test_log_volume_analyzer_file_read_error(self, mock_open):
        """Test LogVolumeAnalyzer handling file read errors."""
        analyzer = LogVolumeAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = log_dir / "test.log"
            log_file.touch()  # Create empty file

            # Should handle file read error gracefully
            result = analyzer.analyze_log_files(log_dir)

            # Should still return valid analysis structure
            assert "analysis_time" in result
            assert "total_files" in result

    def test_debug_statement_analyzer_syntax_error_fallback(self):
        """Test DebugStatementAnalyzer fallback for syntax errors."""
        analyzer = DebugStatementAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            code_dir = Path(temp_dir)

            # Create file with syntax error
            bad_file = code_dir / "bad_syntax.py"
            bad_file.write_text("print('unclosed string")

            result = analyzer.analyze_codebase(code_dir)

            # Should still complete analysis
            assert "analysis_time" in result
            assert "python_files" in result
