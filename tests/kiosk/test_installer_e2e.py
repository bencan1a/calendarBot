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

import pytest
import yaml

from tests.kiosk.e2e_helpers import (
    run_installer_in_container,
    container_file_exists,
    container_dir_exists,
    container_read_file,
    container_service_enabled,
    container_exec,
)


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
            clean_container, "/etc/systemd/system/calendarbot-lite@.service"
        ), "Service file not found"

        service_content = container_read_file(
            clean_container, "/etc/systemd/system/calendarbot-lite@.service"
        )
        assert "ExecStart" in service_content, "Service missing ExecStart"
        assert (
            "python -m calendarbot_lite" in service_content
        ), "Service not running calendarbot_lite"
        assert "User=%i" in service_content, "Service missing User=%i"

        # ✅ VERIFY: Service is enabled
        assert container_service_enabled(
            clean_container, "calendarbot-lite@testuser.service"
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
            watchdog_config["health_check"]["interval"] == 30
        ), "Watchdog interval incorrect"
        assert (
            watchdog_config["health_check"]["browser_heartbeat_timeout"] == 120
        ), "Watchdog heartbeat timeout incorrect"

        # ✅ VERIFY: Watchdog systemd service created
        assert container_file_exists(
            clean_container, "/etc/systemd/system/calendarbot-kiosk-watchdog@.service"
        ), "Watchdog service file not found"

        service = container_read_file(
            clean_container, "/etc/systemd/system/calendarbot-kiosk-watchdog@.service"
        )
        assert (
            "ExecStart=/usr/local/bin/calendarbot-watchdog" in service
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
