"""Production logging optimization and intelligent volume reduction system."""

import ast
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from ..utils.logging import get_logger


class OptimizationType(Enum):
    """Types of logging optimizations."""

    VOLUME_REDUCTION = "volume_reduction"
    LEVEL_ADJUSTMENT = "level_adjustment"
    DEBUG_REMOVAL = "debug_removal"
    FREQUENCY_LIMITING = "frequency_limiting"
    CONDITIONAL_LOGGING = "conditional_logging"
    PERFORMANCE_FILTERING = "performance_filtering"
    CONTENT_OPTIMIZATION = "content_optimization"
    HANDLER_OPTIMIZATION = "handler_optimization"


@dataclass
class OptimizationRule:
    """Defines a logging optimization rule."""

    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    optimization_type: OptimizationType = OptimizationType.VOLUME_REDUCTION
    description: str = ""

    # Rule criteria
    logger_pattern: Optional[str] = None
    level_threshold: Optional[int] = None
    message_pattern: Optional[str] = None
    frequency_limit: Optional[int] = None

    # Rule actions
    target_level: Optional[int] = None
    suppress: bool = False
    rate_limit: Optional[int] = None
    condition: Optional[str] = None

    # Rule metadata
    priority: int = 0
    enabled: bool = True
    production_only: bool = True
    estimated_reduction: float = 0.0

    def matches(self, record: logging.LogRecord) -> bool:
        """Check if this rule matches a log record."""
        # Check logger pattern
        if self.logger_pattern and not re.search(self.logger_pattern, record.name):
            return False

        # Check level threshold
        if self.level_threshold and record.levelno < self.level_threshold:
            return False

        # Check message pattern
        return not (
            self.message_pattern and not re.search(self.message_pattern, record.getMessage())
        )


class ProductionLogFilter(logging.Filter):
    """Advanced filter for production log optimization."""

    def __init__(self, rules: list[OptimizationRule], settings: Optional[Any] = None):
        super().__init__()
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.settings = settings
        self.message_counts: dict[str, int] = defaultdict(int)
        self.last_reset = datetime.now(timezone.utc)
        self.reset_interval = timedelta(minutes=5)

        # Performance optimization tracking
        self.filtered_count = 0
        self.total_count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on optimization rules."""
        self.total_count += 1

        # Reset counters periodically
        now = datetime.now(timezone.utc)
        if now - self.last_reset > self.reset_interval:
            self.message_counts.clear()
            self.last_reset = now

        # Apply optimization rules
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Skip production-only rules when not in production mode
            if (
                rule.production_only
                and self.settings
                and hasattr(self.settings, "logging")
                and not self.settings.logging.production_mode
            ):
                continue

            if rule.matches(record):
                # Apply suppression rule
                if rule.suppress:
                    self.filtered_count += 1
                    return False

                # Apply rate limiting
                if rule.rate_limit:
                    key = f"{record.name}:{record.levelname}:{hash(record.getMessage())}"
                    self.message_counts[key] += 1

                    if self.message_counts[key] > rule.rate_limit:
                        self.filtered_count += 1
                        return False

                # Apply level adjustment
                if rule.target_level:
                    record.levelno = rule.target_level
                    record.levelname = logging.getLevelName(rule.target_level)

        return True

    def get_filter_stats(self) -> dict[str, Any]:
        """Get filtering statistics."""
        return {
            "total_processed": self.total_count,
            "filtered_count": self.filtered_count,
            "filter_rate": self.filtered_count / max(self.total_count, 1),
            "active_rules": len([r for r in self.rules if r.enabled]),
            "message_counts": dict(self.message_counts),
        }


class LogVolumeAnalyzer:
    """Analyzes log volume patterns and suggests optimizations."""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        self.logger = get_logger("log_volume_analyzer")
        self.analysis_cache: dict[str, Any] = {}

    def analyze_log_files(self, log_dir: Union[str, Path], hours: int = 24) -> dict[str, Any]:
        """
        Analyze log files for volume patterns and optimization opportunities.

        Args:
            log_dir: Directory containing log files
            hours: Number of hours to analyze

        Returns:
            Analysis results with optimization recommendations
        """
        log_dir = Path(log_dir)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        if not log_dir.exists():
            return {"error": f"Log directory {log_dir} does not exist"}

        analysis: dict[str, Any] = {
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "log_directory": str(log_dir),
            "time_range_hours": hours,
            "total_files": 0,
            "total_lines": 0,
            "total_size_mb": 0,
            "by_level": defaultdict(int),
            "by_logger": defaultdict(int),
            "frequent_messages": [],
            "optimization_opportunities": [],
            "volume_trends": {},
        }

        # Analyze log files
        log_files = list(log_dir.glob("*.log"))
        analysis["total_files"] = len(log_files)

        # Collect errors to handle after processing
        failed_files = []

        for log_file in log_files:
            file_stats = self._analyze_file(log_file, cutoff_time)
            if file_stats is None:
                failed_files.append(log_file)
                continue

            analysis["total_lines"] += file_stats["lines"]
            analysis["total_size_mb"] += file_stats["size_mb"]

            # Aggregate by level and logger
            by_level_stats: defaultdict[str, int] = file_stats["by_level"]
            by_logger_stats: defaultdict[str, int] = file_stats["by_logger"]
            analysis_by_level: defaultdict[str, int] = analysis["by_level"]
            analysis_by_logger: defaultdict[str, int] = analysis["by_logger"]

            for level, count in by_level_stats.items():
                analysis_by_level[level] += count

            for logger, count in by_logger_stats.items():
                analysis_by_logger[logger] += count

        # Log failed files after processing
        for failed_file in failed_files:
            self.logger.warning(f"Failed to analyze {failed_file}")

        # Find frequent messages for rate limiting opportunities
        analysis["frequent_messages"] = self._find_frequent_messages(log_files, cutoff_time)

        # Generate optimization recommendations
        analysis["optimization_opportunities"] = self._generate_recommendations(analysis)

        return analysis

    def _analyze_file(self, log_file: Path, cutoff_time: datetime) -> Optional[dict[str, Any]]:
        """Analyze a single log file."""
        try:
            stats: dict[str, Any] = {
                "lines": 0,
                "size_mb": log_file.stat().st_size / 1024 / 1024,
                "by_level": defaultdict(int),
                "by_logger": defaultdict(int),
            }

            with log_file.open(encoding="utf-8", errors="ignore") as f:
                for line in f:
                    lines_count: int = stats["lines"]
                    stats["lines"] = lines_count + 1

                    # Parse log line for level and logger
                    level_match = re.search(r" - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ", line)
                    if level_match:
                        by_level_dict: defaultdict[str, int] = stats["by_level"]
                        by_level_dict[level_match.group(1)] += 1

                    # Extract logger name
                    logger_match = re.search(
                        r"(\w+(?:\.\w+)*) - (DEBUG|INFO|WARNING|ERROR|CRITICAL)", line
                    )
                    if logger_match:
                        by_logger_dict: defaultdict[str, int] = stats["by_logger"]
                        by_logger_dict[logger_match.group(1)] += 1

            return stats
        except Exception as e:
            self.logger.warning(f"Error reading {log_file}: {e}")
            return None

    def _find_frequent_messages(
        self, log_files: list[Path], cutoff_time: datetime, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Find frequently occurring log messages."""
        message_patterns: dict[str, int] = defaultdict(int)

        # Collect errors for batch logging
        failed_files = []

        for log_file in log_files:
            file_patterns = self._extract_message_patterns(log_file)
            if file_patterns is None:
                failed_files.append(log_file)
                continue

            # Merge patterns from this file
            for pattern, count in file_patterns.items():
                message_patterns[pattern] += count

        # Log all failures after processing
        for failed_file in failed_files:
            self.logger.warning(f"Error analyzing messages in {failed_file}")

        # Return top frequent messages
        frequent = sorted(message_patterns.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            {
                "pattern": pattern,
                "count": count,
                "estimated_reduction": min(count * 0.8, count - 10) if count > 10 else 0,
            }
            for pattern, count in frequent
        ]

    def _extract_message_patterns(self, log_file: Path) -> Optional[dict[str, int]]:
        """Extract message patterns from a single log file."""
        try:
            patterns: dict[str, int] = defaultdict(int)
            with log_file.open(encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Extract message content
                    message_match = re.search(
                        r" - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.+)$", line
                    )
                    if message_match:
                        message = message_match.group(2).strip()

                        # Normalize message (replace numbers/IDs with placeholders)
                        normalized = re.sub(r"\b\d+\b", "<NUM>", message)
                        normalized = re.sub(
                            r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
                            "<UUID>",
                            normalized,
                        )
                        patterns[normalized] += 1
            return dict(patterns)
        except Exception as e:
            self.logger.warning(f"Error extracting patterns from {log_file}: {e}")
            return None

    def _generate_recommendations(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []

        # High-volume logger optimization
        total_lines = analysis["total_lines"]
        by_logger: defaultdict[str, int] = analysis["by_logger"]
        for logger, count in by_logger.items():
            if count > total_lines * 0.1:  # Logger produces >10% of logs
                recommendations.append(
                    {
                        "type": "volume_reduction",
                        "priority": "high",
                        "logger": logger,
                        "current_volume": count,
                        "percentage": (count / total_lines) * 100,
                        "suggestion": f"Consider increasing log level threshold for {logger}",
                        "estimated_reduction": count * 0.3,
                    }
                )

        # Debug level optimization
        by_level: defaultdict[str, int] = analysis["by_level"]
        debug_count = by_level.get("DEBUG", 0)
        if debug_count > total_lines * 0.2:  # >20% debug logs
            recommendations.append(
                {
                    "type": "level_adjustment",
                    "priority": "medium",
                    "current_debug_logs": debug_count,
                    "percentage": (debug_count / total_lines) * 100,
                    "suggestion": "Consider disabling DEBUG level in production",
                    "estimated_reduction": debug_count,
                }
            )

        # Frequent message rate limiting
        frequent_messages: list[dict[str, Any]] = analysis["frequent_messages"]
        high_volume_messages = [
            {
                "type": "frequency_limiting",
                "priority": "medium",
                "message_pattern": msg_info["pattern"],
                "current_count": msg_info["count"],
                "suggestion": f"Rate limit message: {msg_info['pattern'][:100]}...",
                "estimated_reduction": msg_info["estimated_reduction"],
            }
            for msg_info in frequent_messages[:3]  # Top 3 frequent messages
            if msg_info["count"] > 100
        ]
        recommendations.extend(high_volume_messages)

        # Overall volume warning
        if analysis["total_size_mb"] > 1000:  # >1GB logs
            recommendations.append(
                {
                    "type": "volume_reduction",
                    "priority": "high",
                    "current_size_mb": analysis["total_size_mb"],
                    "suggestion": "Log volume is very high, consider comprehensive optimization",
                    "estimated_reduction": analysis["total_size_mb"] * 0.4,
                }
            )

        return recommendations


class DebugStatementAnalyzer:
    """Analyzes source code for debug statements and print() calls."""

    def __init__(self) -> None:
        self.logger = get_logger("debug_analyzer")

    def analyze_codebase(self, root_dir: Union[str, Path]) -> dict[str, Any]:
        """
        Analyze codebase for debug statements and optimization opportunities.

        Args:
            root_dir: Root directory of the codebase

        Returns:
            Analysis results with recommendations
        """
        root_dir = Path(root_dir)

        analysis: dict[str, Any] = {
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "root_directory": str(root_dir),
            "total_files": 0,
            "python_files": 0,
            "print_statements": [],
            "debug_logs": [],
            "todo_comments": [],
            "optimization_suggestions": [],
        }

        # Find all Python files
        python_files = list(root_dir.rglob("*.py"))
        analysis["python_files"] = len(python_files)
        analysis["total_files"] = len(list(root_dir.rglob("*")))

        # Collect errors for batch processing
        failed_files = []

        for py_file in python_files:
            file_analysis = self._analyze_python_file(py_file)
            if file_analysis is None:
                failed_files.append(py_file)
                continue

            # Extend analysis lists with file results
            print_statements: list[dict[str, Any]] = analysis["print_statements"]
            debug_logs: list[dict[str, Any]] = analysis["debug_logs"]
            todo_comments: list[dict[str, Any]] = analysis["todo_comments"]

            print_statements.extend(file_analysis["print_statements"])
            debug_logs.extend(file_analysis["debug_logs"])
            todo_comments.extend(file_analysis["todo_comments"])

        # Log all failures after processing
        for failed_file in failed_files:
            self.logger.warning(f"Failed to analyze {failed_file}")

        # Generate optimization suggestions
        analysis["optimization_suggestions"] = self._generate_code_suggestions(analysis)

        return analysis

    def _analyze_python_file(self, file_path: Path) -> Optional[dict[str, Any]]:
        """Analyze a single Python file for debug statements."""
        try:
            file_analysis: dict[str, Any] = {
                "file": str(file_path),
                "print_statements": [],
                "debug_logs": [],
                "todo_comments": [],
            }

            with file_path.open(encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()

            # Parse AST for print statements
            try:
                tree = ast.parse(content)
                print_finder = PrintStatementFinder(file_path)
                print_finder.visit(tree)
                print_statements_list: list[dict[str, Any]] = file_analysis["print_statements"]
                print_statements_list.clear()
                print_statements_list.extend(print_finder.print_statements)
            except SyntaxError:
                # Fallback to regex for syntax errors
                self._find_prints_regex(lines, file_path, file_analysis)

            # Find debug log statements and TODO comments
            for line_num, line in enumerate(lines, 1):
                # Debug log statements
                if re.search(r"\.debug\s*\(|logging\.debug\s*\(|logger\.debug\s*\(", line):
                    debug_logs_list: list[dict[str, Any]] = file_analysis["debug_logs"]
                    debug_logs_list.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip(),
                            "context": "debug_logging",
                        }
                    )

                # TODO/FIXME comments
                todo_match = re.search(r"#\s*(TODO|FIXME|HACK|XXX)(.*)$", line, re.IGNORECASE)
                if todo_match:
                    todo_comments_list: list[dict[str, Any]] = file_analysis["todo_comments"]
                    todo_comments_list.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "type": todo_match.group(1).upper(),
                            "content": todo_match.group(2).strip(),
                            "full_line": line.strip(),
                        }
                    )

            return file_analysis
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")
            return None

    def _find_prints_regex(
        self, lines: list[str], file_path: Path, file_analysis: dict[str, Any]
    ) -> None:
        """Fallback regex-based print statement detection."""
        for line_num, line in enumerate(lines, 1):
            if re.search(r"\bprint\s*\(", line):
                print_statements_list: list[dict[str, Any]] = file_analysis["print_statements"]
                print_statements_list.append(
                    {
                        "file": str(file_path),
                        "line": line_num,
                        "content": line.strip(),
                        "context": "print_call",
                    }
                )

    def _generate_code_suggestions(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate code optimization suggestions."""
        suggestions = []

        # Print statement suggestions
        print_statements: list[dict[str, Any]] = analysis["print_statements"]
        core_prints = [
            p
            for p in print_statements
            if not any(lib in p["file"] for lib in ["/site-packages/", "/venv/", "/env/"])
        ]

        if core_prints:
            suggestions.append(
                {
                    "type": "print_removal",
                    "priority": "medium",
                    "count": len(core_prints),
                    "suggestion": f"Replace {len(core_prints)} print() statements with proper logging",
                    "files_affected": len({p["file"] for p in core_prints}),
                }
            )

        # Debug log suggestions
        debug_logs: list[dict[str, Any]] = analysis["debug_logs"]
        if debug_logs:
            suggestions.append(
                {
                    "type": "debug_review",
                    "priority": "low",
                    "count": len(debug_logs),
                    "suggestion": f"Review {len(debug_logs)} debug log statements for production relevance",
                    "files_affected": len({d["file"] for d in debug_logs}),
                }
            )

        # TODO comment suggestions
        todo_comments: list[dict[str, Any]] = analysis["todo_comments"]
        if todo_comments:
            suggestions.append(
                {
                    "type": "technical_debt",
                    "priority": "low",
                    "count": len(todo_comments),
                    "suggestion": f"Address {len(todo_comments)} TODO/FIXME comments",
                    "files_affected": len({t["file"] for t in todo_comments}),
                }
            )

        return suggestions


class PrintStatementFinder(ast.NodeVisitor):
    """AST visitor to find print statements."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.print_statements: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to find print statements."""
        if (isinstance(node.func, ast.Name) and node.func.id == "print") or (
            isinstance(node.func, ast.Attribute) and node.func.attr == "print"
        ):
            self.print_statements.append(
                {
                    "file": str(self.file_path),
                    "line": node.lineno,
                    "content": f"print() call at line {node.lineno}",
                    "context": "ast_analysis",
                }
            )

        self.generic_visit(node)


class LoggingOptimizer:
    """Main class for production logging optimization."""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        self.logger = get_logger("logging_optimizer")
        self.rules: list[OptimizationRule] = []
        self.volume_analyzer = LogVolumeAnalyzer(settings)
        self.debug_analyzer = DebugStatementAnalyzer()

        # Load default optimization rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default optimization rules."""
        default_rules = [
            # Volume reduction rules
            OptimizationRule(
                name="Suppress excessive debug logs",
                optimization_type=OptimizationType.DEBUG_REMOVAL,
                description="Suppress DEBUG level logs in production",
                level_threshold=logging.DEBUG,
                suppress=True,
                priority=100,
                estimated_reduction=0.3,
            ),
            # Rate limiting rules
            OptimizationRule(
                name="Rate limit frequent messages",
                optimization_type=OptimizationType.FREQUENCY_LIMITING,
                description="Rate limit messages that repeat frequently",
                rate_limit=10,
                priority=80,
                estimated_reduction=0.2,
            ),
            # Performance filtering
            OptimizationRule(
                name="Filter verbose library logs",
                optimization_type=OptimizationType.PERFORMANCE_FILTERING,
                description="Reduce verbosity of third-party library logs",
                logger_pattern=r"(urllib3|requests|asyncio|aiohttp)",
                target_level=logging.WARNING,
                priority=60,
                estimated_reduction=0.15,
            ),
            # Content optimization
            OptimizationRule(
                name="Optimize repetitive messages",
                optimization_type=OptimizationType.CONTENT_OPTIMIZATION,
                description="Reduce repetitive log message content",
                message_pattern=r"(Starting|Finished|Processing)",
                rate_limit=5,
                priority=40,
                estimated_reduction=0.1,
            ),
        ]

        self.rules.extend(default_rules)

    def add_rule(self, rule: OptimizationRule) -> None:
        """Add a custom optimization rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def optimize_logging_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize logging configuration for production use.

        Args:
            config: Current logging configuration

        Returns:
            Optimized logging configuration
        """
        optimized_config = config.copy()

        # Adjust root logger level for production
        if "root" in optimized_config and "level" in optimized_config["root"]:
            current_level = optimized_config["root"]["level"]
            if isinstance(current_level, str) and current_level == "DEBUG":
                optimized_config["root"]["level"] = "INFO"
                self.logger.info("Adjusted root logger level from DEBUG to INFO for production")

        # Optimize logger levels
        if "loggers" in optimized_config:
            for logger_name, logger_config in optimized_config["loggers"].items():
                if "level" in logger_config:
                    current_level = logger_config["level"]

                    # Apply optimization rules
                    for rule in self.rules:
                        if (
                            rule.logger_pattern
                            and re.search(rule.logger_pattern, logger_name)
                            and rule.target_level
                            and current_level == "DEBUG"
                        ):
                            logger_config["level"] = logging.getLevelName(rule.target_level)
                            self.logger.info(
                                f"Optimized {logger_name} level: {current_level} -> {logger_config['level']}"
                            )

        # Add production filter to handlers
        if "handlers" in optimized_config:
            for handler_config in optimized_config["handlers"].values():
                if "filters" not in handler_config:
                    handler_config["filters"] = []

                # Add production optimization filter
                if "production_optimizer" not in handler_config["filters"]:
                    handler_config["filters"].append("production_optimizer")

        # Add production filter configuration
        if "filters" not in optimized_config:
            optimized_config["filters"] = {}

        optimized_config["filters"]["production_optimizer"] = {
            "()": "calendarbot.optimization.production.create_production_filter",
            "rules": [rule.__dict__ for rule in self.rules if rule.enabled],
        }

        return optimized_config

    def analyze_and_optimize(
        self, log_dir: Union[str, Path], code_dir: Union[str, Path]
    ) -> dict[str, Any]:
        """
        Perform comprehensive analysis and optimization.

        Args:
            log_dir: Directory containing log files
            code_dir: Directory containing source code

        Returns:
            Comprehensive analysis and optimization results
        """
        results: dict[str, Any] = {
            "optimization_time": datetime.now(timezone.utc).isoformat(),
            "log_analysis": {},
            "code_analysis": {},
            "optimization_summary": {},
            "recommendations": [],
        }

        # Analyze log volume
        self.logger.info("Analyzing log volume patterns...")
        results["log_analysis"] = self.volume_analyzer.analyze_log_files(log_dir)

        # Analyze source code
        self.logger.info("Analyzing source code for debug statements...")
        results["code_analysis"] = self.debug_analyzer.analyze_codebase(code_dir)

        # Generate comprehensive recommendations
        all_recommendations: list[dict[str, Any]] = []
        log_analysis: dict[str, Any] = results["log_analysis"]
        code_analysis: dict[str, Any] = results["code_analysis"]

        log_opportunities = log_analysis.get("optimization_opportunities", [])
        code_suggestions = code_analysis.get("optimization_suggestions", [])

        all_recommendations.extend(log_opportunities)
        all_recommendations.extend(code_suggestions)

        # Prioritize recommendations
        priority_order = {"high": 3, "medium": 2, "low": 1}
        all_recommendations.sort(
            key=lambda x: priority_order.get(x.get("priority", "low"), 1), reverse=True
        )

        results["recommendations"] = all_recommendations

        # Calculate optimization summary
        total_estimated_reduction = sum(
            r.get("estimated_reduction", 0)
            for r in all_recommendations
            if isinstance(r.get("estimated_reduction"), (int, float))
        )

        results["optimization_summary"] = {
            "total_recommendations": len(all_recommendations),
            "high_priority": len([r for r in all_recommendations if r.get("priority") == "high"]),
            "medium_priority": len(
                [r for r in all_recommendations if r.get("priority") == "medium"]
            ),
            "low_priority": len([r for r in all_recommendations if r.get("priority") == "low"]),
            "estimated_total_reduction": total_estimated_reduction,
            "current_log_volume_mb": log_analysis.get("total_size_mb", 0),
        }

        return results


def create_production_filter(rules: list[dict[str, Any]]) -> ProductionLogFilter:
    """Create a production log filter from rule configurations."""
    optimization_rules = []

    for rule_config in rules:
        rule = OptimizationRule()
        for key, value in rule_config.items():
            if hasattr(rule, key):
                if key == "optimization_type":
                    setattr(rule, key, OptimizationType(value))
                else:
                    setattr(rule, key, value)
        optimization_rules.append(rule)

    return ProductionLogFilter(optimization_rules)


def optimize_logging_config(
    config: dict[str, Any], settings: Optional[Any] = None
) -> dict[str, Any]:
    """Convenience function to optimize logging configuration."""
    optimizer = LoggingOptimizer(settings)
    return optimizer.optimize_logging_config(config)


def analyze_log_volume(
    log_dir: Union[str, Path], hours: int = 24, settings: Optional[Any] = None
) -> dict[str, Any]:
    """Convenience function to analyze log volume."""
    analyzer = LogVolumeAnalyzer(settings)
    return analyzer.analyze_log_files(log_dir, hours)
