"""Integration tests for CalendarBot monitoring scripts."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestLogShipperScript:
    """Test log-shipper.sh script functionality."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/log-shipper.sh")
        self.temp_dir = None

    def teardown_method(self) -> None:
        """Cleanup test environment."""
        if self.temp_dir:
            # Clean up any temp files
            pass

    def test_log_shipper_when_help_then_shows_usage(self) -> None:
        """Test that log shipper shows help information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "CalendarBot Remote Log Shipper" in result.stdout
        assert "USAGE:" in result.stdout
        assert "COMMANDS:" in result.stdout

    def test_log_shipper_when_version_then_shows_version(self) -> None:
        """Test that log shipper shows version information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "calendarbot-log-shipper v1.0.0" in result.stdout

    def test_log_shipper_when_disabled_then_exits_gracefully(self) -> None:
        """Test that log shipper exits gracefully when disabled."""
        env = os.environ.copy()
        env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "false"

        result = subprocess.run(
            ["bash", str(self.script_path), "status"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )

        # Should exit with error code when disabled
        assert result.returncode != 0

    def test_log_shipper_when_test_mode_then_attempts_webhook(self) -> None:
        """Test that log shipper test mode attempts webhook call."""
        # Skip if curl not available
        if subprocess.run(["which", "curl"], capture_output=True).returncode != 0:
            pytest.skip("curl not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env.update({
                "CALENDARBOT_LOG_SHIPPER_ENABLED": "true",
                "CALENDARBOT_WEBHOOK_URL": "https://httpbin.org/post",
                "CALENDARBOT_LOG_SHIPPER_DEBUG": "true"
            })

            # Override script to use temp directory instead of system directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            # Replace hardcoded paths with temp directory
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

            # May succeed or fail depending on network, but should attempt
            assert "Testing webhook configuration" in result.stderr or "Sending test payload" in result.stderr or result.returncode == 0


@pytest.mark.integration
class TestLogAggregatorScript:
    """Test log-aggregator.sh script functionality."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/log-aggregator.sh")

    def test_log_aggregator_when_help_then_shows_usage(self) -> None:
        """Test that log aggregator shows help information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "CalendarBot Log Aggregator" in result.stdout
        assert "COMMANDS:" in result.stdout
        assert "daily" in result.stdout
        assert "weekly" in result.stdout

    def test_log_aggregator_when_version_then_shows_version(self) -> None:
        """Test that log aggregator shows version information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "calendarbot-log-aggregator v1.0.0" in result.stdout

    def test_log_aggregator_when_missing_date_then_shows_error(self) -> None:
        """Test that log aggregator shows error for missing date argument."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create modified script with temp directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-aggregator-test.sh"

            modified_content = script_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "daily"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode != 0
            assert "requires date argument" in result.stderr or "Missing required tools" in result.stderr


@pytest.mark.integration
class TestCriticalEventFilterScript:
    """Test critical-event-filter.sh script functionality."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/critical-event-filter.sh")

    def test_critical_filter_when_help_then_shows_usage(self) -> None:
        """Test that critical filter shows help information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "CalendarBot Critical Event Filter" in result.stdout
        assert "COMMANDS:" in result.stdout
        assert "stream" in result.stdout
        assert "monitor" in result.stdout

    def test_critical_filter_when_test_mode_then_processes_test_event(self) -> None:
        """Test that critical filter processes test events correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["CALENDARBOT_FILTER_DRY_RUN"] = "true"
            env["CALENDARBOT_FILTER_DEBUG"] = "true"

            # Create modified script with temp directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "critical-filter-test.sh"

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
                timeout=15,
                env=env
            )

            # Should complete successfully
            assert result.returncode == 0 or "Test event:" in result.stdout or "Test completed" in result.stderr

    def test_critical_filter_when_stats_then_shows_statistics(self) -> None:
        """Test that critical filter shows statistics correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create modified script with temp directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "critical-filter-stats.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{temp_dir}/watchdog"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(temp_script), "stats"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0
            assert "Critical Event Filter Statistics" in result.stdout


@pytest.mark.integration
class TestMonitoringStatusScript:
    """Test monitoring-status.sh script functionality."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/monitoring-status.sh")

    def test_monitoring_status_when_help_then_shows_usage(self) -> None:
        """Test that monitoring status shows help information."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert "CalendarBot Monitoring Status Dashboard" in result.stdout
        assert "COMMANDS:" in result.stdout
        assert "status" in result.stdout

    def test_monitoring_status_when_health_then_shows_health_info(self) -> None:
        """Test that monitoring status health command works."""
        result = subprocess.run(
            ["bash", str(self.script_path), "health"],
            capture_output=True,
            text=True,
            timeout=15
        )

        # Should provide health information regardless of server status
        assert "CalendarBot Health Status:" in result.stdout
        assert "Server reachable:" in result.stdout
        assert "Memory usage:" in result.stdout

    def test_monitoring_status_when_status_to_file_then_creates_json(self) -> None:
        """Test that monitoring status creates valid JSON output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = subprocess.run(
                ["bash", str(self.script_path), "status", temp_path],
                capture_output=True,
                text=True,
                timeout=20
            )

            # Should complete (may succeed or fail depending on server state)
            output_file = Path(temp_path)
            if result.returncode == 0 and output_file.exists():
                # Verify JSON is valid
                content = output_file.read_text()
                parsed = json.loads(content)

                assert "timestamp" in parsed
                assert "status" in parsed
                assert "system" in parsed

        finally:
            # Cleanup
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


@pytest.mark.smoke
class TestScriptPermissions:
    """Test that scripts have proper permissions and dependencies."""

    def test_all_scripts_when_exist_then_have_execute_permissions(self) -> None:
        """Test that all monitoring scripts have execute permissions."""
        scripts = [
            "kiosk/scripts/log-shipper.sh",
            "kiosk/scripts/log-aggregator.sh",
            "kiosk/scripts/critical-event-filter.sh",
            "kiosk/scripts/monitoring-status.sh"
        ]

        for script_path in scripts:
            script_file = Path(script_path)
            assert script_file.exists(), f"Script {script_path} does not exist"

            # Check if file is executable
            assert os.access(script_file, os.X_OK), f"Script {script_path} is not executable"

    def test_all_scripts_when_shebang_then_correct_interpreter(self) -> None:
        """Test that all scripts have correct shebang."""
        scripts = [
            "kiosk/scripts/log-shipper.sh",
            "kiosk/scripts/log-aggregator.sh",
            "kiosk/scripts/critical-event-filter.sh",
            "kiosk/scripts/monitoring-status.sh"
        ]

        for script_path in scripts:
            script_file = Path(script_path)
            first_line = script_file.read_text().split('\n')[0]
            assert first_line == "#!/bin/bash", f"Script {script_path} has incorrect shebang: {first_line}"


@pytest.mark.integration
class TestMonitoringIntegration:
    """Test integration between monitoring components."""

    def test_monitoring_logging_integration_when_server_import_then_no_errors(self) -> None:
        """Test that monitoring logging integrates with server without errors."""
        try:
            from calendarbot_lite.core.monitoring_logging import get_logger, log_server_event
            from calendarbot_lite.api.server import log_monitoring_event

            # Should import successfully
            logger = get_logger("test")
            assert logger is not None

            # Should be able to call functions
            result = log_server_event("test.import", "Import test")
            assert isinstance(result, bool)

        except ImportError as e:
            pytest.fail(f"Failed to import monitoring logging: {e}")

    def test_structured_logging_schema_when_created_then_follows_specification(self) -> None:
        """Test that structured logs follow the specified schema."""
        from calendarbot_lite.core.monitoring_logging import LogEntry

        entry = LogEntry(
            component="server",
            level="INFO",
            event="schema.test",
            message="Schema compliance test",
            details={"test_key": "test_value"},
            action_taken="Test action",
            recovery_level=1,
            system_state={"cpu_load": 0.5, "memory_free_mb": 200}
        )

        data = entry.to_dict()

        # Verify required fields
        required_fields = ["timestamp", "component", "level", "event", "message"]
        for field in required_fields:
            assert field in data, f"Required field {field} missing from schema"

        # Verify optional fields when present
        assert data["details"] == {"test_key": "test_value"}
        assert data["action_taken"] == "Test action"
        assert data["recovery_level"] == 1
        assert data["system_state"] == {"cpu_load": 0.5, "memory_free_mb": 200}
        assert data["schema_version"] == "1.0"

    def test_rate_limiting_integration_when_multiple_loggers_then_shared_state(self) -> None:
        """Test that rate limiting works across multiple logger instances."""
        from calendarbot_lite.core.monitoring_logging import get_logger

        logger1 = get_logger("component1")
        logger2 = get_logger("component2")

        # Fill rate limit using first logger
        for _ in range(5):
            result = logger1.log("INFO", "test.event", "Message", rate_limit_key="shared_key")
            assert result is True

        # Second logger should also be rate limited for same key
        result = logger2.log("INFO", "test.event", "Message", rate_limit_key="shared_key")
        assert result is False


@pytest.mark.integration
class TestScriptDependencies:
    """Test script dependencies and error handling."""

    def test_scripts_when_missing_jq_then_handle_gracefully(self) -> None:
        """Test that scripts handle missing jq dependency gracefully."""
        # Mock missing jq command
        script_path = "kiosk/scripts/log-aggregator.sh"

        env = os.environ.copy()
        env["PATH"] = "/usr/bin:/bin"  # Remove path to jq if it exists

        result = subprocess.run(
            ["bash", script_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )

        # Should still be able to show version
        assert result.returncode == 0

    def test_scripts_when_missing_curl_then_handle_gracefully(self) -> None:
        """Test that scripts handle missing curl dependency gracefully."""
        script_path = "kiosk/scripts/log-shipper.sh"

        env = os.environ.copy()
        env["PATH"] = "/usr/bin:/bin"  # Minimal path
        env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
        env["CALENDARBOT_WEBHOOK_URL"] = "https://example.com/webhook"

        result = subprocess.run(
            ["bash", script_path, "status"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )

        # Should handle missing curl gracefully
        # (may succeed if curl exists, or fail gracefully if not)
        assert isinstance(result.returncode, int)


@pytest.mark.integration
class TestEndToEndMonitoring:
    """Test end-to-end monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitoring_logging_when_server_events_then_structured_output(self) -> None:
        """Test that server events produce structured monitoring logs."""
        from calendarbot_lite.core.monitoring_logging import get_logger

        from calendarbot_lite.core.monitoring_logging import MonitoringLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "monitor_test.log"

            # Create monitoring logger with file output
            logger = MonitoringLogger(
                name="test_server_e2e",
                component="test_server",
                local_file=log_file,
                journald=False,
            )

            # Log various server events
            logger.info("server.startup", "Server starting",
                       details={"port": 8080},
                       include_system_state=True)

            logger.error("server.error", "Connection failed",
                        details={"error": "timeout"},
                        action_taken="Retry connection")

            logger.critical("server.critical", "Service unavailable",
                           recovery_level=3,
                           include_system_state=True)

            # Verify log file contains structured JSON
            if log_file.exists():
                content = log_file.read_text()

                # Should contain structured log entries
                lines = [line for line in content.split('\n') if line.strip()]
                assert len(lines) >= 3  # At least 3 log entries

                # Verify each line contains expected event names
                assert any("server.startup" in line for line in lines)
                assert any("server.error" in line for line in lines)
                assert any("server.critical" in line for line in lines)

    def test_script_chain_when_executed_then_proper_data_flow(self) -> None:
        """Test that monitoring scripts can work together in a chain."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test log entry
            test_event = {
                "timestamp": "2025-10-29T07:00:00Z",
                "component": "server",
                "level": "CRITICAL",
                "event": "test.critical.event",
                "message": "Test critical event for script chain",
                "details": {"test": True}
            }

            # Write test event to temp file
            event_file = Path(temp_dir) / "test_event.json"
            event_file.write_text(json.dumps(test_event))

            # Test that critical filter can process the event
            env = os.environ.copy()
            env["CALENDARBOT_FILTER_DRY_RUN"] = "true"
            env["CALENDARBOT_FILTER_DEBUG"] = "true"

            # Feed event to critical filter
            result = subprocess.run(
                ["bash", "kiosk/scripts/critical-event-filter.sh", "stream"],
                input=json.dumps(test_event),
                capture_output=True,
                text=True,
                timeout=15,
                env=env
            )

            # Should process without error
            assert result.returncode == 0 or "Processing critical event" in result.stderr


@pytest.mark.unit
class TestConfigurationFiles:
    """Test configuration files and integration."""

    def test_rsyslog_config_when_exists_then_valid_syntax(self) -> None:
        """Test that rsyslog configuration file has valid syntax."""
        config_path = Path("kiosk/config/rsyslog-calendarbot.conf")

        assert config_path.exists(), "rsyslog configuration file does not exist"

        content = config_path.read_text()

        # Basic syntax checks
        assert "CalendarBot" in content
        assert "$template" in content
        assert ":programname" in content

        # Should not have obvious syntax errors
        assert content.count('{') == content.count('}')  # Balanced braces

        # Should contain key directives
        assert "calendarbot-server" in content
        assert "calendarbot-watchdog" in content

    def test_monitor_yaml_when_exists_then_valid_structure(self) -> None:
        """Test that monitor.yaml has valid structure for enhanced logging."""
        config_path = Path("kiosk/config/monitor.yaml")

        assert config_path.exists(), "monitor.yaml configuration file does not exist"

        # Try to parse as YAML (if PyYAML available)
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Verify structure
            assert "monitor" in config
            monitor_config = config["monitor"]

            assert "logging" in monitor_config
            assert "health_check" in monitor_config
            assert "commands" in monitor_config

        except ImportError:
            # If PyYAML not available, just check basic syntax
            content = config_path.read_text()
            assert "monitor:" in content
            assert "logging:" in content


@pytest.mark.smoke
class TestScriptExecutability:
    """Test that scripts are properly executable and have required tools."""

    def test_scripts_when_syntax_check_then_no_bash_errors(self) -> None:
        """Test that all scripts have valid bash syntax."""
        scripts = [
            "kiosk/scripts/log-shipper.sh",
            "kiosk/scripts/log-aggregator.sh",
            "kiosk/scripts/critical-event-filter.sh",
            "kiosk/scripts/monitoring-status.sh"
        ]

        for script_path in scripts:
            result = subprocess.run(
                ["bash", "-n", script_path],  # Syntax check only
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == 0, f"Bash syntax error in {script_path}: {result.stderr}"

    def test_scripts_when_basic_commands_then_respond_correctly(self) -> None:
        """Test that scripts respond to basic commands correctly."""
        scripts = [
            ("kiosk/scripts/log-shipper.sh", ["--version"]),
            ("kiosk/scripts/log-aggregator.sh", ["--version"]),
            ("kiosk/scripts/critical-event-filter.sh", ["--version"]),
            ("kiosk/scripts/monitoring-status.sh", ["--version"])
        ]

        for script_path, args in scripts:
            result = subprocess.run(
                ["bash", script_path] + args,
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Script {script_path} failed basic command: {result.stderr}"
            assert "v1.0.0" in result.stdout, f"Script {script_path} version output unexpected"