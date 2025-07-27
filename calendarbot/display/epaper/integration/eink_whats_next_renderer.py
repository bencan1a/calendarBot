"""
E-Paper specialized renderer for What's Next view using shared business logic.

Color Consistency:
- Uses identical grayscale color palette as the web WhatsNext view
- Colors extracted from calendarbot/web/static/layouts/whats-next-view/whats-next-view.css
- Ensures visual consistency between web and e-Paper rendering
"""

import logging
import math
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from PIL.ImageFont import ImageFont as BuiltinFont

if TYPE_CHECKING:
    # Only import for type checking
    from calendarbot.cache.models import CachedEvent
    from calendarbot.display.renderer_interface import InteractionEvent, RendererInterface
    from calendarbot.display.whats_next_data_model import EventData, WhatsNextViewModel
    from calendarbot.display.whats_next_logic import WhatsNextLogic
else:
    # Runtime imports with fallback
    try:
        from calendarbot.cache.models import CachedEvent
        from calendarbot.display.renderer_interface import InteractionEvent, RendererInterface
        from calendarbot.display.whats_next_data_model import EventData, WhatsNextViewModel
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
        InteractionEvent = Dict[str, Any]
        WhatsNextViewModel = Dict[str, Any]
        EventData = Dict[str, Any]
        CachedEvent = Dict[str, Any]

# Import e-Paper components
from ..abstraction import DisplayAbstractionLayer
from ..capabilities import DisplayCapabilities
from ..drivers.mock_eink_driver import EInkDriver
from ..utils.colors import EPaperColors, convert_to_pil_color, get_rendering_colors
from ..utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

# E-Paper availability flag for tests and runtime detection
EPAPER_AVAILABLE = True  # Indicates that e-Paper support is compiled in


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

        # Font configuration for e-Paper
        self._fonts = self._load_fonts()

        # Color configuration using consistent palette from web CSS
        self._colors = get_rendering_colors()

        logger.info("EInkWhatsNextRenderer initialized with consistent color palette")

    def render(self, view_model: WhatsNextViewModel) -> Image.Image:
        """Render the view model to e-Paper format.

        Args:
            view_model: Data model containing all information needed for rendering

        Returns:
            PIL Image optimized for e-Paper display
        """
        logger.debug("EInkWhatsNextRenderer.render called with view model")

        try:
            # Check if we can do partial update (diff detection)
            if self._can_do_partial_update(view_model):
                logger.debug("Using partial update optimization")
                return self._render_partial_update(view_model)

            # Full render
            logger.debug("Performing full render")
            image = self._render_full_image(view_model)

            # Cache for next diff detection
            self._last_view_model = view_model
            self._last_rendered_content = image.tobytes()

            return image

        except Exception as e:
            logger.error(f"Error rendering e-Paper view: {e}")
            return self._render_error_image(f"Rendering error: {e}")

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
        try:
            # Initialize display if needed
            if not self.display.initialize():
                logger.error("Failed to initialize e-Paper display")
                return False

            # Convert image to display format
            display_buffer = self.image_processor.convert_to_display_format(
                content, self.capabilities
            )

            # Render to display
            success = self.display.render(display_buffer)

            if success:
                logger.info("Successfully updated e-Paper display")
            else:
                logger.error("Failed to update e-Paper display")

            return success

        except Exception as e:
            logger.error(f"Error updating e-Paper display: {e}")
            return False

    def render_from_events(
        self, events: List[CachedEvent], status_info: Optional[Dict[str, Any]] = None
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

    def _load_fonts(self) -> Dict[str, Union[FreeTypeFont, BuiltinFont]]:
        """Load fonts optimized for e-Paper display.

        Returns:
            Dictionary of font configurations
        """
        fonts: Dict[str, Union[FreeTypeFont, BuiltinFont]] = {}

        try:
            # Try to load system fonts, fall back to defaults
            fonts["countdown"] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30
            )
            fonts["title"] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
            )
            fonts["subtitle"] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
            )
            fonts["body"] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
            )
            fonts["small"] = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12
            )
        except OSError:
            # Fallback to default fonts
            logger.warning("System fonts not available, using default fonts")
            fonts["countdown"] = ImageFont.load_default()
            fonts["title"] = ImageFont.load_default()
            fonts["subtitle"] = ImageFont.load_default()
            fonts["body"] = ImageFont.load_default()
            fonts["small"] = ImageFont.load_default()

        return fonts

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        bbox: Tuple[int, int, int, int],
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
        bbox: Tuple[int, int, int, int],
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
        else:
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
        # Force exact 300x400 dimensions regardless of capabilities
        width, height = 300, 400

        # Create image in appropriate mode using consistent colors
        if self.capabilities.supports_red:
            mode = "RGB"
            bg_color = convert_to_pil_color(self._colors["background"], mode)
        elif self.capabilities.supports_grayscale:
            mode = "L"
            bg_color = convert_to_pil_color(self._colors["background"], mode)
        else:
            mode = "1"  # Monochrome
            bg_color = convert_to_pil_color(self._colors["background"], mode)

        image = Image.new(mode, (width, height), bg_color)
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

        # ZONE 1: Time gap display (190px)
        self._render_zone1_time_gap(draw, mode, next_event, 0, zone1_y, width, zone1_height)

        # ZONE 2: Meeting card (150px)
        self._render_zone2_meeting_card(draw, mode, next_event, 0, zone2_y, width, zone2_height)

        # ZONE 4: Context area (50px)
        self._render_zone4_context(draw, mode, view_model, 0, zone4_y, width, zone4_height)

        return image

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
            gray_bg = convert_to_pil_color(
                self._colors.get("background_secondary", "#f5f5f5"), mode
            )
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
            text_color = convert_to_pil_color(self._colors["text_primary"], mode)
            # Center text in container
            bbox = draw.textbbox((0, 0), text, font=self._fonts["subtitle"])
            text_width = bbox[2] - bbox[0]
            text_x = container_x + (container_width - text_width) // 2
            text_y = container_y + (container_height - 18) // 2  # Better centering
            draw.text((text_x, text_y), text, font=self._fonts["subtitle"], fill=text_color)
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
        gray_bg = convert_to_pil_color(self._colors.get("background_secondary", "#e0e0e0"), mode)
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
        text_color = convert_to_pil_color(self._colors["text_primary"], mode)

        # Center text in container with improved font
        bbox = draw.textbbox((0, 0), time_text, font=self._fonts["countdown"])
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])
        text_x = container_x + (container_width - text_width) // 2
        text_y = container_y + (container_height - text_height) // 2

        draw.text((text_x, text_y), time_text, font=self._fonts["countdown"], fill=text_color)

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
        white_bg = convert_to_pil_color(self._colors["background"], mode)
        black_border = convert_to_pil_color(self._colors["text_primary"], mode)

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
        content_width = card_width - 2 * content_padding

        # Event title - improved positioning and spacing
        title_color = convert_to_pil_color(self._colors["text_primary"], mode)
        title_text = (
            next_event.subject[:30] + "..." if len(next_event.subject) > 30 else next_event.subject
        )
        draw.text(
            (content_x, content_y), title_text, font=self._fonts["subtitle"], fill=title_color
        )

        # Time range with improved vertical spacing
        if hasattr(next_event, "formatted_time_range"):
            time_y = content_y + 40  # Increased from 35px for better spacing
            time_color = convert_to_pil_color(self._colors["text_secondary"], mode)
            draw.text(
                (content_x, time_y),
                next_event.formatted_time_range,
                font=self._fonts["body"],
                fill=time_color,
            )

        # Location with improved spacing and positioning
        if hasattr(next_event, "location") and next_event.location:
            location_y = content_y + 75  # Increased from 65px for better spacing
            location_color = convert_to_pil_color(self._colors["text_supporting"], mode)
            location_text = (
                f"📍 {next_event.location[:25]}..."
                if len(next_event.location) > 25
                else f"📍 {next_event.location}"
            )
            draw.text(
                (content_x, location_y),
                location_text,
                font=self._fonts["small"],
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
        context_bg = convert_to_pil_color(self._colors.get("background_secondary", "#f5f5f5"), mode)
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
        else:
            # Fallback to data status
            if hasattr(view_model, "status_info") and view_model.status_info.is_cached:
                status_text = "📱 Cached data"
            else:
                status_text = "🔄 Live data"

        # Enhanced text positioning with better vertical centering
        text_y = y + (height - 12) // 2  # Better centering for improved height
        text_color = convert_to_pil_color(self._colors["text_supporting"], mode)

        # Center text horizontally with improved positioning
        bbox = draw.textbbox((0, 0), status_text, font=self._fonts["small"])
        text_width = bbox[2] - bbox[0]
        text_x = x + (width - text_width) // 2

        draw.text((text_x, text_y), status_text, font=self._fonts["small"], fill=text_color)

    def _render_error_image(self, error_message: str) -> Image.Image:
        """Render error message as image.

        Args:
            error_message: Error message to display

        Returns:
            Error image for e-Paper display
        """
        width, height = self.capabilities.width, self.capabilities.height

        # Determine mode and background
        if self.capabilities.supports_grayscale:
            mode = "L"
            bg_color = convert_to_pil_color(self._colors["background"], mode)
            image = Image.new(mode, (width, height), bg_color)
        else:
            mode = "1"
            bg_color = convert_to_pil_color(self._colors["background"], mode)
            image = Image.new(mode, (width, height), bg_color)

        draw = ImageDraw.Draw(image)

        # Error icon and message using consistent colors
        error_y = height // 2 - 40
        accent_color = convert_to_pil_color(self._colors["accent"], mode)
        draw.text((width // 2 - 20, error_y), "⚠️", font=self._fonts["title"], fill=accent_color)

        title_color = convert_to_pil_color(self._colors["text_title"], mode)
        draw.text(
            (width // 2 - 80, error_y + 40),
            "Display Error",
            font=self._fonts["subtitle"],
            fill=title_color,
        )

        # Wrap error message
        max_chars = width // 8  # Rough estimate
        wrapped_message = (
            error_message[:max_chars] + "..." if len(error_message) > max_chars else error_message
        )
        body_color = convert_to_pil_color(self._colors["text_body"], mode)
        draw.text(
            (width // 2 - len(wrapped_message) * 3, error_y + 70),
            wrapped_message,
            font=self._fonts["small"],
            fill=body_color,
        )

        return image

    def render_error(
        self, error_message: str, cached_events: Optional[List[CachedEvent]] = None
    ) -> Image.Image:
        """Render an error message with optional cached events for e-Paper display.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show alongside error

        Returns:
            PIL Image with error display optimized for e-Paper
        """
        logger.debug(f"EInkWhatsNextRenderer.render_error called: {error_message}")

        try:
            width, height = self.capabilities.width, self.capabilities.height

            # Create image in appropriate mode using consistent colors
            if self.capabilities.supports_red:
                mode = "RGB"
                bg_color = convert_to_pil_color(self._colors["background"], mode)
            elif self.capabilities.supports_grayscale:
                mode = "L"
                bg_color = convert_to_pil_color(self._colors["background"], mode)
            else:
                mode = "1"  # Monochrome
                bg_color = convert_to_pil_color(self._colors["background"], mode)

            image = Image.new(mode, (width, height), bg_color)
            draw = ImageDraw.Draw(image)

            y_pos = 20

            # Header with current date
            header_text = datetime.now().strftime("%A, %B %d")
            title_color = convert_to_pil_color(self._colors["text_title"], mode)
            draw.text((20, y_pos), header_text, font=self._fonts["title"], fill=title_color)
            y_pos += 50

            # Error icon and title
            accent_color = convert_to_pil_color(self._colors["accent"], mode)
            draw.text((width // 2 - 20, y_pos), "⚠️", font=self._fonts["title"], fill=accent_color)
            y_pos += 40

            subtitle_color = convert_to_pil_color(self._colors["text_subtitle"], mode)
            draw.text(
                (width // 2 - 80, y_pos),
                "Connection Issue",
                font=self._fonts["subtitle"],
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
            body_color = convert_to_pil_color(self._colors["text_body"], mode)
            draw.text((20, y_pos), wrapped_message, font=self._fonts["body"], fill=body_color)
            y_pos += 60

            # Show cached events if available
            if cached_events:
                subtitle_color = convert_to_pil_color(self._colors["text_subtitle"], mode)
                draw.text(
                    (20, y_pos), "📱 Cached Data", font=self._fonts["subtitle"], fill=subtitle_color
                )
                y_pos += 30

                # Show up to 3 cached events
                for event in cached_events[:3]:
                    if y_pos > height - 60:  # Stop if running out of space
                        break

                    # Event title
                    event_title = (
                        event.subject[:40] + "..." if len(event.subject) > 40 else event.subject
                    )
                    body_color = convert_to_pil_color(self._colors["text_body"], mode)
                    draw.text(
                        (30, y_pos), f"• {event_title}", font=self._fonts["small"], fill=body_color
                    )
                    y_pos += 18

                    # Event time
                    meta_color = convert_to_pil_color(self._colors["text_meta"], mode)
                    draw.text(
                        (35, y_pos),
                        event.format_time_range(),
                        font=self._fonts["small"],
                        fill=meta_color,
                    )
                    y_pos += 25
            else:
                # No cached data message
                meta_color = convert_to_pil_color(self._colors["text_meta"], mode)
                draw.text(
                    (20, y_pos),
                    "❌ No cached data available",
                    font=self._fonts["small"],
                    fill=meta_color,
                )

            return image

        except Exception as e:
            logger.error(f"Error rendering error image: {e}")
            return self._render_error_image(f"Critical error: {e}")

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> Image.Image:
        """Render authentication prompt for device code flow on e-Paper display.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            PIL Image with authentication prompt optimized for e-Paper
        """
        logger.debug(f"EInkWhatsNextRenderer.render_authentication_prompt called")

        try:
            width, height = self.capabilities.width, self.capabilities.height

            # Create image in appropriate mode using consistent colors
            if self.capabilities.supports_red:
                mode = "RGB"
                bg_color = convert_to_pil_color(self._colors["background"], mode)
            elif self.capabilities.supports_grayscale:
                mode = "L"
                bg_color = convert_to_pil_color(self._colors["background"], mode)
            else:
                mode = "1"  # Monochrome
                bg_color = convert_to_pil_color(self._colors["background"], mode)

            image = Image.new(mode, (width, height), bg_color)
            draw = ImageDraw.Draw(image)

            y_pos = 20

            # Header
            title_color = convert_to_pil_color(self._colors["text_title"], mode)
            draw.text(
                (20, y_pos),
                "🔐 Authentication Required",
                font=self._fonts["title"],
                fill=title_color,
            )
            y_pos += 50

            # Subtitle
            subtitle_color = convert_to_pil_color(self._colors["text_subtitle"], mode)
            draw.text(
                (20, y_pos),
                "Microsoft 365 Authentication",
                font=self._fonts["subtitle"],
                fill=subtitle_color,
            )
            y_pos += 40

            # Instructions
            body_color = convert_to_pil_color(self._colors["text_body"], mode)
            draw.text(
                (20, y_pos), "To access your calendar:", font=self._fonts["body"], fill=body_color
            )
            y_pos += 40

            # Step 1
            accent_color = convert_to_pil_color(self._colors["accent"], mode)
            draw.text((20, y_pos), "1. Visit:", font=self._fonts["body"], fill=accent_color)
            y_pos += 25

            # URL (wrap if too long)
            url_text = verification_uri
            if len(url_text) > 35:  # Wrap long URLs
                url_text = url_text[:35] + "..."

            meta_color = convert_to_pil_color(self._colors["text_meta"], mode)
            draw.text((30, y_pos), url_text, font=self._fonts["small"], fill=meta_color)
            y_pos += 40

            # Step 2
            draw.text((20, y_pos), "2. Enter code:", font=self._fonts["body"], fill=accent_color)
            y_pos += 25

            # User code (emphasized)
            title_color = convert_to_pil_color(self._colors["text_title"], mode)
            draw.text((30, y_pos), user_code, font=self._fonts["subtitle"], fill=title_color)
            y_pos += 60

            # Status
            body_color = convert_to_pil_color(self._colors["text_body"], mode)
            draw.text(
                (20, y_pos),
                "Waiting for authentication...",
                font=self._fonts["body"],
                fill=body_color,
            )
            y_pos += 25

            # Loading indicator
            accent_color = convert_to_pil_color(self._colors["accent"], mode)
            draw.text((width // 2 - 10, y_pos), "⏳", font=self._fonts["title"], fill=accent_color)

            return image

        except Exception as e:
            logger.error(f"Error rendering authentication prompt: {e}")
            return self._render_error_image(f"Authentication prompt error: {e}")
