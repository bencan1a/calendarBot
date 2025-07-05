"""Console-based display renderer for testing and debugging."""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from ..cache.models import CachedEvent

logger = logging.getLogger(__name__)


class ConsoleRenderer:
    """Renders calendar events to console/terminal for testing."""
    
    def __init__(self, settings):
        """Initialize console renderer.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.width = 60  # Console display width
        
        logger.debug("Console renderer initialized")
    
    def render_events(self, events: List[CachedEvent],
                     status_info: Optional[dict] = None) -> str:
        """Render events to formatted console output.
        
        Args:
            events: List of cached events to display
            status_info: Additional status information
            
        Returns:
            Formatted string for console display
        """
        try:
            lines = []
            
            # Determine if we're in interactive mode
            interactive_mode = status_info.get('interactive_mode', False) if status_info else False
            
            # Header - use selected date if in interactive mode
            lines.append("=" * self.width)
            if interactive_mode and status_info.get('selected_date'):
                lines.append(f"📅 MICROSOFT 365 CALENDAR - {status_info['selected_date']}")
            else:
                lines.append(f"📅 MICROSOFT 365 CALENDAR - {datetime.now().strftime('%A, %B %d')}")
            lines.append("=" * self.width)
            
            # Status line
            if status_info:
                status_parts = []
                
                if status_info.get('last_update'):
                    try:
                        if isinstance(status_info['last_update'], str):
                            update_time = datetime.fromisoformat(status_info['last_update'].replace('Z', '+00:00'))
                        else:
                            update_time = status_info['last_update']
                        status_parts.append(f"Updated: {update_time.strftime('%H:%M')}")
                    except:
                        pass
                
                if status_info.get('is_cached'):
                    status_parts.append("📱 Cached Data")
                else:
                    status_parts.append("🌐 Live Data")
                
                if status_info.get('connection_status'):
                    status_parts.append(f"📶 {status_info['connection_status']}")
                
                if status_parts:
                    status_line = " | ".join(status_parts)
                    lines.append(status_line)
                    lines.append("-" * self.width)
            
            # Interactive navigation help
            if interactive_mode:
                lines.append(self._render_navigation_help(status_info))
                lines.append("-" * self.width)
            
            # No events case
            if not events:
                lines.append("")
                lines.append("🎉 No meetings scheduled for today!")
                lines.append("")
                lines.append("=" * self.width)
                return "\n".join(lines)
            
            # Group events
            current_events = [e for e in events if e.is_current()]
            upcoming_events = [e for e in events if e.is_upcoming()]
            
            # Current event section
            if current_events:
                lines.append("")
                lines.append("▶ CURRENT EVENT")
                lines.append("")
                
                for event in current_events[:1]:  # Show only one current event
                    lines.extend(self._format_current_event(event))
            
            # Upcoming events section
            if upcoming_events:
                lines.append("")
                lines.append("📋 NEXT UP")
                lines.append("")
                
                for event in upcoming_events[:3]:  # Show next 3 events
                    lines.extend(self._format_upcoming_event(event))
            
            # Later today section
            later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []
            if later_events:
                lines.append("")
                lines.append("⏰ LATER TODAY")
                lines.append("")
                
                for event in later_events[:5]:  # Show up to 5 more events
                    lines.append(f"• {self._truncate_text(event.subject, 45)}")
                    lines.append(f"  {event.format_time_range()}")
            
            lines.append("")
            lines.append("=" * self.width)
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to render events: {e}")
            return f"Error rendering calendar: {e}"
    
    def _format_current_event(self, event: CachedEvent) -> List[str]:
        """Format a current event for display.
        
        Args:
            event: Current event to format
            
        Returns:
            List of lines for the event
        """
        lines = []
        
        # Event title
        lines.append(f"  {self._truncate_text(event.subject, 50)}")
        
        # Time and duration
        duration_mins = (event.end_dt - event.start_dt).total_seconds() / 60
        time_info = f"  {event.format_time_range()}"
        if duration_mins > 0:
            time_info += f" ({int(duration_mins)}min)"
        lines.append(time_info)
        
        # Location
        if event.location_display_name:
            location = self._truncate_text(event.location_display_name, 45)
            lines.append(f"  📍 {location}")
        elif event.is_online_meeting:
            lines.append("  💻 Online Meeting")
        
        # Time remaining
        from ..utils.helpers import get_timezone_aware_now
        now = get_timezone_aware_now()
        time_left = (event.end_dt - now).total_seconds() / 60
        if time_left > 0:
            lines.append(f"  ⏱️  {int(time_left)} minutes remaining")
        
        return lines
    
    def _format_upcoming_event(self, event: CachedEvent) -> List[str]:
        """Format an upcoming event for display.
        
        Args:
            event: Upcoming event to format
            
        Returns:
            List of lines for the event
        """
        lines = []
        
        # Event title with bullet
        lines.append(f"• {self._truncate_text(event.subject, 50)}")
        
        # Time and location
        time_info = f"  {event.format_time_range()}"
        
        if event.location_display_name:
            location = self._truncate_text(event.location_display_name, 30)
            time_info += f" | 📍 {location}"
        elif event.is_online_meeting:
            time_info += " | 💻 Online"
        
        lines.append(time_info)
        
        # Time until start
        time_until = event.time_until_start()
        if time_until is not None and time_until <= 60:  # Show if within 1 hour
            if time_until <= 5:
                lines.append(f"  🔔 Starting in {time_until} minutes!")
            else:
                lines.append(f"  ⏰ In {time_until} minutes")
        
        lines.append("")  # Empty line between events
        
        return lines
    
    def _render_navigation_help(self, status_info: Dict[str, Any]) -> str:
        """Render navigation help text for interactive mode.
        
        Args:
            status_info: Status information containing navigation details
            
        Returns:
            Formatted navigation help string
        """
        help_parts = []
        
        # Navigation controls
        help_parts.append("← → Navigate")
        help_parts.append("Space: Today")
        help_parts.append("ESC: Exit")
        
        # Additional controls if available
        if status_info.get('navigation_help'):
            custom_help = status_info['navigation_help']
            if "Home:" in custom_help:
                help_parts.append("Home: Week Start")
            if "End:" in custom_help:
                help_parts.append("End: Week End")
        
        help_text = " | ".join(help_parts)
        
        # Add relative date info if available
        if status_info.get('relative_description'):
            relative = status_info['relative_description']
            if relative != "Today":
                help_text = f"📍 {relative} | {help_text}"
        
        return help_text
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to fit within specified length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length allowed
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."
    
    def render_error(self, error_message: str, 
                    cached_events: Optional[List[CachedEvent]] = None) -> str:
        """Render an error message with optional cached events.
        
        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show alongside error
            
        Returns:
            Formatted error display
        """
        try:
            lines = []
            
            # Header
            lines.append("=" * self.width)
            lines.append(f"📅 MICROSOFT 365 CALENDAR - {datetime.now().strftime('%A, %B %d')}")
            lines.append("=" * self.width)
            
            # Error message
            lines.append("")
            lines.append("⚠️  CONNECTION ISSUE")
            lines.append("")
            lines.append(f"   {error_message}")
            lines.append("")
            
            # Show cached events if available
            if cached_events:
                lines.append("📱 SHOWING CACHED DATA")
                lines.append("-" * self.width)
                
                # Render cached events (simplified)
                for event in cached_events[:5]:
                    lines.append(f"• {self._truncate_text(event.subject, 45)}")
                    lines.append(f"  {event.format_time_range()}")
                    if event.location_display_name:
                        location = self._truncate_text(event.location_display_name, 40)
                        lines.append(f"  📍 {location}")
                    lines.append("")
            else:
                lines.append("❌ No cached data available")
                lines.append("")
            
            lines.append("=" * self.width)
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to render error: {e}")
            return f"Critical error: {e}"
    
    def render_authentication_prompt(self, verification_uri: str, 
                                   user_code: str) -> str:
        """Render authentication prompt for device code flow.
        
        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter
            
        Returns:
            Formatted authentication prompt
        """
        lines = []
        
        lines.append("=" * self.width)
        lines.append("🔐 MICROSOFT 365 AUTHENTICATION REQUIRED")
        lines.append("=" * self.width)
        lines.append("")
        lines.append("To access your calendar, please complete authentication:")
        lines.append("")
        lines.append(f"1. Visit: {verification_uri}")
        lines.append(f"2. Enter code: {user_code}")
        lines.append("")
        lines.append("Waiting for authentication...")
        lines.append("")
        lines.append("=" * self.width)
        
        return "\n".join(lines)
    
    def clear_screen(self):
        """Clear the console screen."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def display_with_clear(self, content: str):
        """Display content after clearing screen.
        
        Args:
            content: Content to display
        """
        self.clear_screen()
        print(content)
        print()  # Extra newline for spacing