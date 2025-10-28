"""Unit tests for optimization timeout configuration."""

from calendarbot.config.settings import OptimizationSettings


class TestOptimizationTimeoutSetting:
    """Test the new bridge_timeout_seconds configuration."""

    def test_bridge_timeout_default_value(self):
        """Test that bridge_timeout_seconds has correct default value."""
        settings = OptimizationSettings()
        assert settings.bridge_timeout_seconds == 10.0

    def test_bridge_timeout_custom_value(self):
        """Test that bridge_timeout_seconds can be configured."""
        settings = OptimizationSettings(bridge_timeout_seconds=20.0)
        assert settings.bridge_timeout_seconds == 20.0

    def test_bridge_timeout_validation(self):
        """Test that bridge_timeout_seconds accepts reasonable values."""
        # Test various valid values
        valid_values = [1.0, 5.0, 10.0, 30.0, 60.0]

        for value in valid_values:
            settings = OptimizationSettings(bridge_timeout_seconds=value)
            assert settings.bridge_timeout_seconds == value

    def test_bridge_timeout_field_exists(self):
        """Test that bridge_timeout_seconds field exists and has proper metadata."""
        settings = OptimizationSettings()

        # Check field exists
        assert hasattr(settings, "bridge_timeout_seconds")

        # Check field type
        assert isinstance(settings.bridge_timeout_seconds, float)

        # Check field is in model fields
        assert "bridge_timeout_seconds" in OptimizationSettings.__fields__
