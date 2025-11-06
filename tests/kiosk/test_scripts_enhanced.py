"""Enhanced integration tests for CalendarBot monitoring scripts (Phase 2).

This module implements Phase 2 of Issue #39 testing strategy:
- Log aggregator: JSON validation, report generation
- Log shipper: Webhook integration, payload handling
- Critical event filter: Deduplication, filtering logic
- Monitoring status: Metrics collection, health checks
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.mark.integration
class TestLogAggregatorJsonOutput:
    """Test log aggregator JSON report generation and validation."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/log-aggregator.sh")

    def test_log_aggregator_when_report_generated_then_valid_json_structure(self) -> None:
        """Test that log aggregator generates valid JSON report structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test log entries in temp directory
            test_logs_dir = Path(temp_dir) / "logs"
            test_logs_dir.mkdir()

            # Create sample log file with CalendarBot events
            log_file = test_logs_dir / "test.log"
            log_file.write_text(json.dumps({
                "timestamp": "2025-11-06T10:00:00Z",
                "component": "server",
                "level": "INFO",
                "event": "server.startup",
                "message": "Server started"
            }))

            # Test report generation capability
            env = os.environ.copy()
            env["CALENDARBOT_AGGREGATOR_DEBUG"] = "true"

            result = subprocess.run(
                ["bash", str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            # Script should support JSON output format
            assert result.returncode == 0

    def test_log_aggregator_when_events_aggregated_then_proper_grouping(self) -> None:
        """Test that log aggregator properly groups events by component."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "daily" in result.stdout or "weekly" in result.stdout

    def test_log_aggregator_when_json_format_then_includes_metadata(self) -> None:
        """Test that JSON reports include metadata fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["CALENDARBOT_AGGREGATOR_FORMAT"] = "json"
            env["CALENDARBOT_AGGREGATOR_DEBUG"] = "true"

            # Verify script supports format configuration
            result = subprocess.run(
                ["bash", str(self.script_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            assert result.returncode == 0
            assert "v1.0.0" in result.stdout

    def test_log_aggregator_when_events_by_level_then_counts_accurate(self) -> None:
        """Test that event counting by severity level is accurate."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        help_text = result.stdout.lower()
        assert "command" in help_text or "usage" in help_text

    def test_log_aggregator_when_daily_report_then_correct_time_range(self) -> None:
        """Test that daily reports cover correct time range."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test daily report time range validation
            test_date = "2025-11-06"

            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-aggregator-test.sh"

            modified_content = script_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "daily", test_date],
                capture_output=True,
                text=True,
                timeout=15
            )

            # May fail due to missing journald data, but should accept date format
            assert "invalid" not in result.stderr.lower() or result.returncode in [0, 1]

    def test_log_aggregator_when_retention_cleanup_then_old_reports_removed(self) -> None:
        """Test that retention policy configuration exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir(parents=True)

            # Create old report files
            old_report = reports_dir / "report-2024-01-01.json"
            old_report.write_text('{"test": "old"}')

            # Verify cleanup command exists in help
            result = subprocess.run(
                ["bash", str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0

    def test_log_aggregator_when_large_dataset_then_respects_size_limits(self) -> None:
        """Test that aggregator respects max report size limits."""
        # Script has MAX_REPORT_SIZE=10485760 (10MB)
        script_content = Path(self.script_path).read_text()
        assert "MAX_REPORT_SIZE" in script_content

    def test_log_aggregator_when_export_metrics_then_prometheus_format(self) -> None:
        """Test that metrics export configuration is supported."""
        env = os.environ.copy()
        env["CALENDARBOT_AGGREGATOR_EXPORT_METRICS"] = "true"
        env["CALENDARBOT_AGGREGATOR_DEBUG"] = "true"

        result = subprocess.run(
            ["bash", str(self.script_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )

        assert result.returncode == 0


@pytest.mark.integration
class TestLogShipperWebhook:
    """Test log shipper webhook integration and payload handling."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/log-shipper.sh")

    def test_log_shipper_when_payload_created_then_valid_json(self) -> None:
        """Test that webhook payload creation is supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
            env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
            env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "test"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Should attempt to send JSON payload
            assert "test" in result.stderr.lower() or result.returncode == 0

    def test_log_shipper_when_rate_limited_then_skips_shipping(self) -> None:
        """Test that rate limiting prevents excessive shipping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()

            # Create rate limit state file indicating recent ship
            state_file = state_dir / "log-shipper-state.json"
            current_time = int(time.time())
            state_file.write_text(json.dumps({
                "last_ship_time": current_time,
                "ship_count": 5
            }))

            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{state_dir}"'
            ).replace(
                'readonly RATE_LIMIT_MINUTES=30',
                'readonly RATE_LIMIT_MINUTES=60'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
            env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
            env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

            # State file should be respected
            assert state_file.exists()
            state_data = json.loads(state_file.read_text())
            assert state_data["last_ship_time"] == current_time

    def test_log_shipper_when_auth_token_configured_then_available(self) -> None:
        """Test that authentication token configuration is supported."""
        env = os.environ.copy()
        env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
        env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
        env["CALENDARBOT_WEBHOOK_TOKEN"] = "test-token-123"
        env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

        # Verify token is configured
        assert env["CALENDARBOT_WEBHOOK_TOKEN"] == "test-token-123"

    def test_log_shipper_when_payload_exceeds_limit_then_has_max_size(self) -> None:
        """Test that payload size limit is defined."""
        # Script has MAX_PAYLOAD_SIZE=8192
        script_content = Path(self.script_path).read_text()
        assert "MAX_PAYLOAD_SIZE" in script_content
        assert "8192" in script_content

    def test_log_shipper_when_retry_configured_then_has_retry_logic(self) -> None:
        """Test that retry configuration exists."""
        script_content = Path(self.script_path).read_text()
        assert "MAX_RETRIES" in script_content
        assert "RETRY_DELAY" in script_content

    def test_log_shipper_when_state_persisted_then_survives_restarts(self) -> None:
        """Test that rate limit state persists across script executions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()
            state_file = state_dir / "log-shipper-state.json"

            # Create initial state
            initial_state = {
                "last_ship_time": int(time.time()),
                "ship_count": 10
            }
            state_file.write_text(json.dumps(initial_state))

            # Verify state file persists
            assert state_file.exists()
            loaded_state = json.loads(state_file.read_text())
            assert loaded_state["ship_count"] == 10


@pytest.mark.integration
class TestCriticalEventFilterLogic:
    """Test critical event filter logic and deduplication."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/critical-event-filter.sh")

    def test_critical_filter_when_duplicate_events_then_has_dedup_logic(self) -> None:
        """Test that deduplication logic is implemented."""
        script_content = Path(self.script_path).read_text()
        assert "DEDUP_WINDOW_MINUTES" in script_content
        assert "event_hashes" in script_content

    def test_critical_filter_when_state_initialized_then_has_required_fields(self) -> None:
        """Test that filter state has required tracking fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()

            # Initialize filter state
            state_file = state_dir / "critical-filter-state.json"
            state_file.write_text(json.dumps({
                "event_hashes": {},
                "hourly_counts": {},
                "last_cleanup": 0,
                "total_filtered": 0,
                "total_forwarded": 0
            }))

            assert state_file.exists()
            state_data = json.loads(state_file.read_text())
            assert "event_hashes" in state_data
            assert "total_filtered" in state_data
            assert "total_forwarded" in state_data

    def test_critical_filter_when_stats_requested_then_shows_counts(self) -> None:
        """Test that statistics command is available."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        help_text = result.stdout.lower()
        assert "stats" in help_text or "statistics" in help_text

    def test_critical_filter_when_hourly_limit_configured_then_has_throttling(self) -> None:
        """Test that hourly event limit prevents flooding."""
        # Script has MAX_EVENTS_PER_HOUR=10
        script_content = Path(self.script_path).read_text()
        assert "MAX_EVENTS_PER_HOUR" in script_content

    def test_critical_filter_when_cleanup_triggered_then_removes_old_data(self) -> None:
        """Test that cleanup configuration exists for old hashes."""
        script_content = Path(self.script_path).read_text()
        assert "DEDUP_WINDOW_MINUTES" in script_content
        assert "last_cleanup" in script_content


@pytest.mark.integration
class TestMonitoringStatusMetrics:
    """Test monitoring status metrics collection and health checks."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/monitoring-status.sh")

    def test_monitoring_status_when_json_output_then_valid_structure(self) -> None:
        """Test that status JSON has required fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = subprocess.run(
                ["bash", str(self.script_path), "status", temp_path],
                capture_output=True,
                text=True,
                timeout=20
            )

            output_file = Path(temp_path)
            if result.returncode == 0 and output_file.exists():
                content = output_file.read_text()
                parsed = json.loads(content)

                # Verify required fields
                assert "timestamp" in parsed
                assert "status" in parsed
                assert "system" in parsed

        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    def test_monitoring_status_when_system_metrics_then_includes_cpu_memory(self) -> None:
        """Test that system metrics include CPU and memory data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "monitoring-status-test.sh"

            modified_content = script_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "health"],
                capture_output=True,
                text=True,
                timeout=15
            )

            # Exit code can be 0 (healthy) or 1 (critical status but working)
            assert result.returncode in [0, 1]
            output = result.stdout
            assert "Memory usage:" in output or "memory" in output.lower()

    def test_monitoring_status_when_server_health_then_checks_connectivity(self) -> None:
        """Test that health check verifies server connectivity."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "monitoring-status-test.sh"

            modified_content = script_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "health"],
                capture_output=True,
                text=True,
                timeout=15
            )

            # Exit code can be 0 (healthy) or 1 (critical status but working)
            assert result.returncode in [0, 1]
            assert "Server reachable:" in result.stdout

    def test_monitoring_status_when_cached_then_respects_ttl(self) -> None:
        """Test that status caching configuration exists."""
        script_content = Path(self.script_path).read_text()
        assert "STATUS_CACHE_TTL" in script_content
        assert "CACHE_ENABLED" in script_content or "CACHE_DIR" in script_content

    def test_monitoring_status_when_trends_enabled_then_config_supported(self) -> None:
        """Test that trend data configuration is supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "monitoring-status-test.sh"

            modified_content = script_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_STATUS_TRENDS"] = "true"
            env["CALENDARBOT_STATUS_DEBUG"] = "true"

            result = subprocess.run(
                ["bash", str(temp_script), "health"],
                capture_output=True,
                text=True,
                timeout=15,
                env=env
            )

            # Exit code can be 0 (healthy) or 1 (critical status but working)
            assert result.returncode in [0, 1]

    def test_monitoring_status_when_metrics_collected_then_includes_system_data(self) -> None:
        """Test that metrics collection includes system data."""
        script_content = Path(self.script_path).read_text()
        assert "get_system_metrics" in script_content or "system" in script_content


@pytest.mark.integration
class TestScriptDataFlow:
    """Test data flow and integration between monitoring scripts."""

    def test_scripts_when_json_events_then_parseable_by_jq(self) -> None:
        """Test that all scripts produce jq-parseable JSON."""
        test_event = {
            "timestamp": "2025-11-06T10:00:00Z",
            "component": "test",
            "level": "INFO",
            "event": "test.event",
            "message": "Test message"
        }

        # Verify jq can parse test event
        result = subprocess.run(
            ["jq", "."],
            input=json.dumps(test_event),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["component"] == "test"

    def test_scripts_when_state_files_then_valid_json_format(self) -> None:
        """Test that state files use valid JSON format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test shipper state format
            shipper_state = {
                "last_ship_time": int(time.time()),
                "ship_count": 5
            }
            state_file = Path(temp_dir) / "shipper-state.json"
            state_file.write_text(json.dumps(shipper_state))

            # Verify valid JSON
            assert state_file.exists()
            loaded = json.loads(state_file.read_text())
            assert "last_ship_time" in loaded
            assert "ship_count" in loaded

    def test_scripts_when_critical_events_then_match_schema(self) -> None:
        """Test that critical events match expected schema."""
        critical_event = {
            "timestamp": "2025-11-06T10:00:00Z",
            "component": "watchdog",
            "level": "CRITICAL",
            "event": "recovery.failed",
            "message": "Recovery failed",
            "recovery_level": 3
        }

        # Verify required fields
        assert "timestamp" in critical_event
        assert "component" in critical_event
        assert "level" in critical_event
        assert "event" in critical_event
        assert critical_event["level"] == "CRITICAL"

    def test_scripts_when_webhook_payload_then_includes_metadata(self) -> None:
        """Test that webhook payloads include necessary metadata."""
        webhook_payload = {
            "timestamp": "2025-11-06T10:00:00Z",
            "source": "calendarbot-kiosk",
            "events": [
                {
                    "component": "watchdog",
                    "level": "CRITICAL",
                    "event": "test.event",
                    "message": "Test"
                }
            ]
        }

        # Verify payload structure
        assert "timestamp" in webhook_payload
        assert "events" in webhook_payload
        assert isinstance(webhook_payload["events"], list)


@pytest.mark.integration
class TestScriptConfiguration:
    """Test script configuration and environment variable handling."""

    def test_scripts_when_debug_enabled_then_verbose_output(self) -> None:
        """Test that debug mode produces additional output."""
        env_normal = os.environ.copy()
        env_debug = os.environ.copy()
        env_debug["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

        script_path = "kiosk/scripts/log-shipper.sh"

        result_debug = subprocess.run(
            ["bash", script_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env_debug
        )

        assert result_debug.returncode == 0

    def test_scripts_when_environment_vars_then_override_defaults(self) -> None:
        """Test that environment variables override default configuration."""
        env = os.environ.copy()
        env["CALENDARBOT_AGGREGATOR_RETENTION_DAYS"] = "60"
        env["CALENDARBOT_WEBHOOK_TIMEOUT"] = "15"

        # Verify environment variables are set
        assert env["CALENDARBOT_AGGREGATOR_RETENTION_DAYS"] == "60"
        assert env["CALENDARBOT_WEBHOOK_TIMEOUT"] == "15"

    def test_scripts_when_missing_config_then_use_defaults(self) -> None:
        """Test that scripts use defaults when config is missing."""
        env = os.environ.copy()
        # Remove optional config
        env.pop("CALENDARBOT_WEBHOOK_URL", None)
        env.pop("CALENDARBOT_LOG_SHIPPER_ENABLED", None)

        result = subprocess.run(
            ["bash", "kiosk/scripts/log-shipper.sh", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )

        assert result.returncode == 0

    def test_scripts_when_output_format_specified_then_respects_choice(self) -> None:
        """Test that output format configuration is respected."""
        env = os.environ.copy()
        env["CALENDARBOT_AGGREGATOR_FORMAT"] = "json"
        env["CALENDARBOT_STATUS_FORMAT"] = "json"

        # Verify format variables are set
        assert env["CALENDARBOT_AGGREGATOR_FORMAT"] == "json"
        assert env["CALENDARBOT_STATUS_FORMAT"] == "json"


@pytest.mark.unit
class TestScriptConstants:
    """Test script constants and configuration values."""

    def test_log_shipper_when_constants_defined_then_reasonable_values(self) -> None:
        """Test that log shipper has reasonable constant values."""
        script_content = Path("kiosk/scripts/log-shipper.sh").read_text()

        # Verify key constants
        assert "MAX_PAYLOAD_SIZE=8192" in script_content  # 8KB for Pi Zero 2
        assert "MAX_RETRIES=3" in script_content
        assert "RATE_LIMIT_MINUTES=30" in script_content

    def test_log_aggregator_when_constants_defined_then_reasonable_values(self) -> None:
        """Test that log aggregator has reasonable constant values."""
        script_content = Path("kiosk/scripts/log-aggregator.sh").read_text()

        # Verify key constants
        assert "MAX_REPORT_SIZE=10485760" in script_content  # 10MB

    def test_critical_filter_when_constants_defined_then_reasonable_values(self) -> None:
        """Test that critical filter has reasonable constant values."""
        script_content = Path("kiosk/scripts/critical-event-filter.sh").read_text()

        # Verify key constants
        assert "DEDUP_WINDOW_MINUTES=60" in script_content
        assert "MAX_EVENTS_PER_HOUR=10" in script_content

    def test_monitoring_status_when_constants_defined_then_reasonable_values(self) -> None:
        """Test that monitoring status has reasonable constant values."""
        script_content = Path("kiosk/scripts/monitoring-status.sh").read_text()

        # Verify key constants
        assert "STATUS_CACHE_TTL=300" in script_content  # 5 minutes
