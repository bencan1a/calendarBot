from calendarbot.cli.config import apply_cli_overrides
from calendarbot.cli.parser import create_parser
from calendarbot.config.settings import CalendarBotSettings


def test_cli_pi_flag_applies_overrides() -> None:
    """When --pi-optimized is passed on the CLI, the Pi defaults are applied."""
    parser = create_parser()
    args = parser.parse_args(["--pi-optimized"])
    settings = CalendarBotSettings()

    # Sanity: ensure defaults are different from Pi-optimized values
    assert settings.optimization.small_device is False
    assert settings.optimization.prebuild_asset_cache is True
    assert settings.optimization.max_events_processed is None
    assert settings.monitoring.enabled is True

    apply_cli_overrides(settings, args)

    assert settings.optimization.small_device is True
    assert settings.optimization.prebuild_asset_cache is False
    assert settings.optimization.max_events_processed == 10
    assert settings.monitoring.enabled is False
    assert settings.epaper.enabled is False


def test_env_var_pi_optimized_applies_overrides(monkeypatch) -> None:
    """When CALENDARBOT_PI_OPTIMIZED=1 is set, the same overrides are applied."""
    monkeypatch.setenv("CALENDARBOT_PI_OPTIMIZED", "1")
    parser = create_parser()
    args = parser.parse_args([])  # no CLI flag

    settings = CalendarBotSettings()
    apply_cli_overrides(settings, args)

    assert settings.optimization.small_device is True
    assert settings.optimization.prebuild_asset_cache is False
    assert settings.optimization.max_events_processed == 10
    assert settings.monitoring.enabled is False
    assert settings.epaper.enabled is False


def test_no_flag_defaults_unchanged(monkeypatch) -> None:
    """Without the flag or env var, optimization and monitoring defaults remain unchanged."""
    monkeypatch.delenv("CALENDARBOT_PI_OPTIMIZED", raising=False)
    parser = create_parser()
    args = parser.parse_args([])

    settings = CalendarBotSettings()

    # Defaults before applying CLI overrides
    assert settings.optimization.small_device is False
    assert settings.optimization.prebuild_asset_cache is True
    assert settings.optimization.max_events_processed is None
    assert settings.monitoring.enabled is True

    apply_cli_overrides(settings, args)

    # After applying CLI overrides with no pi flag/env, these should remain defaults
    assert settings.optimization.small_device is False
    assert settings.optimization.prebuild_asset_cache is True
    assert settings.optimization.max_events_processed is None
    assert settings.monitoring.enabled is True
