"""
E-Paper specialized renderer for What's Next view using shared business logic.

Color Consistency:
- Uses identical grayscale color palette as the web WhatsNext view
- Colors from SharedStylingConstants for consistent visual appearance
- Ensures visual consistency between web and e-Paper rendering
"""

import contextlib
import logging
import os
import tempfile
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont, ImageFont as BuiltinFont

from calendarbot.utils.network import get_local_network_interface

if TYPE_CHECKING:
    # Only import for type checking
    from calendarbot.cache.models import CachedEvent
    from calendarbot.display.renderer_interface import (
        InteractionEvent,
        RendererInterface,
    )
    from calendarbot.display.whats_next_data_model import EventData, WhatsNextViewModel
    from calendarbot.display.whats_next_logic import WhatsNextLogic
else:
    # Runtime imports with fallback
    try:
        from calendarbot.cache.models import CachedEvent
        from calendarbot.display.renderer_interface import (
            InteractionEvent,
            RendererInterface,
        )
        from calendarbot.display.whats_next_data_model import (
            EventData,
            WhatsNextViewModel,
        )
        from calendarbot.display.whats_next_logic import WhatsNextLogic

        CALENDARBOT_AVAILABLE = True
    except ImportError as e:
        # Handle case where calendarbot is not installed
        logging.warning(f"CalendarBot components not available: {e}")
        CALENDARBOT_AVAILABLE = False

        # Create proper type stubs for fallback
        class RendererInterface:
            """Fallback renderer interface."""

            def render(self, view_model: Any) -> Any:
                pass

            def handle_interaction(self, interaction: Any) -> None:
                pass

            def update_display(self, content: Any) -> bool:
                return False

            def render_error(self, error_message: str, cached_events: Any = None) -> Any:
                pass

            def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Any:
                pass

        class WhatsNextLogic:
            """Fallback logic class."""

            def __init__(self, settings: Any = None) -> None:
                self.settings = settings

            def create_view_model(self, events: Any, status_info: Any = None) -> Any:
                return {}

        # Type aliases for fallback
        InteractionEvent = dict[str, Any]
        WhatsNextViewModel = dict[str, Any]
        EventData = dict[str, Any]
        CachedEvent = dict[str, Any]

# Import e-Paper components
# Import shared styling
from ...shared_styling import (
    get_colors_for_renderer,
    get_layout_for_renderer,
    get_typography_for_renderer,
)
from ...whats_next_renderer import WhatsNextRenderer
from ..abstraction import DisplayAbstractionLayer
from ..drivers.mock_eink_driver import EInkDriver
from ..utils.html_to_png import create_converter, is_html2image_available
from ..utils.image_processor import ImageProcessor
from ..utils.performance import PerformanceMetrics

logger = logging.getLogger(__name__)
# E-Paper availability flag for tests and runtime detection
EPAPER_AVAILABLE = True  # Indicates that e-Paper support is compiled in
HTML2IMAGE_AVAILABLE = is_html2image_available()  # Check if html2image is available

# Constants for optimization
MAX_FONT_CACHE_SIZE = 10  # Maximum number of fonts to cache
MAX_TEXT_MEASURE_CACHE_SIZE = 100  # Maximum number of text measurements to cache
BUFFER_POOL_SIZE = 3  # Number of image buffers to keep in the pool
HTML_RENDER_CACHE_SIZE = 5  # Number of HTML renders to cache


class EInkWhatsNextRenderer(RendererInterface):
    """E-Paper specialized renderer for What's Next view.

    Uses shared business logic from WhatsNextLogic but renders to e-Paper format.
    Optimized for e-Paper display characteristics:
    - Monochrome/limited color rendering
    - Diff detection for partial updates
    - Performance optimization for slow refresh rates
    """

    def __init__(self, settings: Any, display: Optional[DisplayAbstractionLayer] = None) -> None:
        """Initialize e-Paper What's Next renderer.

        Args:
            settings: Application settings
            display: Optional display abstraction layer (for dependency injection)
        """
        self.settings = settings
        self.logic = WhatsNextLogic(settings)

        # Initialize display components
        self.display = display or EInkDriver()
        self.capabilities = self.display.get_capabilities()
        self.image_processor = ImageProcessor()

        # Cache for diff detection and partial updates
        self._last_rendered_content: Optional[bytes] = None
        self._last_view_model: Optional[WhatsNextViewModel] = None

        # Initialize performance monitoring
        self.performance = PerformanceMetrics()

        # Font cache with LRU eviction (most recently used fonts stay in cache)
        self._font_cache: OrderedDict[str, Union[FreeTypeFont, BuiltinFont]] = OrderedDict()

        # Text measurement cache to avoid repeated calculations
        self._text_measure_cache: OrderedDict[
            tuple[str, str, int], tuple[float, float, float, float]
        ] = OrderedDict()

        # Image buffer pool for reuse
        self._image_buffer_pool: dict[tuple[str, int, int], list[Image.Image]] = {}

        # HTML render cache for reuse
        self._html_render_cache: OrderedDict[str, tuple[str, datetime]] = OrderedDict()

        # Lazy-loaded fonts - will be populated on first use
        self._fonts: dict[str, Union[FreeTypeFont, BuiltinFont]] = {}

        # Color configuration using SharedStylingConstants
        # Use "L" as default mode for grayscale e-paper displays
        mode = "RGB" if self.capabilities.supports_red else "L"
        self._colors = get_colors_for_renderer("pil", mode=mode)
        self._typography = get_typography_for_renderer("pil")

        # Initialize HTML renderer for generating HTML content
        self.html_renderer = WhatsNextRenderer(settings)

        # Initialize HTML-to-PNG converter if available
        self.html_converter = None
        if HTML2IMAGE_AVAILABLE:
            try:
                # Get layout dimensions
                layout = get_layout_for_renderer("epaper")
                width, height = int(layout["width"]), int(layout["height"])

                # Create temporary directory for output files
                # Create temporary directory for output files
                temp_dir_path = tempfile.mkdtemp(prefix="calendarbot_epaper_")
                self.temp_dir = Path(temp_dir_path)

                # Ensure the directory exists
                self.temp_dir.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created temporary directory: {self.temp_dir}")

                # Initialize converter with e-paper dimensions
                self.html_converter = create_converter(
                    size=(width, height),
                    output_path=str(self.temp_dir),
                )
                logger.info(f"HTML-to-PNG converter initialized with size {width}x{height}")
            except Exception as e:
                logger.warning(f"Failed to initialize HTML-to-PNG converter: {e}")
                self.html_converter = None

        logger.info(
            "EInkWhatsNextRenderer initialized with SharedStylingConstants and optimizations"
        )

    def render(self, view_model: WhatsNextViewModel) -> Image.Image:
        """Render the view model to e-Paper format.

        Args:
            view_model: Data model containing all information needed for rendering

        Returns:
            PIL Image optimized for e-Paper display
        """
        logger.info("EInkWhatsNextRenderer.render called with view model")

        # Start performance monitoring
        self.performance.start_operation("render")

        try:
            # Check if HTML-to-PNG conversion is available and enabled
            if self.html_converter is not None:
                logger.info("Using HTML-to-PNG conversion")
                logger.info(f"HTML converter type: {type(self.html_converter)}")
                logger.info(
                    f"HTML converter output path: {getattr(self.html_converter, 'output_path', 'Not set')}"
                )
                if hasattr(self.html_converter, "hti"):
                    logger.info(
                        f"HTML converter HTI output path: {getattr(self.html_converter.hti, 'output_path', 'Not set')}"
                    )
                image = self._render_using_html_conversion(view_model)
            # Check if we can do partial update (diff detection)
            elif self._can_do_partial_update(view_model):
                logger.info("Using partial update optimization")
                image = self._render_partial_update(view_model)
            else:
                # Full render
                logger.info("Performing full render with PIL")
                image = self._render_full_image(view_model)

            # Cache for next diff detection
            self._last_view_model = view_model
            self._last_rendered_content = image.tobytes()

            return image

        except Exception as e:
            # Log the specific error message to ensure zone-specific errors are captured
            error_msg = str(e)
            logger.exception(f"Error rendering e-Paper view: {error_msg}")
            return self._render_error_image(f"Rendering error: {e}")
        finally:
            # End performance monitoring
            render_time = self.performance.end_operation("render")
            logger.info(f"Render completed in {render_time:.2f}ms")

    def handle_interaction(self, interaction: InteractionEvent) -> None:
        """Handle user interactions on e-Paper display.

        Args:
            interaction: Interaction event to handle
        """
        logger.debug(f"EInkWhatsNextRenderer.handle_interaction: {interaction.event_type}")

        # E-Paper displays typically have limited interaction capabilities
        # Handle basic interactions like button presses
        if interaction.event_type == "refresh":
            logger.info("Manual refresh requested")
            # Trigger a full refresh
            self._last_rendered_content = None
            self._last_view_model = None
        elif interaction.event_type == "button_press":
            button_id = interaction.data.get("button_id")
            logger.info(f"Button press: {button_id}")
            # Handle specific button actions based on button_id

    def update_display(self, content: Image.Image) -> bool:
        """Update the physical e-Paper display with rendered content.

        Args:
            content: Rendered PIL Image to display

        Returns:
            True if update was successful, False otherwise
        """
        self.performance.start_operation("update_display")

        try:
            # Initialize display if needed
            if not self.display.initialize():
                logger.error("Failed to initialize e-Paper display")
                return False

            # Convert image to display format
            self.performance.start_operation("convert_to_display_format")
            display_buffer = self.image_processor.convert_to_display_format(
                content, self.capabilities
            )
            conversion_time = self.performance.end_operation("convert_to_display_format")
            logger.debug(f"Display format conversion completed in {conversion_time:.2f}ms")

            # Render to display
            self.performance.start_operation("display_render")
            success = self.display.render(display_buffer)
            display_time = self.performance.end_operation("display_render")

            if success:
                logger.info(f"Successfully updated e-Paper display in {display_time:.2f}ms")
            else:
                logger.error("Failed to update e-Paper display")

            return success

        except Exception:
            logger.exception("Error updating e-Paper display")
            return False
        finally:
            total_time = self.performance.end_operation("update_display")
            logger.info(f"Display update completed in {total_time:.2f}ms")

    def render_from_events(
        self, events: list[CachedEvent], status_info: Optional[dict[str, Any]] = None
    ) -> Image.Image:
        """Convenience method to render from cached events.

        Args:
            events: List of cached events
            status_info: Additional status information

        Returns:
            Rendered PIL Image
        """
        # Create view model using shared logic
        view_model = self.logic.create_view_model(events, status_info)

        # Render using the view model
        return self.render(view_model)

    def _load_fonts(self) -> dict[str, Union[FreeTypeFont, BuiltinFont]]:
        """Load fonts optimized for e-Paper display.

        Returns:
            Dictionary of font configurations
        """
        # This is now a lazy-loading function that returns an empty dict
        # Actual fonts will be loaded on first use via _get_font()
        return {}

    def _get_font(self, font_key: str) -> Union[FreeTypeFont, BuiltinFont]:
        """Get a font from cache or load it if not cached.

        Implements LRU caching for fonts to minimize memory usage.

        Args:
            font_key: Key identifying the font ("countdown", "title", etc.)

        Returns:
            Font object from cache or newly loaded
        """
        # Check if font is already in cache
        if font_key in self._font_cache:
            # Move to end of OrderedDict to mark as recently used
            font = self._font_cache.pop(font_key)
            self._font_cache[font_key] = font
            return font

        # Get font sizes from shared typography constants
        font_size = int(self._typography[font_key])

        # Load the font
        try:
            if font_key in ["countdown", "title"]:
                # Bold fonts
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
                )
            else:
                # Regular fonts
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
                )
        except OSError:
            # Fallback to default font
            logger.warning(f"System font not available for {font_key}, using default")
            font = ImageFont.load_default()

        # Add to cache with LRU eviction
        if len(self._font_cache) >= MAX_FONT_CACHE_SIZE:
            # Remove least recently used font (first item in OrderedDict)
            self._font_cache.popitem(last=False)

        # Add new font to cache
        self._font_cache[font_key] = font
        return font

    def _get_text_bbox(
        self, draw: ImageDraw.ImageDraw, text: str, font_key: str
    ) -> tuple[float, float, float, float]:
        """Get text bounding box with caching to avoid repeated calculations.

        Args:
            draw: ImageDraw object
            text: Text to measure
            font_key: Font key to use

        Returns:
            Bounding box as (x1, y1, x2, y2)
        """
        # Create cache key from text and font
        font = self._get_font(font_key)
        cache_key = (text, font_key, id(font))

        # Check if measurement is in cache
        if cache_key in self._text_measure_cache:
            # Move to end of OrderedDict to mark as recently used
            bbox = self._text_measure_cache.pop(cache_key)
            self._text_measure_cache[cache_key] = bbox
            return bbox

        # Calculate text bbox
        bbox = draw.textbbox((0, 0), text, font=font)

        # Add to cache with LRU eviction
        if len(self._text_measure_cache) >= MAX_TEXT_MEASURE_CACHE_SIZE:
            # Remove least recently used measurement (first item in OrderedDict)
            self._text_measure_cache.popitem(last=False)

        # Add new measurement to cache
        self._text_measure_cache[cache_key] = bbox
        return bbox

    def _get_image_buffer(self, mode: str, width: int, height: int) -> Image.Image:
        """Get an image buffer from the pool or create a new one.

        Args:
            mode: Image mode ("L", "RGB", etc.)
            width: Image width
            height: Image height

        Returns:
            PIL Image buffer
        """
        buffer_key = (mode, width, height)

        # Check if we have a buffer of this size in the pool
        if self._image_buffer_pool.get(buffer_key):
            # Reuse an existing buffer
            image = self._image_buffer_pool[buffer_key].pop()
            # Clear the buffer by filling with background color
            image.paste(self._colors["background"], (0, 0, width, height))
            return image

        # Create a new buffer
        return Image.new(mode, (width, height), self._colors["background"])

    def _recycle_image_buffer(self, image: Image.Image) -> None:
        """Recycle an image buffer back to the pool.

        Args:
            image: PIL Image to recycle
        """
        buffer_key = (image.mode, image.width, image.height)

        # Initialize pool for this buffer size if needed
        if buffer_key not in self._image_buffer_pool:
            self._image_buffer_pool[buffer_key] = []

        # Only keep up to BUFFER_POOL_SIZE buffers of each size
        if len(self._image_buffer_pool[buffer_key]) < BUFFER_POOL_SIZE:
            self._image_buffer_pool[buffer_key].append(image)

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        bbox: tuple[int, int, int, int],
        radius: int,
        fill_color: Any,
        outline_color: Optional[Any] = None,
        outline_width: int = 1,
    ) -> None:
        """Draw a rounded rectangle with the specified parameters.

        Args:
            draw: PIL ImageDraw object
            bbox: Bounding box as (x1, y1, x2, y2)
            radius: Corner radius in pixels
            fill_color: Fill color for the rectangle
            outline_color: Optional outline color
            outline_width: Width of the outline in pixels
        """
        x1, y1, x2, y2 = bbox

        # Ensure radius doesn't exceed half the smallest dimension
        max_radius = min((x2 - x1) // 2, (y2 - y1) // 2)
        radius = min(radius, max_radius)

        # Draw the main rectangle body
        draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill_color)
        draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill_color)

        # Draw the four corners as circles
        # Top-left
        draw.pieslice(((x1, y1), (x1 + 2 * radius, y1 + 2 * radius)), 180, 270, fill=fill_color)
        # Top-right
        draw.pieslice(((x2 - 2 * radius, y1), (x2, y1 + 2 * radius)), 270, 360, fill=fill_color)
        # Bottom-left
        draw.pieslice(((x1, y2 - 2 * radius), (x1 + 2 * radius, y2)), 90, 180, fill=fill_color)
        # Bottom-right
        draw.pieslice(((x2 - 2 * radius, y2 - 2 * radius), (x2, y2)), 0, 90, fill=fill_color)

        # Draw outline if specified
        if outline_color is not None:
            self._draw_rounded_rectangle_outline(draw, bbox, radius, outline_color, outline_width)

    def _draw_rounded_rectangle_outline(
        self,
        draw: ImageDraw.ImageDraw,
        bbox: tuple[int, int, int, int],
        radius: int,
        outline_color: Any,
        width: int = 1,
    ) -> None:
        """Draw the outline of a rounded rectangle.

        Args:
            draw: PIL ImageDraw object
            bbox: Bounding box as (x1, y1, x2, y2)
            radius: Corner radius in pixels
            outline_color: Color for the outline
            width: Width of the outline in pixels
        """
        x1, y1, x2, y2 = bbox

        # Ensure radius doesn't exceed half the smallest dimension
        max_radius = min((x2 - x1) // 2, (y2 - y1) // 2)
        radius = min(radius, max_radius)

        # Draw the straight line segments
        # Top line
        draw.rectangle((x1 + radius, y1, x2 - radius, y1 + width), fill=outline_color)
        # Bottom line
        draw.rectangle((x1 + radius, y2 - width, x2 - radius, y2), fill=outline_color)
        # Left line
        draw.rectangle((x1, y1 + radius, x1 + width, y2 - radius), fill=outline_color)
        # Right line
        draw.rectangle((x2 - width, y1 + radius, x2, y2 - radius), fill=outline_color)

        # Draw corner outlines as arcs
        for _ in range(width):
            # Top-left
            draw.arc([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=outline_color)
            # Top-right
            draw.arc([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=outline_color)
            # Bottom-left
            draw.arc([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=outline_color)
            # Bottom-right
            draw.arc([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=outline_color)

    def _format_time_remaining(self, minutes: int) -> str:
        """Format time remaining as 'X HOURS Y MINUTES' to match web display.

        Args:
            minutes: Total minutes remaining

        Returns:
            Formatted time string matching web display format
        """
        if minutes < 60:
            return f"{minutes} MINUTES"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours} HOURS"
        return f"{hours} HOURS {remaining_minutes} MINUTES"

    def _can_do_partial_update(self, view_model: WhatsNextViewModel) -> bool:
        """Check if partial update is possible.

        Args:
            view_model: Current view model to render

        Returns:
            True if partial update can be used, False otherwise
        """
        if not self.capabilities.supports_partial_update:
            return False

        if self._last_view_model is None:
            return False

        # Check if only time-related information changed
        # This is a simple heuristic - in practice, you'd want more sophisticated diff detection
        last_vm = self._last_view_model

        # Same events, just time updates
        if (
            len(view_model.current_events) == len(last_vm.current_events)
            and len(view_model.next_events) == len(last_vm.next_events)
            and view_model.display_date == last_vm.display_date
        ):
            # Check if event subjects are the same
            current_subjects = [e.subject for e in view_model.current_events]
            last_current_subjects = [e.subject for e in last_vm.current_events]

            next_subjects = [e.subject for e in view_model.next_events]
            last_next_subjects = [e.subject for e in last_vm.next_events]

            if current_subjects == last_current_subjects and next_subjects == last_next_subjects:
                return True

        return False

    def _render_partial_update(self, view_model: WhatsNextViewModel) -> Image.Image:
        """Render partial update (optimized for e-Paper).

        Args:
            view_model: View model to render

        Returns:
            Rendered PIL Image with partial updates
        """
        # For simplicity, fall back to full render
        # In practice, you'd implement sophisticated partial update logic
        logger.debug("Partial update requested, falling back to full render")
        return self._render_full_image(view_model)

    def _render_full_image(self, view_model: WhatsNextViewModel) -> Image.Image:
        """Render full image with updated 3-zone layout for cleaner card-based design.

        Layout Structure:
        - Zone 1 (130px): Countdown section with prominent time display
        - Zone 2 (200px): Event card section with enhanced spacing
        - Zone 4 (70px): Footer section with contextual messages
        - Total: 300x400px exactly

        Args:
            view_model: View model to render

        Returns:
            Complete rendered PIL Image with enhanced layout
        """
        self.performance.start_operation("render_full_image")

        try:
            # Get layout dimensions from shared layout constants
            layout = get_layout_for_renderer("epaper")
            # Ensure width and height are integers
            width, height = int(layout["width"]), int(layout["height"])

            # Determine image mode based on capabilities
            if self.capabilities.supports_red:
                mode = "RGB"
            elif self.capabilities.supports_grayscale:
                mode = "L"
            else:
                mode = "1"  # Monochrome

            # Get image buffer from pool or create new one
            image = self._get_image_buffer(mode, width, height)
            draw = ImageDraw.Draw(image)

            # Define zone dimensions for enhanced layout
            zone1_height = 130  # Reduced from 190px for better proportions
            zone2_height = 200  # Increased from 150px for breathing room
            zone4_height = 70  # Increased from 50px for better footer

            # Zone boundaries
            zone1_y = 0
            zone2_y = zone1_height
            zone4_y = zone1_height + zone2_height

            # Get next event for time calculation
            next_event = view_model.get_next_event()

            # ZONE 1: Time gap display
            self.performance.start_operation("render_zone1")
            self._render_zone1_time_gap(draw, mode, next_event, 0, zone1_y, width, zone1_height)
            zone1_time = self.performance.end_operation("render_zone1")
            logger.debug(f"Zone 1 rendered in {zone1_time:.2f}ms")

            # ZONE 2: Meeting card
            self.performance.start_operation("render_zone2")
            self._render_zone2_meeting_card(draw, mode, next_event, 0, zone2_y, width, zone2_height)
            zone2_time = self.performance.end_operation("render_zone2")
            logger.debug(f"Zone 2 rendered in {zone2_time:.2f}ms")

            # ZONE 4: Context area
            self.performance.start_operation("render_zone4")
            self._render_zone4_context(draw, mode, view_model, 0, zone4_y, width, zone4_height)
            zone4_time = self.performance.end_operation("render_zone4")
            logger.debug(f"Zone 4 rendered in {zone4_time:.2f}ms")

            total_time = self.performance.end_operation("render_full_image")
            logger.debug(f"Full image rendered in {total_time:.2f}ms")

            return image
        except Exception as e:
            # Clean up resources in case of error
            # Don't recycle the image if there was an error
            # No need to delete the image variable here
            error_msg = str(e)
            logger.exception(f"Error in _render_full_image: {error_msg}")
            raise

    def _render_zone1_time_gap(
        self,
        draw: ImageDraw.ImageDraw,
        mode: str,
        next_event: Any,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Render Zone 1: Countdown section with prominent time display.

        Args:
            draw: PIL ImageDraw object
            mode: Image mode
            next_event: Next event data
            x, y: Zone position
            width, height: Zone dimensions
        """
        if not next_event or not hasattr(next_event, "time_until_minutes"):
            # No meeting case - use enhanced spacing and messaging
            container_padding = 20  # Increased from 12px for better spacing
            container_x = x + container_padding
            container_y = y + (height - 80) // 2  # Adjusted for new height
            container_width = width - 2 * container_padding
            container_height = 80

            # Gray background container with enhanced border radius
            gray_bg = self._colors["background_secondary"]
            self._draw_rounded_rectangle(
                draw,
                (
                    container_x,
                    container_y,
                    container_x + container_width,
                    container_y + container_height,
                ),
                10,  # Increased from 6px to 10px border radius
                gray_bg,
            )

            # "Plenty of time" text with better positioning
            text = "Plenty of time"
            text_color = self._colors["text_primary"]

            # Get font from cache
            font = self._get_font("subtitle")

            # Center text in container using cached text measurement
            bbox = self._get_text_bbox(draw, text, "subtitle")
            text_width = bbox[2] - bbox[0]
            text_x = container_x + (container_width - text_width) // 2
            text_y = container_y + (container_height - 18) // 2  # Better centering
            draw.text((text_x, text_y), text, font=font, fill=text_color)
            return

        # Calculate time remaining text
        minutes = next_event.time_until_minutes
        time_text = f"STARTS IN {self._format_time_remaining(minutes)}"

        # Container with enhanced padding and spacing
        container_padding = 20  # Increased from 12px for better margins
        container_x = x + container_padding
        container_y = y + (height - 90) // 2  # Adjusted for new zone height
        container_width = width - 2 * container_padding
        container_height = 90

        # Gray background container with enhanced border radius
        gray_bg = self._colors["background_secondary"]
        self._draw_rounded_rectangle(
            draw,
            (
                container_x,
                container_y,
                container_x + container_width,
                container_y + container_height,
            ),
            10,  # Increased from 6px to 10px border radius
            gray_bg,
        )

        # Main countdown text using new larger 30px countdown font
        text_color = self._colors["text_primary"]

        # Get font from cache
        font = self._get_font("countdown")

        # Center text in container with improved font using cached text measurement
        bbox = self._get_text_bbox(draw, time_text, "countdown")
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])
        text_x = container_x + (container_width - text_width) // 2
        text_y = container_y + (container_height - text_height) // 2

        draw.text((text_x, text_y), time_text, font=font, fill=text_color)

    def _render_zone2_meeting_card(
        self,
        draw: ImageDraw.ImageDraw,
        mode: str,
        next_event: Any,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Render Zone 2: Enhanced event card with improved spacing and rounded design.

        Args:
            draw: PIL ImageDraw object
            mode: Image mode
            next_event: Next event data
            x, y: Zone position
            width, height: Zone dimensions
        """
        if not next_event:
            return

        # Card container with enhanced padding for breathing room
        card_padding = 20  # Increased from 16px to 20px for better spacing
        card_x = x + card_padding
        card_y = y + card_padding
        card_width = width - 2 * card_padding
        card_height = height - 2 * card_padding

        # White background with black border and enhanced border radius
        white_bg = self._colors["background"]
        black_border = self._colors["text_primary"]

        self._draw_rounded_rectangle(
            draw,
            (card_x, card_y, card_x + card_width, card_y + card_height),
            10,  # Increased from 6px to 10px border radius
            white_bg,
            black_border,
            2,
        )

        # Content inside card with improved padding
        content_padding = 20  # Increased from 16px to 20px for better internal spacing
        content_x = card_x + content_padding
        content_y = card_y + content_padding

        # Event title - improved positioning and spacing
        title_color = self._colors["text_primary"]
        title_text = (
            next_event.subject[:30] + "..." if len(next_event.subject) > 30 else next_event.subject
        )

        # Get font from cache
        subtitle_font = self._get_font("subtitle")
        draw.text((content_x, content_y), title_text, font=subtitle_font, fill=title_color)

        # Time range with improved vertical spacing
        if hasattr(next_event, "formatted_time_range"):
            time_y = content_y + 40  # Increased from 35px for better spacing
            time_color = self._colors["text_secondary"]

            # Get font from cache
            body_font = self._get_font("body")
            draw.text(
                (content_x, time_y),
                next_event.formatted_time_range,
                font=body_font,
                fill=time_color,
            )

        # Location with improved spacing and positioning
        if hasattr(next_event, "location") and next_event.location:
            location_y = content_y + 75  # Increased from 65px for better spacing
            location_color = self._colors["text_supporting"]
            location_text = (
                f"📍 {next_event.location[:25]}..."
                if len(next_event.location) > 25
                else f"📍 {next_event.location}"
            )

            # Get font from cache
            small_font = self._get_font("small")
            draw.text(
                (content_x, location_y),
                location_text,
                font=small_font,
                fill=location_color,
            )

    def _render_zone4_context(
        self,
        draw: ImageDraw.ImageDraw,
        mode: str,
        view_model: Any,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Render Zone 4: Enhanced footer with dynamic contextual messages.

        Args:
            draw: PIL ImageDraw object
            mode: Image mode
            view_model: View model data
            x, y: Zone position
            width, height: Zone dimensions
        """
        # Light gray background for context area
        context_bg = self._colors["background_secondary"]
        draw.rectangle((x, y, x + width, y + height), fill=context_bg)

        # Determine contextual message based on current state
        next_event = view_model.get_next_event() if hasattr(view_model, "get_next_event") else None

        # Dynamic contextual messages
        if not next_event:
            # No meetings case - encouraging message
            status_text = "✨ Plenty of time to focus"
        elif hasattr(next_event, "time_until_minutes"):
            minutes = next_event.time_until_minutes
            if minutes <= 5:
                status_text = "⏰ Meeting starting soon"
            elif minutes <= 15:
                status_text = "📅 Upcoming meeting"
            elif minutes <= 60:
                status_text = "⏳ Meeting within the hour"
            else:
                status_text = "📆 Next meeting scheduled"
        # Fallback to data status
        elif hasattr(view_model, "status_info") and view_model.status_info.is_cached:
            status_text = "📱 Cached data"
        else:
            status_text = "🔄 Live data"

        # Enhanced text positioning with better vertical centering
        text_y = y + (height - 12) // 2  # Better centering for improved height
        text_color = self._colors["text_supporting"]

        # Get font from cache
        small_font = self._get_font("small")

        # Center text horizontally with improved positioning using cached text measurement
        bbox = self._get_text_bbox(draw, status_text, "small")
        text_width = bbox[2] - bbox[0]
        text_x = x + (width - text_width) // 2

        draw.text((text_x, text_y), status_text, font=small_font, fill=text_color)

    def _render_error_image(self, error_message: str) -> Image.Image:
        """Render error message as image.

        Args:
            error_message: Error message to display

        Returns:
            Error image for e-Paper display
        """
        width, height = self.capabilities.width, self.capabilities.height

        # Determine mode and background
        mode = "L" if self.capabilities.supports_grayscale else "1"

        # Get image buffer from pool or create new one
        image = self._get_image_buffer(mode, width, height)
        draw = ImageDraw.Draw(image)

        try:
            # Error icon and message using consistent colors
            error_y = height // 2 - 40
            accent_color = self._colors["accent"]

            # Get fonts from cache
            title_font = self._get_font("title")
            subtitle_font = self._get_font("subtitle")
            small_font = self._get_font("small")

            draw.text((width // 2 - 20, error_y), "⚠️", font=title_font, fill=accent_color)

            title_color = self._colors["text_primary"]
            draw.text(
                (width // 2 - 80, error_y + 40),
                "Display Error",
                font=subtitle_font,
                fill=title_color,
            )

            # Wrap error message
            max_chars = width // 8  # Rough estimate
            wrapped_message = (
                error_message[:max_chars] + "..."
                if len(error_message) > max_chars
                else error_message
            )
            body_color = self._colors["text_primary"]
            draw.text(
                (width // 2 - len(wrapped_message) * 3, error_y + 70),
                wrapped_message,
                font=small_font,
                fill=body_color,
            )

            return image
        except Exception:
            # Clean up resources in case of error
            self._recycle_image_buffer(image)
            logger.exception("Error in _render_error_image")

            # Create a very simple error image as fallback
            return Image.new(mode, (width, height), self._colors["background"])

    def render_error(
        self, error_message: str, cached_events: Optional[list[CachedEvent]] = None
    ) -> Image.Image:
        """Render an error message with optional cached events for e-Paper display.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show alongside error

        Returns:
            PIL Image with error display optimized for e-Paper
        """
        logger.debug(f"EInkWhatsNextRenderer.render_error called: {error_message}")
        self.performance.start_operation("render_error")

        try:
            width, height = self.capabilities.width, self.capabilities.height

            # Determine image mode based on capabilities
            if self.capabilities.supports_red:
                mode = "RGB"
            elif self.capabilities.supports_grayscale:
                mode = "L"
            else:
                mode = "1"  # Monochrome

            # Get image buffer from pool or create new one
            image = self._get_image_buffer(mode, width, height)
            draw = ImageDraw.Draw(image)

            y_pos = 20

            # Get fonts from cache
            title_font = self._get_font("title")
            subtitle_font = self._get_font("subtitle")
            body_font = self._get_font("body")
            small_font = self._get_font("small")

            # Header with current date
            header_text = datetime.now().strftime("%A, %B %d")
            title_color = self._colors["text_primary"]
            draw.text((20, y_pos), header_text, font=title_font, fill=title_color)
            y_pos += 50

            # Error icon and title
            accent_color = self._colors["accent"]
            draw.text((width // 2 - 20, y_pos), "⚠️", font=title_font, fill=accent_color)
            y_pos += 40

            subtitle_color = self._colors["text_secondary"]
            draw.text(
                (width // 2 - 80, y_pos),
                "Connection Issue",
                font=subtitle_font,
                fill=subtitle_color,
            )
            y_pos += 40

            # Error message (wrapped)
            max_chars = width // 8  # Rough estimate for character width
            wrapped_message = (
                error_message[:max_chars] + "..."
                if len(error_message) > max_chars
                else error_message
            )
            body_color = self._colors["text_primary"]
            draw.text((20, y_pos), wrapped_message, font=body_font, fill=body_color)
            y_pos += 60

            # Show cached events if available
            if cached_events:
                subtitle_color = self._colors["text_secondary"]
                draw.text((20, y_pos), "📱 Cached Data", font=subtitle_font, fill=subtitle_color)
                y_pos += 30

                # Show up to 3 cached events
                for event in cached_events[:3]:
                    if y_pos > height - 60:  # Stop if running out of space
                        break

                    # Event title
                    event_title = (
                        event.subject[:40] + "..." if len(event.subject) > 40 else event.subject
                    )
                    body_color = self._colors["text_primary"]
                    draw.text((30, y_pos), f"• {event_title}", font=small_font, fill=body_color)
                    y_pos += 18

                    # Event time
                    meta_color = self._colors["text_supporting"]
                    draw.text(
                        (35, y_pos),
                        event.format_time_range(),
                        font=small_font,
                        fill=meta_color,
                    )
                    y_pos += 25
            else:
                # No cached data message
                meta_color = self._colors["text_supporting"]
                draw.text(
                    (20, y_pos),
                    "❌ No cached data available",
                    font=small_font,
                    fill=meta_color,
                )

            render_time = self.performance.end_operation("render_error")
            logger.debug(f"Error screen rendered in {render_time:.2f}ms")
            return image

        except Exception as e:
            # Clean up resources in case of error
            logger.exception("Error rendering error image")

            # Safely end the performance operation if it was started
            with contextlib.suppress(KeyError):
                # Operation might not have been started, which can happen in tests
                self.performance.end_operation("render_error")

            return self._render_error_image(f"Critical error: {e}")

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Image.Image:
        """Render authentication prompt for device code flow on e-Paper display.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            PIL Image with authentication prompt optimized for e-Paper
        """
        logger.debug("EInkWhatsNextRenderer.render_authentication_prompt called")
        self.performance.start_operation("render_auth_prompt")

        try:
            width, height = self.capabilities.width, self.capabilities.height

            # Determine image mode based on capabilities
            if self.capabilities.supports_red:
                mode = "RGB"
            elif self.capabilities.supports_grayscale:
                mode = "L"
            else:
                mode = "1"  # Monochrome

            # Get image buffer from pool or create new one
            image = self._get_image_buffer(mode, width, height)
            draw = ImageDraw.Draw(image)

            # Get fonts from cache
            title_font = self._get_font("title")
            subtitle_font = self._get_font("subtitle")
            body_font = self._get_font("body")
            small_font = self._get_font("small")

            y_pos = 20

            # Header
            title_color = self._colors["text_primary"]
            draw.text(
                (20, y_pos),
                "🔐 Authentication Required",
                font=title_font,
                fill=title_color,
            )
            y_pos += 50

            # Subtitle
            subtitle_color = self._colors["text_secondary"]
            draw.text(
                (20, y_pos),
                "Microsoft 365 Authentication",
                font=subtitle_font,
                fill=subtitle_color,
            )
            y_pos += 40

            # Instructions
            body_color = self._colors["text_primary"]
            draw.text((20, y_pos), "To access your calendar:", font=body_font, fill=body_color)
            y_pos += 40

            # Step 1
            accent_color = self._colors["accent"]
            draw.text((20, y_pos), "1. Visit:", font=body_font, fill=accent_color)
            y_pos += 25

            # URL (wrap if too long)
            url_text = verification_uri
            if len(url_text) > 35:  # Wrap long URLs
                url_text = url_text[:35] + "..."

            meta_color = self._colors["text_supporting"]
            draw.text((30, y_pos), url_text, font=small_font, fill=meta_color)
            y_pos += 40

            # Step 2
            draw.text((20, y_pos), "2. Enter code:", font=body_font, fill=accent_color)
            y_pos += 25

            # User code (emphasized)
            title_color = self._colors["text_primary"]
            draw.text((30, y_pos), user_code, font=subtitle_font, fill=title_color)
            y_pos += 60

            # Status
            body_color = self._colors["text_primary"]
            draw.text(
                (20, y_pos),
                "Waiting for authentication...",
                font=body_font,
                fill=body_color,
            )
            y_pos += 25

            # Loading indicator
            accent_color = self._colors["accent"]
            draw.text((width // 2 - 10, y_pos), "⏳", font=title_font, fill=accent_color)

            render_time = self.performance.end_operation("render_auth_prompt")
            logger.debug(f"Authentication prompt rendered in {render_time:.2f}ms")
            return image

        except Exception as e:
            # Clean up resources in case of error
            logger.exception("Error rendering authentication prompt")

            # Safely end the performance operation if it was started
            with contextlib.suppress(KeyError):
                # Operation wasn't started, which can happen in tests
                self.performance.end_operation("render_auth_prompt")

            return self._render_error_image(f"Authentication prompt error: {e}")

    def _render_using_html_conversion(self, view_model: WhatsNextViewModel) -> Image.Image:  # noqa: PLR0915
        """Render view model using HTML-to-PNG conversion.

        This method uses the WhatsNextRenderer to generate HTML content and then
        converts it to a PNG image using the HTML-to-PNG converter.

        Args:
            view_model: View model to render

        Returns:
            PIL Image rendered from HTML

        Raises:
            RuntimeError: If HTML-to-PNG conversion fails
        """
        self.performance.start_operation("render_html_to_png")

        try:
            # Check if HTML converter is available
            if self.html_converter is None:
                logger.warning("HTML-to-PNG converter not available, falling back to PIL rendering")
                return self._render_full_image(view_model)

            logger.info(f"HTML converter is available: {self.html_converter}")
            logger.info(f"HTML converter type: {type(self.html_converter)}")
            logger.info(
                f"HTML converter output path: {getattr(self.html_converter, 'output_path', 'Not set')}"
            )
            if hasattr(self.html_converter, "hti"):
                logger.info(
                    f"HTML converter HTI output path: {getattr(self.html_converter.hti, 'output_path', 'Not set')}"
                )

            # Generate a cache key based on view model content
            # This is a simple hash of the important view model properties
            cache_key = self._generate_cache_key(view_model)

            # Check if we have a cached render
            if cache_key in self._html_render_cache:
                cached_path, timestamp = self._html_render_cache[cache_key]
                if Path(cached_path).exists():
                    # Move to end of OrderedDict to mark as recently used
                    self._html_render_cache.pop(cache_key)
                    self._html_render_cache[cache_key] = (cached_path, timestamp)

                    # Load the cached image
                    logger.debug(f"Using cached HTML render: {cached_path}")
                    try:
                        image = Image.open(cached_path)
                        return image.copy()  # Return a copy to avoid issues with file locks
                    except Exception as e:
                        logger.warning(f"Failed to load cached image: {e}")
                        # Continue with fresh rendering

            # Generate HTML content using WhatsNextRenderer
            logger.debug("Generating HTML content")
            self.performance.start_operation("generate_html")

            # Use the HTML renderer to generate HTML content
            self.html_renderer.render(view_model)
            html_generation_time = self.performance.end_operation("generate_html")
            logger.debug(f"HTML content generated in {html_generation_time:.2f}ms")

            # Use a more reliable directory for output
            output_dir = Path("epaper_output")
            output_dir.mkdir(exist_ok=True, parents=True)
            logger.info(f"Using output directory: {output_dir}")

            # Generate a unique filename for the output image
            output_filename = f"epaper_render_{os.urandom(4).hex()}.png"
            output_path = output_dir / output_filename

            # Convert HTML to PNG
            logger.info(f"Converting HTML to PNG: {output_path}")
            self.performance.start_operation("html_to_png_conversion")

            # Temporarily set the output path of the HTML converter
            original_output_path = None
            if hasattr(self.html_converter, "hti") and self.html_converter.hti is not None:
                original_output_path = self.html_converter.hti.output_path
                self.html_converter.hti.output_path = str(output_dir)
                logger.info(
                    f"Set HTML converter output path to: {self.html_converter.hti.output_path}"
                )

            try:
                # Use just the filename, not the full path
                logger.info(f"Converting HTML to PNG with filename: {output_filename}")
                if hasattr(self.html_converter, "hti") and self.html_converter.hti is not None:
                    logger.info(
                        f"HTML converter output path before conversion: {self.html_converter.hti.output_path}"
                    )
                # Get the webserver URL from the HTTP client

                # Get the webserver port from the settings
                webserver_port = getattr(self.settings, "web_port", 8080)

                # Get the local network interface
                host_ip = get_local_network_interface()

                # Construct the URL for the webserver - use the base URL without any path
                webserver_url = f"http://{host_ip}:{webserver_port}"
                logger.info(f"Using webserver URL: {webserver_url}")

                # Use the URL-based conversion method
                png_path = self.html_converter.convert_url_to_png(
                    url=webserver_url, output_filename=output_filename
                )
                logger.info(f"Conversion result: {png_path}")
            finally:
                # Restore the original output path
                if (
                    original_output_path is not None
                    and hasattr(self.html_converter, "hti")
                    and self.html_converter.hti is not None
                ):
                    self.html_converter.hti.output_path = original_output_path

            conversion_time = self.performance.end_operation("html_to_png_conversion")
            logger.debug(f"HTML-to-PNG conversion completed in {conversion_time:.2f}ms")

            if not png_path or not Path(png_path).exists():
                logger.error(
                    f"HTML-to-PNG conversion failed, checking for file in output directory: {output_dir}"
                )
                # Try to find the file in the output directory
                expected_path = output_dir / output_filename
                if expected_path.exists():
                    logger.info(f"Found output file at expected path: {expected_path}")
                    png_path = str(expected_path)
                else:
                    logger.error(f"Output file not found at expected path: {expected_path}")
                    self._raise_conversion_failed_error()

            # At this point, png_path is guaranteed to be a valid string
            assert png_path is not None, "png_path should not be None after validation"

            # Load the generated PNG as a PIL Image
            logger.info(f"Loading PNG image from: {png_path}")
            image = Image.open(png_path)

            # Cache the result
            self._cache_html_render(cache_key, png_path)

            # Return a copy of the image to avoid issues with file locks
            return image.copy()

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Error in HTML-to-PNG rendering: {error_msg}")
            logger.warning("Falling back to PIL rendering")
            return self._render_full_image(view_model)
        finally:
            total_time = self.performance.end_operation("render_html_to_png")
            logger.info(f"HTML-to-PNG rendering completed in {total_time:.2f}ms")

    def _generate_cache_key(self, view_model: WhatsNextViewModel) -> str:
        """Generate a cache key for the view model.

        Args:
            view_model: View model to generate cache key for

        Returns:
            Cache key string
        """
        # Create a simple hash of the important view model properties
        key_parts: list[str] = []

        # Add current events
        if view_model.current_events:
            key_parts.extend(
                f"c:{event.subject}:{event.start_time}:{event.end_time}"
                for event in view_model.current_events
            )

        # Add next events
        if view_model.next_events:
            key_parts.extend(
                f"n:{event.subject}:{event.start_time}:{event.end_time}"
                for event in view_model.next_events
            )

        # Add later events (just count)
        if view_model.later_events:
            key_parts.append(f"l:{len(view_model.later_events)}")

        # Add display date and current time
        key_parts.append(f"d:{view_model.display_date}")
        key_parts.append(f"t:{view_model.current_time.isoformat()}")

        # Join all parts and create a hash
        return ":".join(key_parts)

    def _cache_html_render(self, cache_key: str, file_path: str) -> None:
        """Cache an HTML render result.

        Args:
            cache_key: Cache key for the render
            file_path: Path to the rendered image file
        """
        # Add to cache with LRU eviction
        if len(self._html_render_cache) >= HTML_RENDER_CACHE_SIZE:
            # Remove least recently used render (first item in OrderedDict)
            old_key, (old_path, _) = self._html_render_cache.popitem(last=False)

            # Delete the old file if it exists
            try:
                old_path_obj = Path(old_path)
                if old_path_obj.exists():
                    old_path_obj.unlink()
                    logger.debug(f"Removed old cached render: {old_path}")
            except Exception as e:
                logger.warning(f"Failed to remove old cached render: {e}")

        # Add new render to cache
        self._html_render_cache[cache_key] = (file_path, datetime.now())
        logger.debug(f"Added HTML render to cache: {file_path}")

    def cleanup(self) -> None:
        """Clean up resources used by the renderer.

        This method should be called when the renderer is no longer needed
        to free up resources.
        """
        # Clean up HTML converter
        if hasattr(self, "html_converter") and self.html_converter is not None:
            try:
                self.html_converter.cleanup()
                logger.debug("HTML converter cleaned up")
            except Exception as e:
                logger.warning(f"Failed to clean up HTML converter: {e}")

        # Clean up temporary directory
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            try:
                # Remove all files in the directory
                for file_path in self.temp_dir.glob("*"):
                    with contextlib.suppress(Exception):
                        file_path.unlink()

                # Remove the directory
                self.temp_dir.rmdir()
                logger.debug(f"Removed temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")

    def _raise_conversion_failed_error(self) -> None:
        """Raise a RuntimeError for HTML-to-PNG conversion failure."""
        raise RuntimeError("HTML-to-PNG conversion failed")
