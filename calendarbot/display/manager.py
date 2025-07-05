"""Display manager coordinating between data and rendering."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..cache.models import CachedEvent
from .console_renderer import ConsoleRenderer

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages display output and coordination between data and renderers."""
    
    def __init__(self, settings):
        """Initialize display manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.renderer = None
        
        # Initialize appropriate renderer based on settings
        if settings.display_type == "console":
            self.renderer = ConsoleRenderer(settings)
        else:
            logger.warning(f"Unknown display type: {settings.display_type}, defaulting to console")
            self.renderer = ConsoleRenderer(settings)
        
        logger.info(f"Display manager initialized with {settings.display_type} renderer")
    
    async def display_events(self, events: List[CachedEvent], 
                           status_info: Optional[Dict[str, Any]] = None,
                           clear_screen: bool = True) -> bool:
        """Display calendar events using the configured renderer.
        
        Args:
            events: List of cached events to display
            status_info: Additional status information
            clear_screen: Whether to clear screen before displaying
            
        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True
            
            # Prepare status information
            display_status = status_info or {}
            display_status['last_update'] = datetime.now().isoformat()
            
            # Render events
            content = self.renderer.render_events(events, display_status)
            
            # Display content
            if clear_screen and hasattr(self.renderer, 'display_with_clear'):
                self.renderer.display_with_clear(content)
            else:
                print(content)
            
            logger.debug(f"Displayed {len(events)} events successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to display events: {e}")
            return False
    
    async def display_error(self, error_message: str, 
                          cached_events: Optional[List[CachedEvent]] = None,
                          clear_screen: bool = True) -> bool:
        """Display error message with optional cached events.
        
        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show
            clear_screen: Whether to clear screen before displaying
            
        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True
            
            content = self.renderer.render_error(error_message, cached_events)
            
            # Display content
            if clear_screen and hasattr(self.renderer, 'display_with_clear'):
                self.renderer.display_with_clear(content)
            else:
                print(content)
            
            logger.debug("Displayed error message successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to display error: {e}")
            return False
    
    async def display_authentication_prompt(self, verification_uri: str, 
                                          user_code: str,
                                          clear_screen: bool = True) -> bool:
        """Display authentication prompt for device code flow.
        
        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter
            clear_screen: Whether to clear screen before displaying
            
        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True
            
            content = self.renderer.render_authentication_prompt(verification_uri, user_code)
            
            # Display content
            if clear_screen and hasattr(self.renderer, 'display_with_clear'):
                self.renderer.display_with_clear(content)
            else:
                print(content)
            
            logger.debug("Displayed authentication prompt successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to display authentication prompt: {e}")
            return False
    
    async def display_status(self, status_info: Dict[str, Any],
                           clear_screen: bool = True) -> bool:
        """Display system status information.
        
        Args:
            status_info: Status information to display
            clear_screen: Whether to clear screen before displaying
            
        Returns:
            True if display was successful, False otherwise
        """
        try:
            if not self.settings.display_enabled:
                logger.debug("Display disabled in settings")
                return True
            
            lines = []
            lines.append("=" * 60)
            lines.append("📊 CALENDAR BOT STATUS")
            lines.append("=" * 60)
            lines.append("")
            
            for key, value in status_info.items():
                # Format key for display
                display_key = key.replace('_', ' ').title()
                lines.append(f"{display_key}: {value}")
            
            lines.append("")
            lines.append("=" * 60)
            
            content = "\n".join(lines)
            
            # Display content
            if clear_screen and hasattr(self.renderer, 'display_with_clear'):
                self.renderer.display_with_clear(content)
            else:
                print(content)
            
            logger.debug("Displayed status information successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to display status: {e}")
            return False
    
    def clear_display(self):
        """Clear the display."""
        try:
            if hasattr(self.renderer, 'clear_screen'):
                self.renderer.clear_screen()
            else:
                import os
                os.system('clear' if os.name == 'posix' else 'cls')
                
        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
    
    def get_renderer_info(self) -> Dict[str, Any]:
        """Get information about the current renderer.
        
        Returns:
            Dictionary with renderer information
        """
        return {
            "type": self.settings.display_type,
            "enabled": self.settings.display_enabled,
            "renderer_class": self.renderer.__class__.__name__ if self.renderer else None
        }