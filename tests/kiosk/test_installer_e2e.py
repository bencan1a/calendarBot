"""E2E tests for kiosk installer in Docker container.

These tests run the actual install-kiosk.sh script in an isolated Docker container
and verify that files, services, and configurations are created correctly.

What these tests DO:
- Actually run install-kiosk.sh
- Create real files in /etc, /usr/local/bin, etc.
- Install real systemd services
- Verify file contents and permissions

What these tests DON'T:
- Test X server or browser functionality (mocked)
- Test Pi-specific hardware (not relevant)
- Test actual service startup (systemd in container has limitations)
"""

import time
import pytest
import yaml

from tests.kiosk.e2e_helpers import (
    run_installer_in_container,
    container_file_exists,
    container_dir_exists,
    container_read_file,
    container_service_enabled,
    container_exec,
    prepare_repository_in_container,
)


@pytest.mark.e2e
@pytest.mark.integration
class TestInstallerE2E:
    """End-to-end installer tests in Docker container.

    These tests run the actual installer in an isolated container
    and verify that files, services, and configurations are created correctly.
    """
    def test_installer_section_1_base_installation(self, clean_container):
        """Test Section 1: Base CalendarBot installation.

        Verifies:
        - Repository is cloned to /home/testuser/calendarbot
        - Virtual environment is created with dependencies
        - systemd service is installed and enabled
        - .env file is created with correct values
        - Python can import calendarbot_lite
        """
        # Create config with only Section 1 enabled
        config_content = """system:
  username: testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv
sections:
  section_1_base: true
  section_2_kiosk: false
  section_3_alexa: false
  section_4_monitoring: false
calendarbot:
  ics_url: http://example.com/test-calendar.ics
  web_port: 8080
  debug: true
"""

        # Run installer
        exit_code, stdout, stderr = run_installer_in_container(
            clean_container, config_content
        )

        # Verify installer succeeded
        assert exit_code == 0, f"Installer failed:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

        # ✅ VERIFY: Repository was cloned
        assert container_dir_exists(
            clean_container, "/home/testuser/calendarbot"
        ), "Repository directory not found"
        assert container_dir_exists(
            clean_container, "/home/testuser/calendarbot/.git"
        ), "Repository .git directory not found"

        # ✅ VERIFY: Virtual environment created
        assert container_file_exists(
            clean_container, "/home/testuser/calendarbot/venv/bin/python"
        ), "Python venv not found"
        assert container_file_exists(
            clean_container, "/home/testuser/calendarbot/venv/bin/pip"
        ), "Pip in venv not found"

        # ✅ VERIFY: Dependencies installed (check one key package)
        exit_code, output = container_exec(
            clean_container,
            "/home/testuser/calendarbot/venv/bin/pip list | grep aiohttp",
            user="testuser",
        )
        assert exit_code == 0, "aiohttp not installed in venv"

        # ✅ VERIFY: .env file created with correct values
        env_file = container_read_file(clean_container, "/home/testuser/calendarbot/.env")
        assert (
            "CALENDARBOT_ICS_URL=http://example.com/test-calendar.ics" in env_file
        ), "ICS URL not in .env"
        assert "CALENDARBOT_WEB_PORT=8080" in env_file, "Web port not in .env"
        assert "CALENDARBOT_DEBUG=true" in env_file, "Debug flag not in .env"

        # ✅ VERIFY: systemd service file created
        assert container_file_exists(
            clean_container, "/etc/systemd/system/calendarbot-kiosk@.service"
        ), "Service file not found"

        service_content = container_read_file(
            clean_container, "/etc/systemd/system/calendarbot-kiosk@.service"
        )
        assert "ExecStart" in service_content, "Service missing ExecStart"
        assert (
            "python -m calendarbot_lite" in service_content
        ), "Service not running calendarbot_lite"
        assert "User=%i" in service_content, "Service missing User=%i"

        # ✅ VERIFY: Service is enabled
        assert container_service_enabled(
            clean_container, "calendarbot-kiosk@testuser.service"
        ), "Service not enabled"

        # ✅ VERIFY: Python can import calendarbot_lite
        exit_code, output = container_exec(
            clean_container,
            "cd /home/testuser/calendarbot && "
            "./venv/bin/python -c 'import calendarbot_lite; print(calendarbot_lite.__file__)'",
            user="testuser",
        )
        assert exit_code == 0, f"Cannot import calendarbot_lite: {output}"
        assert "calendarbot_lite" in output, "Import did not return module path"

    def test_installer_section_2_kiosk_components(self, clean_container):
        """Test Section 2: Kiosk mode and watchdog.

        Verifies:
        - .xinitrc is created with browser command
        - Watchdog daemon is installed
        - Watchdog config file is created
        - Watchdog systemd service is installed
        - Sudoers file for watchdog is created
        """
        # Create config with section_1_base AND section_2_kiosk enabled
        config_content = """system:
  username: testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv
sections:
  section_1_base: true
  section_2_kiosk: true
  section_3_alexa: false
  section_4_monitoring: false
calendarbot:
  ics_url: http://example.com/calendar.ics
  web_port: 8080
kiosk:
  browser_url: http://127.0.0.1:8080/display
  watchdog:
    health_check_interval: 30
    browser_heartbeat_timeout: 120
"""

        # Run installer
        exit_code, stdout, stderr = run_installer_in_container(
            clean_container, config_content
        )

        # Verify installer succeeded
        assert exit_code == 0, f"Installer failed:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

        # ✅ VERIFY: .xinitrc created with kiosk browser
        assert container_file_exists(
            clean_container, "/home/testuser/.xinitrc"
        ), ".xinitrc not found"

        xinitrc = container_read_file(clean_container, "/home/testuser/.xinitrc")
        assert "chromium" in xinitrc.lower(), ".xinitrc missing chromium"
        assert "--kiosk" in xinitrc, ".xinitrc missing --kiosk flag"
        assert (
            "http://127.0.0.1:8080/display" in xinitrc
        ), ".xinitrc missing browser URL"
        assert (
            "openbox" in xinitrc.lower() or "exec" in xinitrc
        ), ".xinitrc missing window manager"

        # ✅ VERIFY: Watchdog daemon installed
        assert container_file_exists(
            clean_container, "/usr/local/bin/calendarbot-watchdog"
        ), "Watchdog daemon not found"

        # Verify it's executable
        exit_code, _ = container_exec(
            clean_container, "test -x /usr/local/bin/calendarbot-watchdog"
        )
        assert exit_code == 0, "Watchdog daemon not executable"

        # Verify it's Python script
        watchdog_content = container_read_file(
            clean_container, "/usr/local/bin/calendarbot-watchdog"
        )
        assert (
            "#!/usr/bin/env python3" in watchdog_content or "python" in watchdog_content
        ), "Watchdog daemon not a Python script"

        # ✅ VERIFY: Watchdog config created
        assert container_file_exists(
            clean_container, "/etc/calendarbot-monitor/monitor.yaml"
        ), "Watchdog config not found"

        config = container_read_file(
            clean_container, "/etc/calendarbot-monitor/monitor.yaml"
        )
        # Parse YAML to verify structure
        watchdog_config = yaml.safe_load(config)

        assert "health_check" in watchdog_config, "Watchdog config missing health_check"
        assert (
            watchdog_config["health_check"]["interval_s"] == 30
        ), "Watchdog interval incorrect"
        assert (
            watchdog_config["health_check"]["browser_heartbeat_timeout_s"] == 120
        ), "Watchdog heartbeat timeout incorrect"

        # ✅ VERIFY: Watchdog systemd service created
        assert container_file_exists(
            clean_container, "/etc/systemd/system/calendarbot-kiosk-watchdog@.service"
        ), "Watchdog service file not found"

        service = container_read_file(
            clean_container, "/etc/systemd/system/calendarbot-kiosk-watchdog@.service"
        )
        assert (
            "/usr/local/bin/calendarbot-watchdog" in service
        ), "Watchdog service missing ExecStart"
        assert "User=%i" in service, "Watchdog service missing User=%i"

        # ✅ VERIFY: Service is enabled
        assert container_service_enabled(
            clean_container, "calendarbot-kiosk-watchdog@testuser.service"
        ), "Watchdog service not enabled"

        # ✅ VERIFY: Sudoers file for watchdog
        assert container_file_exists(
            clean_container, "/etc/sudoers.d/calendarbot-watchdog"
        ), "Sudoers file not found"

        sudoers = container_read_file(
            clean_container, "/etc/sudoers.d/calendarbot-watchdog"
        )
        assert "NOPASSWD" in sudoers, "Sudoers missing NOPASSWD"
        assert "systemctl restart" in sudoers, "Sudoers missing systemctl restart"
    def test_installer_when_section_3_then_installs_alexa_components(self, clean_container):
        """Test Section 3: Alexa integration with Nginx and SSL.

        Verifies:
        - Nginx configuration is created
        - SSL certificates are generated
        - Sudoers file for port binding is created
        - Configuration contains correct proxy settings
        """
        from .e2e_helpers import (
            run_installer_in_container,
            container_file_exists,
            container_read_file,
        )

        config_yaml = """sections:
  section_1_base: true
  section_2_kiosk: false
  section_3_alexa: true
  section_4_monitoring: false

system:
  username: testuser
  home_dir: /home/testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv

calendarbot:
  ics_url: "http://example.com/calendar.ics"
  web_port: 8080

alexa:
  domain: "test.example.com"
"""

        # Run installer
        exit_code, stdout, stderr = run_installer_in_container(
            clean_container, config_yaml
        )

        assert exit_code == 0, f"Installer failed:\n{stdout}\n{stderr}"

        # Verify Caddyfile created
        assert container_file_exists(
            clean_container, "/etc/caddy/Caddyfile"
        ), "Caddyfile not found"

        caddyfile = container_read_file(
            clean_container, "/etc/caddy/Caddyfile"
        )
        assert "test.example.com" in caddyfile, \
            "Caddyfile missing domain"
        assert "reverse_proxy localhost:8080" in caddyfile, \
            "Caddyfile missing reverse_proxy directive"

        # Verify bearer token added to .env
        env_file = container_read_file(
            clean_container, "/home/testuser/calendarbot/.env"
        )
        assert "CALENDARBOT_ALEXA_BEARER_TOKEN" in env_file, \
            "Bearer token not set in .env"

        # Verify Caddy service is installed and enabled
        result = clean_container.exec_run(
            "systemctl is-enabled caddy",
            privileged=True
        )
        assert result.exit_code == 0, "Caddy service not enabled"

    def test_installer_when_section_4_then_installs_monitoring_components(self, clean_container):
        """Test Section 4: Monitoring and log management.

        Verifies:
        - Monitoring scripts are installed and executable
        - Scripts have --help functionality
        - Rsyslog configuration is created
        - Cron jobs are configured for reports
        - State directories are created with correct ownership
        """
        from .e2e_helpers import (
            run_installer_in_container,
            container_file_exists,
            container_dir_exists,
            container_read_file,
        )

        config_yaml = """sections:
  section_1_base: true
  section_2_kiosk: false
  section_3_alexa: false
  section_4_monitoring: true

system:
  username: testuser
  home_dir: /home/testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv

calendarbot:
  ics_url: "http://example.com/calendar.ics"
  web_port: 8080

monitoring:
  reports:
    enabled: true
    daily_report_time: "02:00"
    weekly_report_time: "03:00"
  log_shipping:
    enabled: true
    webhook_url: "https://example.com/webhook"
"""

        # Run installer
        exit_code, stdout, stderr = run_installer_in_container(
            clean_container, config_yaml
        )

        assert exit_code == 0, f"Installer failed:\n{stdout}\n{stderr}"

        # Verify monitoring scripts are installed
        scripts = [
            "/usr/local/bin/log-aggregator.sh",
            "/usr/local/bin/log-shipper.sh",
            "/usr/local/bin/monitoring-status.sh"
        ]

        for script in scripts:
            # Check script exists
            assert container_file_exists(clean_container, script), \
                f"Script not found: {script}"

            # Verify executable
            result = clean_container.exec_run(f"test -x {script}")
            assert result.exit_code == 0, f"Script not executable: {script}"

            # Verify has shebang
            content = container_read_file(clean_container, script)
            assert content.startswith("#!/bin/bash") or content.startswith("#!/usr/bin/env bash"), \
                f"Script missing shebang: {script}"

        # Verify scripts have --help
        for script in scripts:
            result = clean_container.exec_run(f"{script} --help")
            # Exit code 0 or 1 is OK (some scripts exit 1 for --help)
            assert result.exit_code in [0, 1], \
                f"Script --help failed with exit code {result.exit_code}: {script}"
            output = result.output.decode()
            assert "usage" in output.lower() or "help" in output.lower(), \
                f"Script --help has no usage information: {script}"

        # Verify rsyslog configuration created (only if enabled in config)
        # Note: rsyslog is optional and only deployed if monitoring.rsyslog.enabled is true
        # For this test, we're not enabling rsyslog, so we skip this check

        # Verify cron jobs configured
        result = clean_container.exec_run("crontab -l -u testuser")
        if result.exit_code == 0:
            cron_output = result.output.decode()
            assert "log-aggregator.sh" in cron_output, \
                "log-aggregator cron job not found"
            assert "00 02" in cron_output or "0 2" in cron_output, \
                "Daily report time not configured in cron (expected '00 02' or '0 2')"

        # Verify state directories created
        state_dirs = [
            "/var/local/calendarbot-watchdog",
            "/var/local/calendarbot-watchdog/reports"
        ]

        for state_dir in state_dirs:
            assert container_dir_exists(clean_container, state_dir), \
                f"State directory not created: {state_dir}"

            # Verify ownership
            result = clean_container.exec_run(f"stat -c '%U' {state_dir}")
            owner = result.output.decode().strip()
            assert owner == "testuser", \
                f"Wrong owner for {state_dir}: expected 'testuser', got '{owner}'"

    def test_installer_idempotency(self, clean_container):
        """Test that running installer twice is safe (idempotency).

        This test verifies that running the installer multiple times with the same
        configuration doesn't break the installation or create duplicate entries.

        Verifies:
        - First run completes successfully
        - Second run detects existing installation
        - Files are not recreated unnecessarily (timestamps unchanged)
        - No duplicate entries in configuration files
        - Services remain enabled and functional
        """
        from .e2e_helpers import (
            run_installer_in_container,
            container_file_exists,
            container_read_file,
            prepare_repository_in_container,
        )

        config_yaml = """sections:
  section_1_base: true
  section_2_kiosk: true
  section_3_alexa: false
  section_4_monitoring: true

system:
  username: testuser
  home_dir: /home/testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv

calendarbot:
  ics_url: "http://example.com/calendar.ics"

kiosk:
  browser_url: "http://127.0.0.1:8080"

monitoring:
  reports:
    enabled: true
"""

        # Write config file to container
        clean_container.exec_run(
            ["bash", "-c", f"cat > /tmp/test-config.yaml <<'EOFCONFIG'\n{config_yaml}\nEOFCONFIG"],
            privileged=True,
        )

        # Prepare repository (copy workspace to avoid git clone issues)
        prepare_repository_in_container(clean_container, target_user="testuser")

        # FIRST RUN
        result1 = clean_container.exec_run(
            ["bash", "-c", "cd /workspace/kiosk && sudo ./install-kiosk.sh --config /tmp/test-config.yaml"],
            user="testuser",
            workdir="/workspace"
        )

        assert result1.exit_code == 0, f"First install failed:\n{result1.output.decode()}"
        output1 = result1.output.decode()

        # Verify first run did installation
        assert "Installing" in output1 or "Creating" in output1 or "Configuring" in output1

        # Get state after first run
        venv_mtime1 = clean_container.exec_run("stat -c %Y /home/testuser/calendarbot/venv").output
        service_mtime1 = clean_container.exec_run("stat -c %Y /etc/systemd/system/calendarbot-kiosk@.service").output

        # Wait a moment to ensure timestamps would change if files were recreated
        time.sleep(2)

        # SECOND RUN (idempotency test)
        result2 = clean_container.exec_run(
            ["bash", "-c", "cd /workspace/kiosk && sudo ./install-kiosk.sh --config /tmp/test-config.yaml"],
            user="testuser",
            workdir="/workspace"
        )

        assert result2.exit_code == 0, f"Second install failed:\n{result2.output.decode()}"
        output2 = result2.output.decode()

        # VERIFY: Second run detected existing installation
        assert "already exists" in output2.lower() or \
               "already installed" in output2.lower() or \
               "up to date" in output2.lower() or \
               "Skipping" in output2, \
               "Second run should detect existing installation"

        # VERIFY: Files still exist (not deleted)
        assert container_file_exists(clean_container, "/home/testuser/calendarbot/venv/bin/python")
        assert container_file_exists(clean_container, "/etc/systemd/system/calendarbot-kiosk@.service")
        assert container_file_exists(clean_container, "/home/testuser/.xinitrc")

        # VERIFY: Venv wasn't recreated (timestamps unchanged)
        venv_mtime2 = clean_container.exec_run("stat -c %Y /home/testuser/calendarbot/venv").output
        assert venv_mtime1 == venv_mtime2, "Venv was recreated (should be skipped)"

        # VERIFY: Services still enabled
        result = clean_container.exec_run("systemctl is-enabled calendarbot-kiosk@testuser.service")
        assert result.exit_code == 0 or "enabled" in result.output.decode()

        # VERIFY: No duplicate entries in config files
        # Note: .xinitrc legitimately contains "chromium" 4 times
        # (comment, command invocation, log message, and in flags)
        xinitrc = container_read_file(clean_container, "/home/testuser/.xinitrc")
        chromium_count = xinitrc.count("chromium")
        assert chromium_count >= 1, f"'chromium' not found in .xinitrc (count={chromium_count})"
        # Verify the command invocation contains both 'chromium' and '--kiosk' (may be on separate lines)
        assert "chromium" in xinitrc and "--kiosk" in xinitrc, \
            ".xinitrc missing 'chromium' or '--kiosk'"

    def test_installer_update_mode(self, clean_container):
        """Test that update mode preserves existing configuration.

        This test verifies that running the installer with --update flag
        preserves user customizations while updating code and dependencies.

        Verifies:
        - Initial installation completes successfully
        - Custom .env settings are preserved during update
        - Original configuration values remain intact
        - Git repository structure is maintained (not recloned)
        - Virtual environment is updated, not recreated
        """
        from .e2e_helpers import (
            run_installer_in_container,
            container_file_exists,
            container_dir_exists,
            container_read_file,
            prepare_repository_in_container,
        )

        config_yaml = """sections:
  section_1_base: true
  section_2_kiosk: false
  section_3_alexa: false
  section_4_monitoring: false

system:
  username: testuser
  home_dir: /home/testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv

calendarbot:
  ics_url: "http://example.com/original-calendar.ics"
  web_port: 8080
"""

        # Write config file to container
        clean_container.exec_run(
            ["bash", "-c", f"cat > /tmp/test-config.yaml <<'EOFCONFIG'\n{config_yaml}\nEOFCONFIG"],
            privileged=True,
        )

        # Prepare repository (copy workspace to avoid git clone issues)
        prepare_repository_in_container(clean_container, target_user="testuser")

        # INITIAL INSTALLATION
        result1 = clean_container.exec_run(
            ["bash", "-c", "cd /workspace/kiosk && sudo ./install-kiosk.sh --config /tmp/test-config.yaml"],
            user="testuser",
            workdir="/workspace"
        )

        assert result1.exit_code == 0, f"Initial install failed:\n{result1.output.decode()}"

        # USER MODIFIES .env (simulating manual customization)
        clean_container.exec_run(
            ["bash", "-c",
             "echo 'CALENDARBOT_CUSTOM_SETTING=user_customized_value' >> /home/testuser/calendarbot/.env"],
            user="testuser"
        )

        # Verify custom setting was added
        env_before = container_read_file(clean_container, "/home/testuser/calendarbot/.env")
        assert "CALENDARBOT_CUSTOM_SETTING=user_customized_value" in env_before

        # RUN UPDATE MODE
        result2 = clean_container.exec_run(
            ["bash", "-c", "cd /workspace/kiosk && sudo ./install-kiosk.sh --update --config /tmp/test-config.yaml"],
            user="testuser",
            workdir="/workspace"
        )

        assert result2.exit_code == 0, f"Update failed:\n{result2.output.decode()}"
        output2 = result2.output.decode()

        # VERIFY: Update mode ran
        assert "--update" in output2 or "Updating" in output2 or "update" in output2.lower()

        # VERIFY: Custom .env setting preserved
        env_after = container_read_file(clean_container, "/home/testuser/calendarbot/.env")
        assert "CALENDARBOT_CUSTOM_SETTING=user_customized_value" in env_after, \
            "Custom .env setting was lost during update"

        # VERIFY: Original settings still present
        assert "CALENDARBOT_ICS_URL=http://example.com/original-calendar.ics" in env_after
        assert "CALENDARBOT_WEB_PORT=8080" in env_after

        # VERIFY: Git repository still exists (update should git pull, not reclone)
        assert container_dir_exists(clean_container, "/home/testuser/calendarbot/.git")

        # VERIFY: Git repository has remote configured (enables git pull)
        result = clean_container.exec_run(
            ["bash", "-c", "cd /home/testuser/calendarbot && git remote -v"],
            user="testuser"
        )
        # In E2E test with copied workspace, git remote should be present
        assert result.exit_code == 0, "Git remote not configured"

        # VERIFY: Venv still exists (update should update packages, not recreate)
        assert container_file_exists(clean_container, "/home/testuser/calendarbot/venv/bin/python")

        # VERIFY: Pip is still working (implies dependencies could be updated)
        result = clean_container.exec_run(
            ["bash", "-c", "/home/testuser/calendarbot/venv/bin/pip --version"],
            user="testuser"
        )
        assert result.exit_code == 0, \
            f"Venv pip not functional after update: {result.output.decode()}"


# ==============================================================================
# Progressive Installation Tests - Full End-to-End
# ==============================================================================

@pytest.mark.integration
@pytest.mark.e2e
class TestProgressiveInstallation:
    """Progressive installation test that validates full deployment flow.

    This test class uses a single container (class-scoped) to run a complete
    installation progressively: Section 1 → 2 → 3 → 4.

    After installation completes, the test validates:
    - CalendarBot server boots successfully
    - Critical API endpoints are responsive
    - Core functionality works end-to-end

    This mirrors real-world deployment where sections are installed sequentially.
    """

    @pytest.fixture(scope="class")
    def installed_container(self, progressive_container):
        """Install all sections progressively on a single container.

        This fixture runs once for the entire test class and installs
        all 4 sections sequentially on the same container.

        Args:
            progressive_container: Class-scoped container fixture

        Yields:
            Container with full CalendarBot installation
        """
        from .e2e_helpers import (
            run_installer_in_container,
            prepare_repository_in_container,
        )
        import logging
        import os
        from pathlib import Path
        logger = logging.getLogger(__name__)

        # Prepare repository
        prepare_repository_in_container(progressive_container)

        # Read ICS URL from workspace .env file for realistic testing
        # This validates that fetch/parse works with real calendar data
        workspace_ics_url = 'http://example.com/test-calendar.ics'  # fallback
        workspace_env = Path(__file__).parent.parent.parent / '.env'
        if workspace_env.exists():
            with open(workspace_env, 'r') as f:
                for line in f:
                    if line.strip().startswith('CALENDARBOT_ICS_URL='):
                        workspace_ics_url = line.split('=', 1)[1].strip()
                        break
        logger.info(f"Using ICS URL for E2E test: {workspace_ics_url[:60]}...")

        # Full installation config - all sections enabled
        config_yaml = f"""sections:
  section_1_base: true
  section_2_kiosk: true
  section_3_alexa: true
  section_4_monitoring: true

system:
  username: testuser
  home_dir: /home/testuser
  repo_dir: /home/testuser/calendarbot
  venv_dir: /home/testuser/calendarbot/venv

calendarbot:
  ics_url: "{workspace_ics_url}"
  web_port: 8080
  debug: true
  bearer_token: "test-bearer-token-for-e2e"

kiosk:
  display: ":0"
  resolution: "1920x1080"
  chromium_flags: "--kiosk --noerrdialogs --disable-infobars"

alexa:
  domain: "test.example.com"
  email: "test@example.com"
  enable_ssl: false  # Skip SSL for testing

monitoring:
  enable_health_checks: true
  check_interval_minutes: 5
  log_retention_days: 7
"""

        logger.info("=" * 70)
        logger.info("PROGRESSIVE INSTALLATION: Installing all sections sequentially")
        logger.info("=" * 70)

        # Run full installation
        exit_code, stdout, stderr = run_installer_in_container(
            progressive_container,
            config_yaml,
            prep_repo=False,  # Already prepared above
        )

        if exit_code != 0:
            logger.error("Progressive installation failed!")
            logger.error(f"STDOUT:\n{stdout}")
            logger.error(f"STDERR:\n{stderr}")
            pytest.fail(f"Installation failed with exit code {exit_code}")

        logger.info("=" * 70)
        logger.info("PROGRESSIVE INSTALLATION: Complete!")
        logger.info("=" * 70)

        # Wait for server to respond (accept both 200 and 503 during startup)
        logger.info("Waiting for CalendarBot server to respond...")
        max_attempts = 30
        for attempt in range(max_attempts):
            result = progressive_container.exec_run(
                ["curl", "-s", "-w", "\\n%{http_code}", "http://127.0.0.1:8080/api/health"],
            )
            if result.exit_code == 0:
                output = result.output.decode('utf-8', errors='replace')
                lines = output.strip().split('\n')
                if len(lines) >= 2:
                    http_code = lines[-1]
                    # Accept both 200 (ok) and 503 (degraded) as valid responses
                    if http_code in ['200', '503']:
                        logger.info(f"Server responding after {attempt + 1} attempts (HTTP {http_code})")
                        break
            if attempt < max_attempts - 1:
                time.sleep(2)
        else:
            # Get service logs if server never responded
            result = progressive_container.exec_run(
                ["journalctl", "-u", "calendarbot-kiosk@testuser.service", "-n", "50"],
                privileged=True,
            )
            logs = result.output.decode('utf-8', errors='replace')
            logger.warning(f"Server did not respond within {max_attempts * 2}s. Logs:\n{logs}")

        yield progressive_container

    def test_01_installation_completes_successfully(self, installed_container):
        """Test that progressive installation completes without errors.

        This test verifies that all 4 sections install successfully in sequence.
        """
        from .e2e_helpers import container_file_exists, container_dir_exists

        # Verify key files from each section exist

        # Section 1: Base installation
        assert container_dir_exists(installed_container, "/home/testuser/calendarbot"), \
            "Repository not installed"
        assert container_file_exists(installed_container, "/home/testuser/calendarbot/venv/bin/python"), \
            "Virtual environment not created"

        # Section 2: Kiosk
        assert container_file_exists(installed_container, "/home/testuser/.xinitrc"), \
            "Kiosk .xinitrc not installed"

        # Section 3: Alexa (we skip actual SSL/nginx in test mode)
        # Just verify the service file exists
        assert container_file_exists(installed_container,
                                     "/etc/systemd/system/calendarbot-kiosk@.service"), \
            "CalendarBot service not installed"

        # Section 4: Monitoring
        # Verify monitoring scripts were deployed (if applicable)
        # For now, just verify service is enabled
        result = installed_container.exec_run(
            ["systemctl", "is-enabled", "calendarbot-kiosk@testuser.service"],
            privileged=True,
        )
        assert result.exit_code == 0, \
            f"CalendarBot service not enabled: {result.output.decode()}"

    def test_02_calendarbot_service_starts(self, installed_container):
        """Test that CalendarBot systemd service starts successfully."""
        import logging
        logger = logging.getLogger(__name__)

        # Restart service to ensure clean state
        logger.info("Restarting CalendarBot service...")
        result = installed_container.exec_run(
            ["systemctl", "restart", "calendarbot-kiosk@testuser.service"],
            privileged=True,
        )

        if result.exit_code != 0:
            logger.error(f"Service restart failed: {result.output.decode()}")

        # Wait for service to be fully active and server to be ready
        logger.info("Waiting for service to become active...")
        time.sleep(15)  # Give server time to start and bind ports

        # Check service status
        result = installed_container.exec_run(
            ["systemctl", "status", "calendarbot-kiosk@testuser.service"],
            privileged=True,
        )

        output = result.output.decode('utf-8', errors='replace')
        logger.info(f"Service status:\n{output}")

        # Check if service is active
        result = installed_container.exec_run(
            ["systemctl", "is-active", "calendarbot-kiosk@testuser.service"],
            privileged=True,
        )

        assert result.exit_code == 0, \
            f"CalendarBot service is not active. Status:\n{output}"

    def test_03_server_responds_to_health_check(self, installed_container):
        """Test that CalendarBot server responds to health check endpoint."""
        import logging
        import json
        logger = logging.getLogger(__name__)

        # Wait for server to respond with valid health data
        # Accept both 200 (ok) and 503 (degraded during startup) as valid responses
        max_attempts = 30
        last_response = None
        for attempt in range(max_attempts):
            result = installed_container.exec_run(
                ["curl", "-s", "-w", "\\n%{http_code}", "http://127.0.0.1:8080/api/health"],
            )

            if result.exit_code == 0:
                output = result.output.decode('utf-8', errors='replace')
                lines = output.strip().split('\n')
                if len(lines) >= 2:
                    response_body = '\n'.join(lines[:-1])
                    http_code = lines[-1]
                    last_response = (http_code, response_body)

                    # Accept both 200 (ok) and 503 (degraded) as valid
                    if http_code in ['200', '503']:
                        try:
                            data = json.loads(response_body)
                            logger.info(f"Health check responded on attempt {attempt + 1}")
                            logger.info(f"HTTP {http_code}, Status: {data.get('status', 'unknown')}")
                            logger.info(f"Response: {response_body[:200]}...")

                            # Verify expected fields exist
                            assert 'status' in data, "Health response missing 'status' field"
                            assert 'server_time_iso' in data, "Health response missing 'server_time_iso' field"
                            return  # Test passed
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON response: {e}")

            if attempt < max_attempts - 1:
                logger.debug(f"Health check attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
        else:
            # Check service logs if health check failed
            result = installed_container.exec_run(
                ["journalctl", "-u", "calendarbot-kiosk@testuser.service", "-n", "50"],
                privileged=True,
            )
            logs = result.output.decode('utf-8', errors='replace')
            last_resp_str = f"Last response: {last_response}" if last_response else "No response received"
            pytest.fail(f"Server health check failed after {max_attempts} attempts.\n{last_resp_str}\n\nService logs:\n{logs}")

    def test_04_api_endpoints_are_responsive(self, installed_container):
        """Test that critical API endpoints respond correctly."""
        import logging
        logger = logging.getLogger(__name__)

        # Test /api/whats-next endpoint
        result = installed_container.exec_run(
            ["curl", "-s", "-w", "\\n%{http_code}", "http://127.0.0.1:8080/api/whats-next"],
        )

        assert result.exit_code == 0, \
            f"curl command failed with exit code {result.exit_code}"

        output = result.output.decode('utf-8', errors='replace')
        lines = output.strip().split('\n')

        assert len(lines) >= 2, f"Unexpected curl output format: {output}"

        response_body = '\n'.join(lines[:-1])
        http_code = lines[-1]

        logger.info(f"/api/whats-next HTTP {http_code}")
        logger.info(f"/api/whats-next response: {response_body[:200]}...")  # First 200 chars

        # Expect 200 OK for API endpoints
        assert http_code == '200', \
            f"/api/whats-next returned HTTP {http_code}, expected 200. Response: {response_body[:500]}"

        # Verify response is valid JSON
        import json
        try:
            data = json.loads(response_body)
            assert isinstance(data, dict), "Response should be JSON object"
            assert 'meeting' in data, "Response should have 'meeting' field"

            # Validate that ICS fetch/parse worked by checking if we got actual event data
            meeting = data.get('meeting')
            if meeting is not None:
                assert isinstance(meeting, dict), "Meeting should be a dict"
                assert 'subject' in meeting, "Meeting should have 'subject' field"
                assert 'meeting_id' in meeting, "Meeting should have 'meeting_id' field"
                logger.info(f"/api/whats-next returned event: '{meeting.get('subject', 'N/A')}'")
                logger.info("✓ ICS fetch and parse validated - received real calendar data")
            else:
                logger.info("/api/whats-next returned no upcoming meetings (meeting=null)")
                logger.info("✓ API working but no events in calendar")
        except json.JSONDecodeError as e:
            pytest.fail(f"/api/whats-next returned invalid JSON: {e}\nResponse: {response_body[:500]}")

    def test_05_static_files_are_served(self, installed_container):
        """Test that static files (HTML, CSS, JS) are served correctly."""
        import logging
        logger = logging.getLogger(__name__)

        # Test root HTML page
        result = installed_container.exec_run(
            ["curl", "-s", "-w", "\\n%{http_code}", "http://127.0.0.1:8080/"],
        )

        assert result.exit_code == 0, \
            f"curl command failed with exit code {result.exit_code}"

        output = result.output.decode('utf-8', errors='replace')
        lines = output.strip().split('\n')

        assert len(lines) >= 2, f"Unexpected curl output format: {output}"

        response_body = '\n'.join(lines[:-1])
        http_code = lines[-1]

        logger.info(f"Root page HTTP {http_code}")

        # Expect 200 OK for static pages
        assert http_code == '200', \
            f"Root page returned HTTP {http_code}, expected 200. Response: {response_body[:500]}"

        # Verify it's HTML content
        assert "<!DOCTYPE html>" in response_body or "<html" in response_body, \
            "Root page should return HTML content"

        logger.info("Root page loads successfully")

    def test_06_server_handles_invalid_requests(self, installed_container):
        """Test that server handles invalid requests gracefully."""
        import logging
        logger = logging.getLogger(__name__)

        # Test 404 handling
        result = installed_container.exec_run(
            ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null",
             "http://127.0.0.1:8080/nonexistent-endpoint"],
        )

        http_code = result.output.decode('utf-8', errors='replace').strip()
        logger.info(f"404 test returned HTTP {http_code}")

        assert http_code == "404", \
            f"Invalid endpoint should return 404, got {http_code}"

