"""Pygame-based framebuffer renderer for CalendarBot display.

This module provides the core rendering engine using pygame to draw
the 3-zone layout directly to the framebuffer without requiring X11.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

import pygame

from framebuffer_ui.config import Config
from framebuffer_ui.layout_engine import LayoutData

logger = logging.getLogger(__name__)

# Color palette (8-shade grayscale matching CSS)
COLORS = {
    "gray-1": (255, 255, 255),  # #ffffff - white
    "gray-2": (247, 247, 247),  # #f7f7f7
    "gray-3": (229, 229, 229),  # #e5e5e5
    "gray-4": (204, 204, 204),  # #cccccc
    "gray-5": (153, 153, 153),  # #999999
    "gray-6": (102, 102, 102),  # #666666
    "gray-7": (51, 51, 51),  # #333333
    "gray-8": (0, 0, 0),  # #000000 - black
}

# Zone heights (480x800 display)
ZONE_1_HEIGHT = 300  # Countdown section
ZONE_2_HEIGHT = 400  # Meeting card
ZONE_3_HEIGHT = 100  # Status message


class FramebufferRenderer:
    """Direct framebuffer rendering using pygame.

    Renders the 3-zone layout to the framebuffer:
    - Zone 1 (0-300px): Countdown timer with large fonts
    - Zone 2 (300-700px): Meeting card with title/time/location
    - Zone 3 (700-800px): Bottom status message

    The renderer matches the HTML/CSS design pixel-perfectly using
    pygame drawing primitives and bundled TTF fonts.
    """

    def __init__(self, config: Config):
        """Initialize pygame renderer.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.width = config.display_width
        self.height = config.display_height

        # Initialize pygame
        self._init_pygame()

        # Load fonts
        self._load_fonts()

        logger.info(
            "Renderer initialized: %dx%d display", self.width, self.height
        )

    def _init_pygame(self) -> None:
        """Initialize pygame with framebuffer backend."""
        # Set SDL environment variables for framebuffer mode
        # These can be overridden by the user if needed
        if "SDL_VIDEODRIVER" not in os.environ or not os.environ.get("SDL_VIDEODRIVER"):
            # Choose appropriate driver based on platform
            system = platform.system()
            if system == "Linux":
                # Raspberry Pi: Use DRM/KMS (modern, hardware-accelerated)
                # Can also use 'fbcon' for legacy framebuffer
                os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
                logger.debug("SDL_VIDEODRIVER not set, using default for Linux: kmsdrm")
            elif system == "Darwin":
                # Mac: Use native Cocoa driver (auto-detect)
                # Don't set SDL_VIDEODRIVER, let pygame auto-detect
                logger.debug("SDL_VIDEODRIVER not set, letting pygame auto-detect for Mac (Cocoa)")
            elif system == "Windows":
                # Windows: Use native Windows driver (auto-detect)
                logger.debug("SDL_VIDEODRIVER not set, letting pygame auto-detect for Windows")
            else:
                # Unknown platform: Let pygame auto-detect
                logger.warning("Unknown platform %s, letting SDL auto-detect driver", system)

        if "SDL_NOMOUSE" not in os.environ:
            os.environ["SDL_NOMOUSE"] = "1"

        # Initialize pygame
        pygame.init()

        # Create display surface
        # Only use fullscreen on Linux (Raspberry Pi framebuffer mode)
        # Mac/Windows use windowed mode for testing
        system = platform.system()
        if system == "Linux":
            # Raspberry Pi: Try fullscreen framebuffer mode
            try:
                self.screen = pygame.display.set_mode(
                    (self.width, self.height), pygame.FULLSCREEN
                )
                logger.info("Framebuffer display created (fullscreen)")
            except pygame.error as e:
                logger.warning(
                    "Failed to create fullscreen display, falling back to windowed: %s",
                    e,
                )
                # Fallback to windowed mode for testing
                self.screen = pygame.display.set_mode((self.width, self.height))
                logger.info("Windowed display created for testing")
        else:
            # Mac/Windows: Use windowed mode for testing
            self.screen = pygame.display.set_mode((self.width, self.height))
            logger.info("Windowed display created for testing (%s)", system)

        pygame.display.set_caption("CalendarBot")

        # Hide mouse cursor
        pygame.mouse.set_visible(False)

    def _load_fonts(self) -> None:
        """Load TTF fonts for rendering.

        Fonts are loaded from the bundled fonts/ directory unless
        a custom font directory is specified in config.
        """
        # Determine font directory
        if self.config.font_dir:
            font_dir = self.config.font_dir
        else:
            # Use bundled fonts
            package_dir = Path(__file__).parent
            font_dir = package_dir / "fonts"

        # Font file paths
        regular_font = font_dir / "DejaVuSans.ttf"
        bold_font = font_dir / "DejaVuSans-Bold.ttf"

        # Verify fonts exist
        if not regular_font.exists():
            raise FileNotFoundError(f"Regular font not found: {regular_font}")
        if not bold_font.exists():
            raise FileNotFoundError(f"Bold font not found: {bold_font}")

        # Load fonts with appropriate sizes (matching CSS)
        self.fonts = {
            "countdown_label": pygame.font.Font(
                str(regular_font), 21
            ),  # 21px, medium
            "countdown_value": pygame.font.Font(
                str(bold_font), 78
            ),  # 78px, bold
            "countdown_units": pygame.font.Font(
                str(regular_font), 18
            ),  # 18px, medium
            "meeting_title": pygame.font.Font(
                str(bold_font), 40
            ),  # 40px, bold
            "meeting_time": pygame.font.Font(
                str(regular_font), 18
            ),  # 18px, medium
            "meeting_location": pygame.font.Font(
                str(regular_font), 14
            ),  # 14px
            "status_message": pygame.font.Font(
                str(regular_font), 32
            ),  # 32px
        }

        logger.debug("Fonts loaded from: %s", font_dir)

    def render(self, layout: LayoutData) -> None:
        """Render complete layout to display.

        Args:
            layout: Layout data for all zones
        """
        # Clear screen
        self.screen.fill(COLORS["gray-2"])

        # Render each zone
        if layout.countdown:
            self._render_countdown_section(layout.countdown)

        if layout.meeting:
            self._render_meeting_section(layout.meeting)

        if layout.status:
            self._render_status_section(layout.status)

        # Update display
        pygame.display.flip()

    def _render_countdown_section(self, countdown: Any) -> None:
        """Render zone 1: Countdown timer (0-300px).

        Args:
            countdown: CountdownDisplay data
        """
        # Background
        pygame.draw.rect(
            self.screen, COLORS["gray-2"], (0, 0, self.width, ZONE_1_HEIGHT)
        )

        # Countdown container (rounded rect)
        container_width = int(self.width * 0.75)  # 75% of screen width
        container_height = 200
        container_x = (self.width - container_width) // 2
        container_y = 50

        container_rect = pygame.Rect(
            container_x, container_y, container_width, container_height
        )

        # Draw container with state-based color
        bg_color = COLORS["gray-3"]
        if countdown.state == "warning":
            bg_color = (255, 250, 205)  # Light yellow
        elif countdown.state == "critical":
            bg_color = (255, 228, 225)  # Light red

        pygame.draw.rect(self.screen, bg_color, container_rect, border_radius=12)
        pygame.draw.rect(
            self.screen,
            COLORS["gray-4"],
            container_rect,
            width=1,
            border_radius=12,
        )

        # "STARTS IN" label
        label_surf = self.fonts["countdown_label"].render(
            countdown.label, True, COLORS["gray-6"]
        )
        label_x = self.width // 2 - label_surf.get_width() // 2
        self.screen.blit(label_surf, (label_x, 70))

        # Large countdown number
        value_surf = self.fonts["countdown_value"].render(
            str(countdown.value), True, COLORS["gray-8"]
        )
        value_x = self.width // 2 - value_surf.get_width() // 2
        self.screen.blit(value_surf, (value_x, 110))

        # Primary units
        units_surf = self.fonts["countdown_units"].render(
            countdown.primary_unit, True, COLORS["gray-6"]
        )
        units_x = self.width // 2 - units_surf.get_width() // 2
        self.screen.blit(units_surf, (units_x, 200))

        # Secondary units (if present)
        if countdown.secondary:
            secondary_surf = self.fonts["countdown_units"].render(
                countdown.secondary, True, COLORS["gray-6"]
            )
            secondary_x = self.width // 2 - secondary_surf.get_width() // 2
            self.screen.blit(secondary_surf, (secondary_x, 220))

    def _render_meeting_section(self, meeting: Any) -> None:
        """Render zone 2: Meeting card (300-700px).

        Args:
            meeting: MeetingDisplay data
        """
        zone_y = ZONE_1_HEIGHT
        zone_height = ZONE_2_HEIGHT

        # Background
        pygame.draw.rect(
            self.screen,
            COLORS["gray-2"],
            (0, zone_y, self.width, zone_height),
        )

        # Meeting card (rounded rect with shadow effect)
        card_margin = 40
        card_width = self.width - (2 * card_margin)
        card_height = 300
        card_x = card_margin
        card_y = zone_y + 50

        card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

        # Draw shadow (simple offset)
        shadow_rect = card_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(
            self.screen,
            COLORS["gray-3"],
            shadow_rect,
            border_radius=8,
        )

        # Draw card
        pygame.draw.rect(
            self.screen, COLORS["gray-1"], card_rect, border_radius=8
        )
        pygame.draw.rect(
            self.screen,
            COLORS["gray-4"],
            card_rect,
            width=1,
            border_radius=8,
        )

        # Meeting title (with word wrap)
        title_lines = self._wrap_text(
            meeting.title, self.fonts["meeting_title"], card_width - 40
        )

        y_offset = card_y + 40
        for line in title_lines[:2]:  # Max 2 lines
            title_surf = self.fonts["meeting_title"].render(
                line, True, COLORS["gray-8"]
            )
            title_x = self.width // 2 - title_surf.get_width() // 2
            self.screen.blit(title_surf, (title_x, y_offset))
            y_offset += 50

        # Meeting time
        if meeting.time:
            time_surf = self.fonts["meeting_time"].render(
                meeting.time, True, COLORS["gray-6"]
            )
            time_x = self.width // 2 - time_surf.get_width() // 2
            self.screen.blit(time_surf, (time_x, y_offset + 10))

        # Meeting location (if present)
        if meeting.location:
            location_surf = self.fonts["meeting_location"].render(
                meeting.location, True, COLORS["gray-5"]
            )
            location_x = self.width // 2 - location_surf.get_width() // 2
            self.screen.blit(location_surf, (location_x, y_offset + 40))

    def _render_status_section(self, status: Any) -> None:
        """Render zone 3: Status message (700-800px).

        Args:
            status: StatusDisplay data
        """
        zone_y = ZONE_1_HEIGHT + ZONE_2_HEIGHT
        zone_height = ZONE_3_HEIGHT

        # Background color based on urgency
        bg_color = COLORS["gray-3"]
        if status.is_critical:
            bg_color = (255, 228, 225)  # Light red
        elif status.is_urgent:
            bg_color = (255, 250, 205)  # Light yellow

        pygame.draw.rect(
            self.screen, bg_color, (0, zone_y, self.width, zone_height)
        )

        # Status message
        text_color = COLORS["gray-7"]
        if status.is_urgent:
            text_color = COLORS["gray-8"]  # Darker for visibility

        status_surf = self.fonts["status_message"].render(
            status.message, True, text_color
        )
        status_x = self.width // 2 - status_surf.get_width() // 2
        status_y = zone_y + (zone_height - status_surf.get_height()) // 2

        self.screen.blit(status_surf, (status_x, status_y))

    def _wrap_text(
        self, text: str, font: pygame.font.Font, max_width: int
    ) -> list[str]:
        """Wrap text to fit within maximum width.

        Args:
            text: Text to wrap
            font: Font to use for rendering
            max_width: Maximum width in pixels

        Returns:
            List of wrapped text lines
        """
        words = text.split()
        lines: list[str] = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " " if current_line else word + " "
            test_surf = font.render(test_line, True, (0, 0, 0))

            if test_surf.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.strip())

        return lines if lines else [text]

    def cleanup(self) -> None:
        """Clean up pygame resources."""
        pygame.quit()
        logger.debug("Renderer cleaned up")
