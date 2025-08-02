"""Region model for e-Paper displays."""




class Region:
    """Represents a rectangular region on the display."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        """Initialize a region.

        Args:
            x: X-coordinate of top-left corner
            y: Y-coordinate of top-left corner
            width: Width of region in pixels
            height: Height of region in pixels
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        """Return string representation of region.

        Returns:
            String representation
        """
        return f"Region(x={self.x}, y={self.y}, width={self.width}, height={self.height})"

    def contains_point(self, x: int, y: int) -> bool:
        """Check if region contains a point.

        Args:
            x: X-coordinate
            y: Y-coordinate

        Returns:
            True if point is in region, False otherwise
        """
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def overlaps(self, other: "Region") -> bool:
        """Check if region overlaps with another region.

        Args:
            other: Other region

        Returns:
            True if regions overlap, False otherwise
        """
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )

    def get_coordinates(self) -> tuple[int, int, int, int]:
        """Get coordinates of the region.

        Returns:
            Tuple of (x, y, width, height)
        """
        return (self.x, self.y, self.width, self.height)

    def get_area(self) -> int:
        """Get area of the region in pixels.

        Returns:
            Area in pixels
        """
        return self.width * self.height
