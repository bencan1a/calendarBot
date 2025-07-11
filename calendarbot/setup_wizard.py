"""Interactive configuration wizard for Calendar Bot setup."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import yaml

from config.settings import CalendarBotSettings

from .ics.exceptions import ICSError
from .ics.fetcher import ICSFetcher
from .ics.models import ICSAuth, ICSSource

# Import security logging
from .security import SecurityEventLogger, mask_credentials

logger = logging.getLogger(__name__)


class CalendarServiceTemplate:
    """Template for popular calendar services."""

    def __init__(
        self,
        name: str,
        description: str,
        url_pattern: str,
        auth_type: str = "none",
        instructions: str = "",
    ):
        self.name = name
        self.description = description
        self.url_pattern = url_pattern
        self.auth_type = auth_type
        self.instructions = instructions


class SetupWizard:
    """Interactive configuration wizard for Calendar Bot."""

    # Service templates for popular calendar providers
    SERVICE_TEMPLATES = {
        "outlook": CalendarServiceTemplate(
            name="Microsoft Outlook",
            description="Outlook.com or Office 365 calendar",
            url_pattern=r"https://outlook\.live\.com/owa/calendar/.*/calendar\.ics",
            auth_type="none",
            instructions="""
To get your Outlook calendar ICS URL:
1. Go to Outlook.com and sign in
2. Click on Calendar
3. Click on 'Add calendar' → 'Subscribe from web'
4. Copy the ICS URL from your calendar settings
5. Or go to Settings → View all Outlook settings → Calendar → Shared calendars
            """,
        ),
        "google": CalendarServiceTemplate(
            name="Google Calendar",
            description="Google Calendar with secret iCal URL",
            url_pattern=r"https://calendar\.google\.com/calendar/ical/.*/basic\.ics",
            auth_type="none",
            instructions="""
To get your Google Calendar ICS URL:
1. Go to Google Calendar and sign in
2. Click on Settings (gear icon) → Settings
3. Select your calendar from the left sidebar
4. Scroll down to 'Integrate calendar'
5. Copy the 'Secret address in iCal format' URL
            """,
        ),
        "icloud": CalendarServiceTemplate(
            name="Apple iCloud",
            description="iCloud calendar (public sharing required)",
            url_pattern=r"https://p\d+-caldav\.icloud\.com/published/.*",
            auth_type="none",
            instructions="""
To get your iCloud calendar ICS URL:
1. Open Calendar app on Mac or go to iCloud.com
2. Right-click on your calendar name
3. Select 'Share Calendar...'
4. Choose 'Public Calendar'
5. Copy the provided URL
            """,
        ),
        "caldav": CalendarServiceTemplate(
            name="CalDAV Server",
            description="Generic CalDAV server (Nextcloud, ownCloud, etc.)",
            url_pattern=r"https://.*\.php/dav/calendars/.*/\?export",
            auth_type="basic",
            instructions="""
For CalDAV servers (Nextcloud, ownCloud, etc.):
1. Log into your server's web interface
2. Go to Calendar app
3. Click on the calendar settings (3 dots menu)
4. Select 'Download' or 'Export'
5. Use the export URL with your username/password
            """,
        ),
        "custom": CalendarServiceTemplate(
            name="Custom/Other",
            description="Custom ICS URL or other calendar service",
            url_pattern=r"https?://.*\.ics",
            auth_type="none",
            instructions="""
For other calendar services:
1. Look for 'Export', 'Subscribe', or 'iCal' options
2. Copy the ICS/iCal URL
3. If authentication is required, you'll configure that next
            """,
        ),
    }

    def __init__(self) -> None:
        """Initialize setup wizard."""
        self.config_data: Dict[str, Any] = {}
        self.settings = None

    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 60)
        print(f"📅 {title}")
        print("=" * 60)

    def print_section(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n🔧 {title}")
        print("-" * 40)

    def get_input(
        self,
        prompt: str,
        default: Optional[str] = None,
        required: bool = True,
        validate_func: Optional[Callable[[str], bool]] = None,
    ) -> str:
        """Get user input with validation."""
        while True:
            if default:
                full_prompt = f"{prompt} [{default}]: "
            else:
                full_prompt = f"{prompt}: "

            response = input(full_prompt).strip()

            # Use default if no response and default provided
            if not response and default:
                response = default

            # Check if required
            if required and not response:
                print("❌ This field is required. Please enter a value.")
                continue

            # Run validation if provided
            if validate_func and response:
                try:
                    if validate_func(response):
                        return response
                    else:
                        print("❌ Invalid input. Please try again.")
                        continue
                except Exception as e:
                    print(f"❌ Validation error: {e}")
                    continue

            return response

    def get_choice(
        self, prompt: str, choices: List[str], descriptions: Optional[List[str]] = None
    ) -> str:
        """Get user choice from a list of options."""
        print(f"\n{prompt}")

        for i, choice in enumerate(choices, 1):
            if descriptions and i - 1 < len(descriptions):
                print(f"  {i}. {choice} - {descriptions[i-1]}")
            else:
                print(f"  {i}. {choice}")

        while True:
            try:
                response = input(f"\nEnter choice (1-{len(choices)}): ").strip()
                choice_num = int(response)

                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    print(f"❌ Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("❌ Please enter a valid number")

    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no input from user."""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes", "true", "1"]

    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            print("❌ Please enter a valid HTTP or HTTPS URL")
            return False

        return True

    def select_calendar_service(self) -> str:
        """Let user select calendar service template."""
        self.print_section("Calendar Service Selection")

        print("Select your calendar service for quick setup:")

        service_keys = list(self.SERVICE_TEMPLATES.keys())
        service_names = [self.SERVICE_TEMPLATES[key].name for key in service_keys]
        service_descriptions = [self.SERVICE_TEMPLATES[key].description for key in service_keys]

        selected_name = self.get_choice(
            "Choose your calendar service:", service_names, service_descriptions
        )

        # Find the corresponding key
        for key, template in self.SERVICE_TEMPLATES.items():
            if template.name == selected_name:
                return key

        return "custom"  # fallback

    def configure_ics_url(self, service_key: str) -> Dict[str, Any]:
        """Configure ICS URL with service-specific guidance."""
        template = self.SERVICE_TEMPLATES[service_key]

        self.print_section(f"{template.name} Configuration")

        # Show instructions
        if template.instructions.strip():
            print("📖 Instructions:")
            print(template.instructions.strip())
            print()

        # Get URL
        url = self.get_input(
            "Enter your ICS calendar URL", required=True, validate_func=self.validate_url
        )

        # Validate URL pattern for known services
        if service_key != "custom" and not re.search(template.url_pattern, url):
            print(f"⚠️  Warning: URL doesn't match expected pattern for {template.name}")
            print(f"Expected pattern: {template.url_pattern}")

            if not self.get_yes_no("Do you want to continue with this URL anyway?"):
                return self.configure_ics_url(service_key)

        return {"url": url, "recommended_auth": template.auth_type}

    def configure_authentication(self, recommended_auth: str = "none") -> Dict[str, Any]:
        """Configure authentication settings."""
        self.print_section("Authentication Configuration")

        print("Choose authentication method for your calendar:")

        auth_types = ["none", "basic", "bearer"]
        auth_descriptions = [
            "No authentication (public calendar)",
            "Basic authentication (username/password)",
            "Bearer token authentication",
        ]

        # If we have a recommendation, show it
        if recommended_auth != "none":
            print(f"💡 Recommended for your service: {recommended_auth}")

        auth_type = self.get_choice("Select authentication method:", auth_types, auth_descriptions)

        auth_config: Dict[str, Any] = {"auth_type": auth_type}

        if auth_type == "basic":
            print("\n📝 Basic Authentication Setup:")
            username = self.get_input("Username", required=True)
            password = self.get_input("Password", required=True)

            # Log authentication setup with credential masking
            security_logger = SecurityEventLogger()
            security_logger.log_authentication_success(
                user_id=mask_credentials(username),
                details={"event_type": "credential_setup", "auth_method": "basic"},
            )

            auth_config["username"] = username
            auth_config["password"] = password

        elif auth_type == "bearer":
            print("\n📝 Bearer Token Setup:")
            token = self.get_input("Bearer Token", required=True)

            # Log token setup with credential masking
            security_logger = SecurityEventLogger()
            security_logger.log_authentication_success(
                user_id="wizard_user",
                details={"event_type": "token_setup", "auth_method": "bearer"},
            )

            auth_config["token"] = token

        return auth_config

    def configure_advanced_settings(self) -> Dict[str, Any]:
        """Configure advanced application settings."""
        self.print_section("Advanced Settings")

        print("Configure advanced settings (or press Enter for defaults):")

        settings: Dict[str, Any] = {}

        # Refresh interval
        refresh_str = self.get_input("Refresh interval in seconds", default="300", required=False)
        if refresh_str:
            try:
                settings["refresh_interval"] = int(refresh_str)
            except ValueError:
                print("⚠️  Invalid number, using default (300)")
                settings["refresh_interval"] = 300

        # Cache TTL
        cache_str = self.get_input("Cache TTL in seconds", default="3600", required=False)
        if cache_str:
            try:
                settings["cache_ttl"] = int(cache_str)
            except ValueError:
                print("⚠️  Invalid number, using default (3600)")
                settings["cache_ttl"] = 3600

        # SSL verification
        settings["verify_ssl"] = self.get_yes_no(
            "Verify SSL certificates (recommended)", default=True
        )

        # Logging level
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        log_level_str = self.get_choice("Choose default logging level:", log_levels)
        settings["log_level"] = log_level_str

        return settings

    async def test_configuration(self, ics_config: Dict[str, Any]) -> bool:
        """Test the ICS configuration."""
        self.print_section("Configuration Testing")

        print("🧪 Testing ICS calendar connection...")

        try:
            # Create ICS source from config
            from .ics.models import AuthType

            auth_type_str = ics_config.get("auth_type", "none")
            if auth_type_str == "basic":
                auth_type = AuthType.BASIC
            elif auth_type_str == "bearer":
                auth_type = AuthType.BEARER
            else:
                auth_type = AuthType.NONE

            auth = ICSAuth(
                type=auth_type,
                username=ics_config.get("username"),
                password=ics_config.get("password"),
                bearer_token=ics_config.get("token"),
            )

            source = ICSSource(
                name="Setup Wizard Test",
                url=ics_config["url"],
                auth=auth,
                validate_ssl=ics_config.get("verify_ssl", True),
                timeout=30,
            )

            # Test connection
            async with ICSFetcher(CalendarBotSettings()) as fetcher:
                print("  → Testing connection...")
                if await fetcher.test_connection(source):
                    print("  ✅ Connection successful")

                    print("  → Fetching sample data...")
                    response = await fetcher.fetch_ics(source)

                    if response.success:
                        content_size = len(response.content) if response.content else 0
                        print(f"  ✅ Successfully fetched ICS data ({content_size} bytes)")

                        # Basic content validation
                        if response.content and "BEGIN:VCALENDAR" in response.content:
                            print("  ✅ ICS format appears valid")
                        else:
                            print("  ⚠️  Warning: Content may not be valid ICS format")

                        return True
                    else:
                        print(f"  ❌ Failed to fetch ICS data: {response.error_message}")
                        return False
                else:
                    print("  ❌ Connection test failed")
                    return False

        except ICSError as e:
            print(f"  ❌ ICS Error: {e.message}")
            return False
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            return False

    def generate_config_content(
        self, ics_config: Dict[str, Any], advanced_settings: Dict[str, Any]
    ) -> str:
        """Generate YAML configuration content."""
        config = {
            # Header comment
            "_comment": f'Calendar Bot Configuration - Generated by setup wizard on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            # ICS Configuration
            "ics": {
                "url": ics_config["url"],
                "auth_type": ics_config.get("auth_type", "none"),
                "verify_ssl": advanced_settings.get("verify_ssl", True),
                "timeout": 30,
            },
            # Application Settings
            "app_name": "CalendarBot",
            "refresh_interval": advanced_settings.get("refresh_interval", 300),
            "cache_ttl": advanced_settings.get("cache_ttl", 3600),
            # Logging Configuration
            "log_level": advanced_settings.get("log_level", "WARNING"),
            "log_file": None,
            # Display Settings
            "display_enabled": True,
            "display_type": "console",
            # Web Interface Settings
            "web": {
                "enabled": False,
                "port": 8080,
                "host": "0.0.0.0",  # nosec B104
                "theme": "4x8",
                "auto_refresh": 60,
            },
            # Raspberry Pi E-ink Settings
            "rpi": {
                "enabled": False,
                "display_width": 480,
                "display_height": 800,
                "refresh_mode": "partial",
                "auto_theme": True,
            },
        }

        # Add authentication if needed
        if ics_config.get("auth_type") == "basic":
            config["ics"]["username"] = ics_config.get("username")
            config["ics"]["password"] = ics_config.get("password")
        elif ics_config.get("auth_type") == "bearer":
            config["ics"]["token"] = ics_config.get("token")

        # Convert to YAML
        yaml_content = "# Calendar Bot Configuration\n"
        yaml_content += (
            f"# Generated by setup wizard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        # Remove the comment field before dumping
        config.pop("_comment", None)

        yaml_content += yaml.dump(config, default_flow_style=False, indent=2)

        return yaml_content

    def save_configuration(self, config_content: str) -> Optional[Path]:
        """Save configuration to file."""
        self.print_section("Saving Configuration")

        # Determine config file location
        config_options = [
            ("Project directory", Path(__file__).parent.parent / "config" / "config.yaml"),
            ("User home directory", Path.home() / ".config" / "calendarbot" / "config.yaml"),
        ]

        print("Where would you like to save the configuration?")

        location_names = [option[0] for option in config_options]
        location_paths = [option[1] for option in config_options]

        choice = self.get_choice(
            "Select configuration location:", location_names, [str(path) for path in location_paths]
        )

        # Find selected path
        config_path = None
        for name, path in config_options:
            if name == choice:
                config_path = path
                break

        if not config_path:
            config_path = location_paths[0]  # fallback

        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists
        if config_path.exists():
            if not self.get_yes_no(
                f"Configuration file already exists at {config_path}. Overwrite?"
            ):
                print("❌ Configuration not saved. Exiting wizard.")
                return None

        # Save configuration
        try:
            with open(config_path, "w") as f:
                f.write(config_content)

            print(f"✅ Configuration saved to: {config_path}")
            return config_path

        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return None

    def show_completion_message(self, config_path: Optional[Path]) -> None:
        """Show completion message with next steps."""
        self.print_header("Setup Complete! 🎉")

        if config_path:
            print(f"📁 Configuration file: {config_path}")
            print("\n🚀 Next Steps:")
            print("   calendarbot --test-mode    # Test your configuration")
            print("   calendarbot --interactive  # Interactive calendar view")
            print("   calendarbot --web          # Web interface")
            print("   calendarbot --rpi --web    # Raspberry Pi e-ink mode")

            print("\n📝 Customization:")
            print(f"   Edit {config_path} for advanced settings")
            print("   See config/config.yaml.example for all options")
        else:
            print("⚠️ Configuration file could not be saved")

        print("\n📖 Documentation:")
        print("   README.md     - General usage")
        print("   docs/INSTALL.md    - Installation guide")
        print("   docs/USAGE.md      - Detailed usage examples")

        print("\n" + "=" * 60)

    async def run(self) -> bool:
        """Run the complete setup wizard."""
        try:
            self.print_header("Calendar Bot Configuration Wizard")

            print("This wizard will help you configure Calendar Bot step by step.")
            print("You can always edit the configuration file later for advanced settings.\n")

            if not self.get_yes_no("Ready to start configuration?", default=True):
                print("Setup cancelled.")
                return False

            # Step 1: Select calendar service
            service_key = self.select_calendar_service()

            # Step 2: Configure ICS URL
            ics_result = self.configure_ics_url(service_key)

            # Step 3: Configure authentication
            auth_config = self.configure_authentication(ics_result["recommended_auth"])
            ics_config = {**ics_result, **auth_config}

            # Step 4: Test configuration
            if self.get_yes_no("Test configuration before saving?", default=True):
                test_success = await self.test_configuration(ics_config)

                if not test_success:
                    if not self.get_yes_no("Configuration test failed. Continue anyway?"):
                        print("Setup cancelled.")
                        return False

            # Step 5: Configure advanced settings
            if self.get_yes_no("Configure advanced settings?", default=False):
                advanced_settings = self.configure_advanced_settings()
            else:
                advanced_settings = {}

            # Step 6: Generate and save configuration
            config_content = self.generate_config_content(ics_config, advanced_settings)
            config_path = self.save_configuration(config_content)

            if not config_path:
                return False

            # Step 7: Show completion
            self.show_completion_message(config_path)

            return True

        except KeyboardInterrupt:
            print("\n\nSetup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            logger.error(f"Setup wizard error: {e}")
            return False


async def run_setup_wizard() -> bool:
    """Run the interactive setup wizard."""
    wizard = SetupWizard()
    return await wizard.run()


def run_simple_wizard() -> bool:
    """Run a simplified synchronous wizard for basic setups."""
    """This is for backwards compatibility and command-line usage."""

    try:
        print("\n" + "=" * 60)
        print("📅 Calendar Bot Quick Setup")
        print("=" * 60)
        print("This is a simplified setup wizard.")
        print(
            "For full setup options, use: python -c 'import asyncio; from calendarbot.setup_wizard import run_setup_wizard; asyncio.run(run_setup_wizard())'"
        )
        print()

        # Create config directory
        config_dir = Path.home() / ".config" / "calendarbot"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        # Check if config already exists
        if config_file.exists():
            print(f"⚠️  Configuration file already exists: {config_file}")
            response = input("Do you want to overwrite it? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                print("Setup cancelled.")
                return False

        # Get ICS URL
        print("🔗 Calendar URL Configuration:")
        print("Enter your ICS/iCal calendar URL.")
        print("Examples:")
        print("- Outlook: https://outlook.live.com/owa/calendar/.../calendar.ics")
        print("- Google: https://calendar.google.com/calendar/ical/.../basic.ics")
        print("- iCloud: https://p01-caldav.icloud.com/published/...")
        print()

        ics_url = input("Enter your ICS calendar URL: ").strip()
        if not ics_url:
            print("❌ ICS URL is required. Setup cancelled.")
            return False

        # Basic validation
        if not (ics_url.startswith("http://") or ics_url.startswith("https://")):
            print("⚠️  Warning: URL should start with http:// or https://")

        # Create basic config (same as original in main.py)
        config_content = f"""# Calendar Bot Configuration
# Generated by simple wizard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# ICS Calendar Configuration
ics:
  url: "{ics_url}"
  auth_type: "none"
  verify_ssl: true
  timeout: 30

# Application Settings
app_name: "CalendarBot"
refresh_interval: 300       # 5 minutes
cache_ttl: 3600            # 1 hour

# Logging Configuration
log_level: "WARNING"
log_file: null

# Display Settings
display_enabled: true
display_type: "console"

# Web Interface Settings (for --web mode)
web:
  enabled: false
  port: 8080
  host: "0.0.0.0"
  theme: "4x8"
  auto_refresh: 60

# Raspberry Pi E-ink Settings (for --rpi mode)
rpi:
  enabled: false
  display_width: 480
  display_height: 800
  refresh_mode: "partial"
  auto_theme: true
"""

        # Write config file
        with open(config_file, "w") as f:
            f.write(config_content)

        print(f"\n✅ Configuration created successfully!")
        print(f"📁 Config file: {config_file}")
        print("\n🎉 You're all set! Try running:")
        print("   calendarbot --test-mode    # Test your configuration")
        print("   calendarbot --interactive  # Interactive calendar view")
        print("   calendarbot --web          # Web interface")
        print("\n📝 To customize further, edit the config file or see config.yaml.example")
        print("=" * 60)

        return True

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return False
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False
