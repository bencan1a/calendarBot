"""Tests for Region class."""

from calendarbot.display.epaper.region import Region


class TestRegion:
    """Test suite for Region class."""

    def test_init_when_valid_parameters_then_creates_instance(self) -> None:
        """Test initialization with valid parameters."""
        # Arrange & Act
        region = Region(x=10, y=20, width=100, height=200)

        # Assert
        assert region.x == 10
        assert region.y == 20
        assert region.width == 100
        assert region.height == 200

    def test_init_when_zero_values_then_creates_instance(self) -> None:
        """Test initialization with zero values."""
        # Arrange & Act
        region = Region(x=0, y=0, width=0, height=0)

        # Assert
        assert region.x == 0
        assert region.y == 0
        assert region.width == 0
        assert region.height == 0

    def test_init_when_negative_values_then_creates_instance(self) -> None:
        """Test initialization with negative values."""
        # Arrange & Act
        region = Region(x=-10, y=-20, width=100, height=200)

        # Assert
        assert region.x == -10
        assert region.y == -20
        assert region.width == 100
        assert region.height == 200

    def test_repr_when_called_then_returns_string_representation(self) -> None:
        """Test string representation of Region."""
        # Arrange
        region = Region(x=10, y=20, width=100, height=200)

        # Act
        result = repr(region)

        # Assert
        assert "Region" in result
        assert "x=10" in result
        assert "y=20" in result
        assert "width=100" in result
        assert "height=200" in result

    def test_contains_point_when_point_inside_then_returns_true(self) -> None:
        """Test contains_point with point inside region."""
        # Arrange
        region = Region(x=10, y=20, width=100, height=200)

        # Act & Assert
        assert region.contains_point(50, 50) is True
        assert region.contains_point(10, 20) is True  # Top-left corner
        assert region.contains_point(109, 219) is True  # Bottom-right corner (exclusive)

    def test_contains_point_when_point_outside_then_returns_false(self) -> None:
        """Test contains_point with point outside region."""
        # Arrange
        region = Region(x=10, y=20, width=100, height=200)

        # Act & Assert
        assert region.contains_point(5, 50) is False  # Left of region
        assert region.contains_point(150, 50) is False  # Right of region
        assert region.contains_point(50, 10) is False  # Above region
        assert region.contains_point(50, 250) is False  # Below region
        assert region.contains_point(110, 220) is False  # Bottom-right corner (inclusive)

    def test_contains_point_when_point_on_edge_then_returns_expected(self) -> None:
        """Test contains_point with point on edge of region."""
        # Arrange
        region = Region(x=10, y=20, width=100, height=200)

        # Act & Assert - Points on left and top edges are included
        assert region.contains_point(10, 50) is True  # Left edge
        assert region.contains_point(50, 20) is True  # Top edge

        # Act & Assert - Points on right and bottom edges are excluded
        assert region.contains_point(110, 50) is False  # Right edge
        assert region.contains_point(50, 220) is False  # Bottom edge

    def test_contains_point_when_zero_width_height_then_returns_false(self) -> None:
        """Test contains_point with zero width/height region."""
        # Arrange
        region = Region(x=10, y=20, width=0, height=0)

        # Act & Assert
        assert region.contains_point(10, 20) is False  # Point at origin
        assert region.contains_point(11, 21) is False  # Point near origin

    def test_overlaps_when_regions_overlap_then_returns_true(self) -> None:
        """Test overlaps with overlapping regions."""
        # Arrange
        region1 = Region(x=10, y=20, width=100, height=200)

        # Act & Assert - Different overlap scenarios
        # Partial overlap
        region2 = Region(x=50, y=50, width=100, height=200)
        assert region1.overlaps(region2) is True
        assert region2.overlaps(region1) is True  # Symmetry check

        # One region contains the other
        region3 = Region(x=20, y=30, width=50, height=50)
        assert region1.overlaps(region3) is True
        assert region3.overlaps(region1) is True  # Symmetry check

        # Edge overlap
        region4 = Region(x=110, y=20, width=100, height=200)
        assert region1.overlaps(region4) is False  # Right edge
        assert region4.overlaps(region1) is False  # Symmetry check

    def test_overlaps_when_regions_do_not_overlap_then_returns_false(self) -> None:
        """Test overlaps with non-overlapping regions."""
        # Arrange
        region1 = Region(x=10, y=20, width=100, height=200)

        # Act & Assert - Different non-overlap scenarios
        # Completely separate
        region2 = Region(x=200, y=300, width=100, height=200)
        assert region1.overlaps(region2) is False
        assert region2.overlaps(region1) is False  # Symmetry check

        # Adjacent but not overlapping (right)
        region3 = Region(x=110, y=20, width=100, height=200)
        assert region1.overlaps(region3) is False
        assert region3.overlaps(region1) is False  # Symmetry check

        # Adjacent but not overlapping (bottom)
        region4 = Region(x=10, y=220, width=100, height=200)
        assert region1.overlaps(region4) is False
        assert region4.overlaps(region1) is False  # Symmetry check

    def test_overlaps_when_zero_width_height_then_returns_false(self) -> None:
        """Test overlaps with zero width/height regions."""
        # Arrange
        region1 = Region(x=10, y=20, width=0, height=0)
        region2 = Region(x=10, y=20, width=100, height=200)
        region3 = Region(x=10, y=20, width=0, height=0)

        # Act & Assert
        assert region1.overlaps(region2) is False
        assert region2.overlaps(region1) is False  # Symmetry check
        assert region1.overlaps(region3) is False  # Two zero-sized regions

    def test_get_coordinates_when_called_then_returns_tuple(self) -> None:
        """Test get_coordinates returns correct tuple."""
        # Arrange
        region = Region(x=10, y=20, width=100, height=200)

        # Act
        result = region.get_coordinates()

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert result == (10, 20, 100, 200)

    def test_get_area_when_called_then_returns_correct_area(self) -> None:
        """Test get_area returns correct area."""
        # Arrange & Act & Assert
        region1 = Region(x=10, y=20, width=100, height=200)
        assert region1.get_area() == 20000

        region2 = Region(x=0, y=0, width=5, height=10)
        assert region2.get_area() == 50

        region3 = Region(x=-10, y=-20, width=100, height=200)
        assert region3.get_area() == 20000  # Negative coordinates don't affect area

        region4 = Region(x=10, y=20, width=0, height=200)
        assert region4.get_area() == 0  # Zero width means zero area

        region5 = Region(x=10, y=20, width=100, height=0)
        assert region5.get_area() == 0  # Zero height means zero area
