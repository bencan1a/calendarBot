"""Utility functions for Waveshare e-Paper displays."""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def delay_ms(delaytime: int) -> None:
    """Delay for specified milliseconds.

    Args:
        delaytime: Delay time in milliseconds
    """
    time.sleep(delaytime / 1000.0)


def bytes_to_list(data: bytes) -> list[int]:
    """Convert bytes to list of integers.

    Args:
        data: Bytes to convert

    Returns:
        List of integers
    """
    return list(data)


def list_to_bytes(data: list[int]) -> bytes:
    """Convert list of integers to bytes.

    Args:
        data: List of integers to convert

    Returns:
        Bytes
    """
    return bytes(data)


def validate_buffer_size(buffer: bytes, expected_size: int) -> bool:
    """Validate buffer size.

    Args:
        buffer: Buffer to validate
        expected_size: Expected buffer size

    Returns:
        True if buffer size is valid, False otherwise
    """
    if len(buffer) != expected_size:
        logger.error(f"Invalid buffer size: {len(buffer)}, expected {expected_size}")
        return False
    return True


def split_color_buffer(buffer: bytes, buffer_size: int) -> Optional[tuple[bytes, bytes]]:
    """Split buffer into black and red parts.

    Args:
        buffer: Buffer containing both black and red data
        buffer_size: Size of each color buffer

    Returns:
        Tuple of (black_buffer, red_buffer) or None if buffer size is invalid
    """
    if len(buffer) != buffer_size * 2:
        logger.error(f"Invalid buffer size: {len(buffer)}, expected {buffer_size * 2}")
        return None

    black_buffer = buffer[:buffer_size]
    red_buffer = buffer[buffer_size:]

    return (black_buffer, red_buffer)


def extract_region_buffer(
    buffer: bytes,
    display_width: int,
    region_x: int,
    region_y: int,
    region_width: int,
    region_height: int,
) -> Optional[bytes]:
    """Extract a region buffer from the full buffer.

    Args:
        buffer: Full display buffer
        display_width: Width of the display in pixels
        region_x: X-coordinate of region
        region_y: Y-coordinate of region
        region_width: Width of region in pixels
        region_height: Height of region in pixels

    Returns:
        Buffer for the specified region or None if region is invalid
    """
    try:
        # Calculate buffer size for region
        region_buffer_size = region_width * region_height // 8
        region_buffer = bytearray(region_buffer_size)

        # Extract region data from full buffer
        display_width_bytes = display_width // 8

        for y in range(region_height):
            for x in range(region_width // 8):
                src_x = region_x // 8 + x
                src_y = region_y + y
                src_idx = src_y * display_width_bytes + src_x
                dst_idx = y * (region_width // 8) + x

                if src_idx < len(buffer) and dst_idx < len(region_buffer):
                    region_buffer[dst_idx] = buffer[src_idx]

        return bytes(region_buffer)
    except Exception as e:
        logger.error(f"Failed to extract region buffer: {e}")
        return None
