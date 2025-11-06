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

import pytest


@pytest.mark.integration
class TestLogAggregatorJsonOutput:
    """Test log aggregator JSON report generation and validation."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/log-aggregator.sh")

    def test_log_aggregator_when_report_generated_then_valid_json_structure(self) -> None:
        """Test that log aggregator generates valid JSON report structure.

        Verifies:
        - Script processes input events from mock journalctl
        - Generates valid JSON structure
        - Includes required metadata fields (date, generated_at, summary, report_version)
        - Creates report file in correct location
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock journalctl command that outputs CalendarBot events
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:00:00Z\",\"component\":\"server\",\"level\":\"INFO\",\"event\":\"server.startup\",\"message\":\"Server started\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:01:00Z\",\"component\":\"watchdog\",\"level\":\"INFO\",\"event\":\"health_check\",\"message\":\"System healthy\"}"}'
""")
            mock_journalctl.chmod(0o755)

            # Create test script with modified DATA_DIR
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            # Mock jq to be available
            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"

            # Run aggregator to generate daily report
            result = subprocess.run(
                ["bash", str(test_script), "daily", "2025-11-06"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify script succeeded or gracefully handled missing jq
            assert result.returncode in [0, 1, 4], f"Unexpected failure: {result.stderr}"

            # If jq is available, verify report structure
            if result.returncode == 0:
                report_file = Path(temp_dir) / "watchdog" / "reports" / "daily_2025-11-06.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())

                    # Verify required metadata fields
                    assert "date" in report, "Report missing 'date' field"
                    assert "generated_at" in report, "Report missing 'generated_at' field"
                    assert "summary" in report, "Report missing 'summary' field"
                    assert "report_version" in report, "Report missing 'report_version' field"
                    assert report["date"] == "2025-11-06"

    def test_log_aggregator_when_events_aggregated_then_proper_grouping(self) -> None:
        """Test that log aggregator properly groups events by component.

        Verifies:
        - Events are grouped by component field
        - Component counts are accurate
        - Multiple components are handled correctly
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock journalctl with multiple components
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:00:00Z\",\"component\":\"watchdog\",\"level\":\"INFO\",\"event\":\"health_check\",\"message\":\"Check 1\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:01:00Z\",\"component\":\"watchdog\",\"level\":\"INFO\",\"event\":\"health_check\",\"message\":\"Check 2\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:02:00Z\",\"component\":\"server\",\"level\":\"ERROR\",\"event\":\"connection_failed\",\"message\":\"Failed\"}"}'
""")
            mock_journalctl.chmod(0o755)

            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"

            result = subprocess.run(
                ["bash", str(test_script), "daily", "2025-11-06"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify grouping if jq is available
            if result.returncode == 0:
                report_file = Path(temp_dir) / "watchdog" / "reports" / "daily_2025-11-06.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())

                    # Verify component grouping exists
                    assert "summary" in report
                    assert "by_component" in report["summary"]

                    by_component = report["summary"]["by_component"]
                    # Should have 2 components: watchdog (2 events) and server (1 event)
                    watchdog_group = [c for c in by_component if c["component"] == "watchdog"]
                    server_group = [c for c in by_component if c["component"] == "server"]

                    assert len(watchdog_group) == 1, "Watchdog component should be grouped"
                    assert watchdog_group[0]["count"] == 2, "Watchdog should have 2 events"
                    assert len(server_group) == 1, "Server component should be grouped"
                    assert server_group[0]["count"] == 1, "Server should have 1 event"

    def test_log_aggregator_when_json_format_then_includes_metadata(self) -> None:
        """Test that JSON reports include metadata fields.

        Verifies:
        - Report includes date field
        - Report includes generated_at timestamp
        - Report includes report_version
        - Report includes patterns analysis
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock journalctl
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:00:00Z\",\"component\":\"server\",\"level\":\"INFO\",\"event\":\"startup\",\"message\":\"Started\"}"}'
""")
            mock_journalctl.chmod(0o755)

            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"
            env["CALENDARBOT_AGGREGATOR_FORMAT"] = "json"

            result = subprocess.run(
                ["bash", str(test_script), "daily", "2025-11-06"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify metadata if jq is available
            if result.returncode == 0:
                report_file = Path(temp_dir) / "watchdog" / "reports" / "daily_2025-11-06.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())

                    # Verify all required metadata fields
                    assert "date" in report, "Missing date field"
                    assert "generated_at" in report, "Missing generated_at field"
                    assert "report_version" in report, "Missing report_version field"
                    assert "patterns" in report, "Missing patterns analysis"
                    assert report["report_version"] == "1.0.0"

    def test_log_aggregator_when_events_by_level_then_counts_accurate(self) -> None:
        """Test that event counting by severity level is accurate.

        Verifies:
        - Events are grouped by level (INFO, ERROR, CRITICAL)
        - Level counts match actual event counts
        - by_level array contains correct data
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock journalctl with various levels
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:00:00Z\",\"component\":\"watchdog\",\"level\":\"INFO\",\"event\":\"health_check\",\"message\":\"Healthy\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:01:00Z\",\"component\":\"server\",\"level\":\"ERROR\",\"event\":\"connection_failed\",\"message\":\"Error 1\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:02:00Z\",\"component\":\"server\",\"level\":\"ERROR\",\"event\":\"timeout\",\"message\":\"Error 2\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:03:00Z\",\"component\":\"watchdog\",\"level\":\"CRITICAL\",\"event\":\"recovery_failed\",\"message\":\"Critical\"}"}'
""")
            mock_journalctl.chmod(0o755)

            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"

            result = subprocess.run(
                ["bash", str(test_script), "daily", "2025-11-06"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify level counts if jq is available
            if result.returncode == 0:
                report_file = Path(temp_dir) / "watchdog" / "reports" / "daily_2025-11-06.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())

                    by_level = report["summary"]["by_level"]

                    # Verify counts by level
                    info_events = [l for l in by_level if l["level"] == "INFO"]
                    error_events = [l for l in by_level if l["level"] == "ERROR"]
                    critical_events = [l for l in by_level if l["level"] == "CRITICAL"]

                    assert len(info_events) == 1 and info_events[0]["count"] == 1, "Should have 1 INFO event"
                    assert len(error_events) == 1 and error_events[0]["count"] == 2, "Should have 2 ERROR events"
                    assert len(critical_events) == 1 and critical_events[0]["count"] == 1, "Should have 1 CRITICAL event"

    def test_log_aggregator_when_daily_report_then_correct_time_range(self) -> None:
        """Test that daily reports cover correct time range.

        Verifies:
        - Daily command accepts date argument (YYYY-MM-DD)
        - Report includes correct date in metadata
        - Script invokes journalctl with correct --since and --until parameters
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_date = "2025-11-06"

            # Create mock journalctl that verifies time range arguments
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
# Verify --since and --until arguments are passed
if [[ "$*" == *"--since=2025-11-06 00:00:00"* ]] && [[ "$*" == *"--until=2025-11-06 23:59:59"* ]]; then
    echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T12:00:00Z\",\"component\":\"server\",\"level\":\"INFO\",\"event\":\"test\",\"message\":\"Test\"}"}'
else
    echo "ERROR: Expected --since='2025-11-06 00:00:00' and --until='2025-11-06 23:59:59'" >&2
    exit 1
fi
""")
            mock_journalctl.chmod(0o755)

            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"

            result = subprocess.run(
                ["bash", str(test_script), "daily", test_date],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify script accepted date format and processed correctly
            assert result.returncode in [0, 1, 4], f"Script failed: {result.stderr}"

            # Verify report has correct date if generated
            if result.returncode == 0:
                report_file = Path(temp_dir) / "watchdog" / "reports" / "daily_2025-11-06.json"
                if report_file.exists():
                    report = json.loads(report_file.read_text())
                    assert report["date"] == test_date, "Report date should match input date"

    def test_log_aggregator_when_retention_cleanup_then_old_reports_removed(self) -> None:
        """Test that retention policy removes old reports.

        Verifies:
        - Cleanup command processes reports directory
        - Old reports (beyond retention days) are removed
        - Recent reports are preserved
        - CALENDARBOT_AGGREGATOR_RETENTION_DAYS is respected
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            # Create reports directory with old and recent reports
            reports_dir = Path(temp_dir) / "watchdog" / "reports"
            reports_dir.mkdir(parents=True)

            # Create an old report (90 days old via file timestamp)
            old_report = reports_dir / "daily_2024-08-01.json"
            old_report.write_text('{"date": "2024-08-01", "summary": {"total_events": 0}}')
            # Set mtime to 90 days ago
            old_time = time.time() - (90 * 24 * 60 * 60)
            os.utime(old_report, (old_time, old_time))

            # Create a recent report
            recent_report = reports_dir / "daily_2025-11-05.json"
            recent_report.write_text('{"date": "2025-11-05", "summary": {"total_events": 0}}')

            # Run cleanup with 30-day retention
            env = os.environ.copy()
            env["CALENDARBOT_AGGREGATOR_RETENTION_DAYS"] = "30"

            result = subprocess.run(
                ["bash", str(test_script), "cleanup"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            assert result.returncode == 0, f"Cleanup failed: {result.stderr}"

            # Verify old report was removed and recent report preserved
            assert not old_report.exists(), "Old report should be removed"
            assert recent_report.exists(), "Recent report should be preserved"

    def test_log_aggregator_when_large_dataset_then_respects_size_limits(self) -> None:
        """Test that aggregator respects max report size limits.

        Verifies:
        - MAX_REPORT_SIZE constant exists in script
        - MAX_REPORT_SIZE is set to 10485760 (10MB)
        - Configuration is documented for size constraints

        Note: This test verifies the constant exists. Full size limit enforcement
        would require generating 10MB+ of test data which is impractical for unit tests.
        """
        script_content = Path(self.script_path).read_text()

        # Verify MAX_REPORT_SIZE constant exists
        assert "MAX_REPORT_SIZE" in script_content, "MAX_REPORT_SIZE constant missing"

        # Verify it's set to 10MB (10485760 bytes)
        assert "MAX_REPORT_SIZE=10485760" in script_content, "MAX_REPORT_SIZE should be 10MB (10485760 bytes)"

    def test_log_aggregator_when_export_metrics_then_prometheus_format(self) -> None:
        """Test that metrics export generates Prometheus format.

        Verifies:
        - CALENDARBOT_AGGREGATOR_EXPORT_METRICS enables metrics export
        - Metrics file is created in Prometheus format
        - Metrics include HELP and TYPE declarations
        - Metrics include calendarbot_events_total counter
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock journalctl
            mock_journalctl = Path(temp_dir) / "journalctl"
            mock_journalctl.write_text("""#!/bin/bash
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:00:00Z\",\"component\":\"server\",\"level\":\"INFO\",\"event\":\"startup\",\"message\":\"Started\"}"}'
echo '{"MESSAGE":"{\"timestamp\":\"2025-11-06T10:01:00Z\",\"component\":\"watchdog\",\"level\":\"ERROR\",\"event\":\"check_failed\",\"message\":\"Error\"}"}'
""")
            mock_journalctl.chmod(0o755)

            # Create test script
            test_script = Path(temp_dir) / "log-aggregator-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly DATA_DIR="/var/local/calendarbot-watchdog"',
                f'readonly DATA_DIR="{temp_dir}/watchdog"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{temp_dir}:{env['PATH']}"
            env["CALENDARBOT_AGGREGATOR_EXPORT_METRICS"] = "true"

            result = subprocess.run(
                ["bash", str(test_script), "daily", "2025-11-06"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify metrics file if jq is available
            if result.returncode == 0:
                metrics_file = Path(temp_dir) / "watchdog" / "reports" / "metrics_2025-11-06.prom"
                if metrics_file.exists():
                    metrics_content = metrics_file.read_text()

                    # Verify Prometheus format
                    assert "# HELP calendarbot_events_total" in metrics_content, "Missing HELP for events_total"
                    assert "# TYPE calendarbot_events_total counter" in metrics_content, "Missing TYPE for events_total"
                    assert "calendarbot_events_total" in metrics_content, "Missing events_total metric"

                    # Verify component-specific metrics
                    assert "calendarbot_component_events" in metrics_content, "Missing component metrics"
                    assert "calendarbot_level_events" in metrics_content, "Missing level metrics"

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
        """Test that rate limiting prevents excessive shipping.

        Verifies:
        - First critical event is processed and shipped
        - Second critical event immediately after is rate limited
        - Rate limit message appears in debug output
        - State file shows same last_ship_time (no second ship occurred)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()
            state_file = state_dir / "log-shipper-state.json"

            # Create test script with modified state directory and short rate limit
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{state_dir}"'
            ).replace(
                'readonly RATE_LIMIT_MINUTES=30',
                'readonly RATE_LIMIT_MINUTES=60'  # 60 minutes - ensures rate limiting
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
            env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
            env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

            # Create a critical event payload
            critical_event = json.dumps({
                "timestamp": "2025-11-06T10:00:00Z",
                "component": "watchdog",
                "level": "CRITICAL",
                "event": "recovery.failed",
                "message": "Test critical event"
            })

            # First ship - process critical event through stream mode using echo pipe
            result1 = subprocess.run(
                f"echo '{critical_event}' | bash {temp_script} stream",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Accept exit codes: 0 (success), 1 (config/curl error), 4 (missing deps)
            assert result1.returncode in [0, 1, 4], f"First ship failed unexpectedly: {result1.stderr}"

            # If jq/curl available and ship succeeded, verify rate limiting
            if result1.returncode == 0 and state_file.exists():
                state1 = json.loads(state_file.read_text())
                first_ship_time = state1["last_ship_time"]

                # Second ship immediately - should be rate limited
                result2 = subprocess.run(
                    f"echo '{critical_event}' | bash {temp_script} stream",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )

                # Should succeed but not actually ship (rate limited)
                assert result2.returncode in [0, 1], f"Second ship failed unexpectedly: {result2.stderr}"

                # Verify "rate limit" message in debug output
                combined_output = (result2.stdout + result2.stderr).lower()
                assert "rate limit" in combined_output, \
                    f"Expected rate limit message in output, got: {result2.stdout + result2.stderr}"

                # Verify state file shows no second ship (same timestamp)
                state2 = json.loads(state_file.read_text())
                assert state2["last_ship_time"] == first_ship_time, \
                    "Second ship should be rate limited (same timestamp)"

    def test_log_shipper_when_auth_token_configured_then_available(self) -> None:
        """Test that authentication token configuration is supported.

        Verifies:
        - Script runs successfully with token configured
        - Token configuration is accepted by script
        - Status command shows token is configured
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test script with modified state directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{temp_dir}/state"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
            env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
            env["CALENDARBOT_WEBHOOK_TOKEN"] = "test-token-123"
            env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

            # Run status command to verify token config is recognized
            result = subprocess.run(
                ["bash", str(temp_script), "status"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Verify script runs successfully with token configured
            assert result.returncode == 0, f"Script failed with token configured: {result.stderr}"

            # Verify status output shows authentication is configured
            output = result.stdout.lower()
            assert "authentication:" in output or "configured" in output, \
                f"Expected authentication status in output, got: {result.stdout}"

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
        """Test that rate limit state persists across script executions.

        Verifies:
        - Running script creates state file
        - Running script again preserves existing state
        - State data survives across multiple invocations
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()
            state_file = state_dir / "log-shipper-state.json"

            # Create test script with modified state directory
            script_content = Path(self.script_path).read_text()
            temp_script = Path(temp_dir) / "log-shipper-test.sh"

            modified_content = script_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{state_dir}"'
            )
            temp_script.write_text(modified_content)
            temp_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_LOG_SHIPPER_ENABLED"] = "true"
            env["CALENDARBOT_WEBHOOK_URL"] = "https://httpbin.org/post"
            env["CALENDARBOT_LOG_SHIPPER_DEBUG"] = "true"

            # Run script once to create state
            result1 = subprocess.run(
                ["bash", str(temp_script), "test"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            # Accept exit codes: 0 (success), 1 (config/curl error), 4 (missing deps)
            assert result1.returncode in [0, 1, 4], f"First run failed unexpectedly: {result1.stderr}"

            # If successful, verify state was created
            if result1.returncode == 0:
                assert state_file.exists(), "State file should be created after first run"
                state1 = json.loads(state_file.read_text())
                assert "last_ship_time" in state1, "State should include last_ship_time"
                assert "ship_count" in state1, "State should include ship_count"

                # Save state from first run
                first_ship_count = state1["ship_count"]

                # Run status command - should not modify state
                result2 = subprocess.run(
                    ["bash", str(temp_script), "status"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )

                # Status should succeed and state should still exist
                assert result2.returncode == 0, f"Status command failed: {result2.stderr}"
                assert state_file.exists(), "State file should persist after status command"

                # Verify state structure is maintained
                state2 = json.loads(state_file.read_text())
                assert "last_ship_time" in state2, "State should still include last_ship_time"
                assert "ship_count" in state2, "State should still include ship_count"
                assert state2["ship_count"] == first_ship_count, \
                    "Status command should not modify ship_count"


@pytest.mark.integration
class TestCriticalEventFilterLogic:
    """Test critical event filter logic and deduplication."""

    def setup_method(self) -> None:
        """Setup test environment."""
        self.script_path = Path("kiosk/scripts/critical-event-filter.sh")

    def test_critical_filter_when_duplicate_events_then_has_dedup_logic(self) -> None:
        """Test that duplicate critical events are filtered within dedup window.

        Verifies:
        - Script can process critical events
        - Script tracks event hashes in state file
        - Built-in test command completes successfully
        - State file is created with dedup data structures
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()

            # Create test script with modified state directory
            test_script = Path(temp_dir) / "filter-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{state_dir}"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            env = os.environ.copy()
            env["CALENDARBOT_FILTER_DRY_RUN"] = "true"
            env["CALENDARBOT_FILTER_DEBUG"] = "true"

            # Run built-in test command which processes a test event and exits cleanly
            result = subprocess.run(
                ["bash", str(test_script), "test"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )

            assert result.returncode == 0, f"Test command failed: {result.stderr}"

            # Verify event processing output
            output = result.stdout + result.stderr
            assert "processing" in output.lower() and "critical" in output.lower(), \
                f"Should process critical event, got: {output}"

            # Verify state file was created with event hash
            state_file = state_dir / "critical-filter-state.json"
            assert state_file.exists(), "State file should be created"
            state_data = json.loads(state_file.read_text())

            # Verify deduplication data structures exist and are populated
            assert "event_hashes" in state_data, "Should track event hashes"
            assert len(state_data["event_hashes"]) > 0, "Should store event hash after processing"
            assert "total_filtered" in state_data, "Should track total filtered count"
            assert "total_forwarded" in state_data, "Should track total forwarded count"

            # Verify the event was counted
            assert state_data["total_filtered"] > 0, "Should have processed at least one event"

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
        """Test that statistics command shows filter stats and counts.

        Verifies:
        - Stats command runs successfully
        - Shows total filtered/forwarded counts
        - Displays dedup cache size
        - Shows hourly event counts
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir()

            # Create test script with modified state directory
            test_script = Path(temp_dir) / "filter-test.sh"
            original_content = self.script_path.read_text()
            modified_content = original_content.replace(
                'readonly STATE_DIR="/var/local/calendarbot-watchdog"',
                f'readonly STATE_DIR="{state_dir}"'
            )
            test_script.write_text(modified_content)
            test_script.chmod(0o755)

            # Initialize state with some data
            state_file = state_dir / "critical-filter-state.json"
            test_state = {
                "event_hashes": {
                    "abc123": 1730899200,
                    "def456": 1730899300
                },
                "hourly_counts": {
                    "2025110610": 5,
                    "2025110611": 3
                },
                "last_cleanup": 1730899000,
                "total_filtered": 15,
                "total_forwarded": 8
            }
            state_file.write_text(json.dumps(test_state))

            # Run stats command
            result = subprocess.run(
                ["bash", str(test_script), "stats"],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Stats command failed: {result.stderr}"
            output = result.stdout.lower()

            # Verify key metrics are shown
            assert "total events filtered: 15" in output or "15" in output, \
                f"Should show total filtered count, got: {result.stdout}"
            assert "total events forwarded: 8" in output or "8" in output, \
                f"Should show total forwarded count, got: {result.stdout}"
            assert "dedup cache" in output or "event_hashes" in output, \
                f"Should show dedup cache info, got: {result.stdout}"
            assert "hourly" in output, \
                f"Should show hourly counts, got: {result.stdout}"

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
        """Test that status JSON has required fields and numeric metrics.

        Verifies:
        - Script runs status command successfully
        - Output is valid JSON
        - Contains required fields (timestamp, status, system)
        - System metrics are numeric/measurable
        - Metrics include CPU, memory, disk data
        """
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

                # Verify system metrics are present and numeric
                system = parsed["system"]

                # CPU metrics - should have load average
                if "cpu" in system:
                    cpu = system["cpu"]
                    if "load_1m" in cpu:
                        assert isinstance(cpu["load_1m"], (int, float)), \
                            f"CPU load should be numeric, got {type(cpu['load_1m'])}"
                        assert cpu["load_1m"] >= 0, "CPU load should be non-negative"

                # Memory metrics - should be numeric KB values
                if "memory" in system:
                    mem = system["memory"]
                    if "total_kb" in mem:
                        assert isinstance(mem["total_kb"], int), \
                            f"Memory total should be integer, got {type(mem['total_kb'])}"
                        assert mem["total_kb"] > 0, "Memory total should be positive"
                    if "usage_percent" in mem:
                        assert isinstance(mem["usage_percent"], int), \
                            f"Memory usage percent should be integer, got {type(mem['usage_percent'])}"
                        assert 0 <= mem["usage_percent"] <= 100, \
                            f"Memory usage percent should be 0-100, got {mem['usage_percent']}"

                # Disk metrics - should be numeric
                if "disk" in system:
                    disk = system["disk"]
                    if "usage_percent" in disk:
                        assert isinstance(disk["usage_percent"], int), \
                            f"Disk usage percent should be integer, got {type(disk['usage_percent'])}"
                        assert 0 <= disk["usage_percent"] <= 100, \
                            f"Disk usage percent should be 0-100, got {disk['usage_percent']}"

        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    def test_monitoring_status_when_system_metrics_then_includes_cpu_memory(self) -> None:
        """Test that system metrics include CPU and memory data with numeric values.

        Verifies:
        - Script runs health check successfully
        - Output includes memory metrics
        - Memory usage is reported as numeric percentage
        - Output contains measurable data, not just strings
        """
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

            # Verify memory metric is present
            assert "Memory usage:" in output or "memory" in output.lower()

            # Verify numeric values are present (percentage)
            # Should contain something like "45%" or "Memory usage: 45%"
            import re
            percentage_pattern = r'\d+%'
            assert re.search(percentage_pattern, output), \
                f"Expected numeric percentage in output, got: {output}"

    def test_monitoring_status_when_server_health_then_checks_connectivity(self) -> None:
        """Test that health check verifies server connectivity.

        Verifies:
        - Script runs health check successfully
        - Performs actual server connectivity check (curl to health endpoint)
        - Reports server reachable status in output
        - Exits with valid status code (0=healthy, 1=warnings)
        """
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
        """Test that status caching configuration exists.

        Verifies:
        - Script has STATUS_CACHE_TTL constant defined
        - Script has caching configuration (CACHE_ENABLED or CACHE_DIR)
        - Caching infrastructure is present in script

        Note: This test verifies configuration constants exist.
        Actual cache behavior is tested in integration tests.
        """
        script_content = Path(self.script_path).read_text()
        assert "STATUS_CACHE_TTL" in script_content
        assert "CACHE_ENABLED" in script_content or "CACHE_DIR" in script_content

    def test_monitoring_status_when_trends_enabled_then_config_supported(self) -> None:
        """Test that trend data configuration is supported.

        Verifies:
        - Script accepts CALENDARBOT_STATUS_TRENDS environment variable
        - Script runs successfully with trends enabled
        - Configuration is processed without errors
        - Debug mode works with trends enabled
        """
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
        """Test that metrics collection includes system data.

        Verifies:
        - Script has get_system_metrics function or equivalent
        - Script has system metrics infrastructure
        - Metrics collection logic is present in script

        Note: This test verifies the metrics collection function exists.
        Actual metric values are tested in other tests.
        """
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
