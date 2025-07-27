"""Image processing utilities for e-Paper displays."""

import logging
from typing import Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.ImageFont import ImageFont as BuiltinFont

logger = logging.getLogger(__name__)


def convert_image_to_epaper_format(
    image: Image.Image, threshold: int = 128, red_threshold: Optional[int] = None
) -> bytes:
    """Convert PIL Image to e-Paper display format.

    Args:
        image: PIL Image to convert
        threshold: Threshold for black/white conversion (0-255)
        red_threshold: Threshold for red conversion (0-255), None to disable red

    Returns:
        Bytes in e-Paper display format (black and red buffers)
    """
    # Ensure image is in RGB mode
    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size

    # Calculate buffer size
    buffer_size = width * height // 8
    black_buffer = bytearray(buffer_size)
    red_buffer = bytearray(buffer_size)

    # Fill buffers with white (0xFF)
    for i in range(buffer_size):
        black_buffer[i] = 0xFF
        red_buffer[i] = 0xFF

    # Process image pixel by pixel
    for y in range(height):
        for x in range(width):
            # Get pixel color
            pixel = image.getpixel((x, y))
            if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            else:
                # Handle grayscale or other formats
                val = int(pixel) if isinstance(pixel, (int, float)) else 0
                r = g = b = val

            # Calculate pixel position in buffer
            index = (y * width + x) // 8
            bit = 7 - (x % 8)

            # Convert to black/white/red
            if (
                red_threshold is not None
                and r > red_threshold
                and g < red_threshold
                and b < red_threshold
            ):
                # Red pixel
                red_buffer[index] &= ~(1 << bit)
            elif r < threshold and g < threshold and b < threshold:
                # Black pixel
                black_buffer[index] &= ~(1 << bit)

    # Combine buffers
    return bytes(black_buffer) + bytes(red_buffer)


def resize_image_for_epaper(
    image: Image.Image,
    width: int,
    height: int,
    maintain_aspect_ratio: bool = True,
    bg_color: Union[str, Tuple[int, int, int]] = "white",
) -> Image.Image:
    """Resize image for e-Paper display.

    Args:
        image: PIL Image to resize
        width: Target width
        height: Target height
        maintain_aspect_ratio: Whether to maintain aspect ratio
        bg_color: Background color for padding

    Returns:
        Resized PIL Image
    """
    if maintain_aspect_ratio:
        # Calculate new size while maintaining aspect ratio
        img_width, img_height = image.size
        ratio = min(width / img_width, height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create new image with target size and paste resized image
        new_image = Image.new("RGB", (width, height), bg_color)
        paste_x = (width - new_width) // 2
        paste_y = (height - new_height) // 2
        new_image.paste(resized_image, (paste_x, paste_y))

        return new_image
    else:
        # Resize image to target size without maintaining aspect ratio
        return image.resize((width, height), Image.Resampling.LANCZOS)


def render_text_to_image(
    text: str,
    width: int,
    height: int,
    font_path: Optional[str] = None,
    font_size: int = 20,
    text_color: Tuple[int, int, int] = (0, 0, 0),
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    align: str = "center",
) -> Image.Image:
    """Render text to a PIL Image.

    Args:
        text: Text to render
        width: Image width in pixels
        height: Image height in pixels
        font_path: Optional path to font file
        font_size: Font size in points
        text_color: Text color as RGB tuple
        bg_color: Background color as RGB tuple
        align: Text alignment ("left", "center", "right")

    Returns:
        PIL Image with rendered text
    """
    # Create image
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # Load font
    font: Union[FreeTypeFont, BuiltinFont]
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except Exception as e:
        logger.warning(f"Failed to load font: {e}, using default font")
        font = ImageFont.load_default()

    # Calculate text position (compatible with newer PIL versions)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = int(bbox[2] - bbox[0])
    text_height = int(bbox[3] - bbox[1])

    if align == "left":
        x = 10
    elif align == "right":
        x = width - text_width - 10
    else:  # center
        x = (width - text_width) // 2

    y = (height - text_height) // 2

    # Draw text
    draw.text((x, y), text, font=font, fill=text_color)

    return image


def create_test_pattern(width: int, height: int, has_red: bool = True) -> bytes:
    """Create a test pattern for e-Paper display.

    Args:
        width: Display width
        height: Display height
        has_red: Whether the display supports red color

    Returns:
        Bytes in e-Paper display format
    """
    # Create image
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Draw black border
    draw.rectangle(((0, 0), (width - 1, height - 1)), outline="black")

    # Draw horizontal and vertical lines
    for i in range(0, width, 50):
        draw.line([(i, 0), (i, height - 1)], fill="black")
    for i in range(0, height, 50):
        draw.line([(0, i), (width - 1, i)], fill="black")

    # Draw diagonal lines
    draw.line([(0, 0), (width - 1, height - 1)], fill="black")
    draw.line([(0, height - 1), (width - 1, 0)], fill="black")

    # Draw red elements if supported
    if has_red:
        # Draw red rectangle in the center
        center_x = width // 2
        center_y = height // 2
        rect_size = min(width, height) // 4
        draw.rectangle(
            (
                (center_x - rect_size, center_y - rect_size),
                (center_x + rect_size, center_y + rect_size),
            ),
            outline="red",
        )

        # Draw red circles in corners
        corner_size = min(width, height) // 8
        draw.ellipse([(10, 10), (10 + corner_size, 10 + corner_size)], outline="red")
        draw.ellipse(
            [(width - 10 - corner_size, 10), (width - 10, 10 + corner_size)], outline="red"
        )
        draw.ellipse(
            [(10, height - 10 - corner_size), (10 + corner_size, height - 10)], outline="red"
        )
        draw.ellipse(
            [(width - 10 - corner_size, height - 10 - corner_size), (width - 10, height - 10)],
            outline="red",
        )

    # Convert to e-Paper format
    return convert_image_to_epaper_format(image, red_threshold=200 if has_red else None)
