"""Display capabilities model for e-Paper displays."""

from typing import Any


class DisplayCapabilities:
    """Represents the capabilities of a display device."""

    def __init__(
        self,
        width: int,
        height: int,
        colors: int,
        supports_partial_update: bool,
        supports_grayscale: bool,
        supports_red: bool,
    ) -> None:
        """Initialize display capabilities.

        Args:
            width: Display width in pixels
            height: Display height in pixels
            colors: Number of colors supported
            supports_partial_update: Whether partial updates are supported
            supports_grayscale: Whether grayscale is supported
            supports_red: Whether red color is supported
        """
        self.width = width
        self.height = height
        self.colors = colors
        self.supports_partial_update = supports_partial_update
        self.supports_grayscale = supports_grayscale
        self.supports_red = supports_red

    def __repr__(self) -> str:
        """Return string representation of display capabilities.

        Returns:
            String representation
        """
        return (
            f"DisplayCapabilities(width={self.width}, height={self.height}, "
            f"colors={self.colors}, partial_update={self.supports_partial_update}, "
            f"grayscale={self.supports_grayscale}, red={self.supports_red})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert capabilities to dictionary.

        Returns:
            Dictionary representation of capabilities
        """
        return {
            "width": self.width,
            "height": self.height,
            "colors": self.colors,
            "supports_partial_update": self.supports_partial_update,
            "supports_grayscale": self.supports_grayscale,
            "supports_red": self.supports_red,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DisplayCapabilities":
        """Create DisplayCapabilities from dictionary.

        Args:
            data: Dictionary containing capability data

        Returns:
            DisplayCapabilities instance

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "width",
            "height",
            "colors",
            "supports_partial_update",
            "supports_grayscale",
            "supports_red",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return cls(
            width=data["width"],
            height=data["height"],
            colors=data["colors"],
            supports_partial_update=data["supports_partial_update"],
            supports_grayscale=data["supports_grayscale"],
            supports_red=data["supports_red"],
        )
