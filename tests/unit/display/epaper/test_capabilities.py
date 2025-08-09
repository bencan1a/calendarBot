"""Tests for DisplayCapabilities class."""

from typing import Any, Dict

import pytest

from calendarbot.display.epaper.capabilities import DisplayCapabilities


class TestDisplayCapabilities:
    """Test suite for DisplayCapabilities class."""

    def test_init_when_valid_parameters_then_creates_instance(self) -> None:
        """Test initialization with valid parameters."""
        # Arrange & Act
        capabilities = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

        # Assert
        assert capabilities.width == 800
        assert capabilities.height == 600
        assert capabilities.colors == 2
        assert capabilities.supports_partial_update is True
        assert capabilities.supports_grayscale is False
        assert capabilities.supports_red is False

    def test_init_when_different_parameters_then_creates_instance(self) -> None:
        """Test initialization with different parameter values."""
        # Arrange & Act
        capabilities = DisplayCapabilities(
            width=400,
            height=300,
            colors=3,
            supports_partial_update=False,
            supports_grayscale=True,
            supports_red=True,
        )

        # Assert
        assert capabilities.width == 400
        assert capabilities.height == 300
        assert capabilities.colors == 3
        assert capabilities.supports_partial_update is False
        assert capabilities.supports_grayscale is True
        assert capabilities.supports_red is True

    def test_repr_when_called_then_returns_string_representation(self) -> None:
        """Test string representation of DisplayCapabilities."""
        # Arrange
        capabilities = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

        # Act
        result = repr(capabilities)

        # Assert
        assert "DisplayCapabilities" in result
        assert "width=800" in result
        assert "height=600" in result
        assert "colors=2" in result
        assert "partial_update=True" in result
        assert "grayscale=False" in result
        assert "red=False" in result

    def test_to_dict_when_called_then_returns_dictionary(self) -> None:
        """Test conversion to dictionary."""
        # Arrange
        capabilities = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

        # Act
        result = capabilities.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["width"] == 800
        assert result["height"] == 600
        assert result["colors"] == 2
        assert result["supports_partial_update"] is True
        assert result["supports_grayscale"] is False
        assert result["supports_red"] is False

    def test_from_dict_when_valid_data_then_creates_instance(self) -> None:
        """Test creation from valid dictionary."""
        # Arrange
        data = {
            "width": 800,
            "height": 600,
            "colors": 2,
            "supports_partial_update": True,
            "supports_grayscale": False,
            "supports_red": False,
        }

        # Act
        capabilities = DisplayCapabilities.from_dict(data)

        # Assert
        assert capabilities.width == 800
        assert capabilities.height == 600
        assert capabilities.colors == 2
        assert capabilities.supports_partial_update is True
        assert capabilities.supports_grayscale is False
        assert capabilities.supports_red is False

    def test_from_dict_when_missing_field_then_raises_value_error(self) -> None:
        """Test validation in from_dict for missing fields."""
        # Arrange
        data: Dict[str, Any] = {
            "width": 800,
            "height": 600,
            "colors": 2,
            "supports_partial_update": True,
            # Missing supports_grayscale
            "supports_red": False,
        }

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            DisplayCapabilities.from_dict(data)

        assert "Missing required field" in str(excinfo.value)
        assert "supports_grayscale" in str(excinfo.value)

    def test_from_dict_when_all_fields_missing_then_raises_value_error(self) -> None:
        """Test validation in from_dict for all missing fields."""
        # Arrange
        data: Dict[str, Any] = {}

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            DisplayCapabilities.from_dict(data)

        assert "Missing required field" in str(excinfo.value)

    def test_from_dict_when_extra_fields_then_ignores_extra_fields(self) -> None:
        """Test that from_dict ignores extra fields."""
        # Arrange
        data = {
            "width": 800,
            "height": 600,
            "colors": 2,
            "supports_partial_update": True,
            "supports_grayscale": False,
            "supports_red": False,
            "extra_field": "value",
        }

        # Act
        capabilities = DisplayCapabilities.from_dict(data)

        # Assert
        assert capabilities.width == 800
        assert capabilities.height == 600
        assert capabilities.colors == 2
        assert capabilities.supports_partial_update is True
        assert capabilities.supports_grayscale is False
        assert capabilities.supports_red is False
        assert not hasattr(capabilities, "extra_field")

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Test roundtrip conversion to dictionary and back."""
        # Arrange
        original = DisplayCapabilities(
            width=800,
            height=600,
            colors=2,
            supports_partial_update=True,
            supports_grayscale=False,
            supports_red=False,
        )

        # Act
        data = original.to_dict()
        recreated = DisplayCapabilities.from_dict(data)

        # Assert
        assert recreated.width == original.width
        assert recreated.height == original.height
        assert recreated.colors == original.colors
        assert recreated.supports_partial_update == original.supports_partial_update
        assert recreated.supports_grayscale == original.supports_grayscale
        assert recreated.supports_red == original.supports_red
