"""HTML-based display renderer for web interface and e-ink testing."""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import pytz
from ..cache.models import CachedEvent

logger = logging.getLogger(__name__)


class HTMLRenderer:
    """Renders calendar events to HTML for web display and e-ink testing."""
    
    def __init__(self, settings):
        """Initialize HTML renderer.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.theme = getattr(settings, 'web_theme', 'eink')
        
        logger.info(f"HTML renderer initialized with theme: {self.theme}")
    
    def render_events(self, events: List[CachedEvent],
                     status_info: Optional[dict] = None) -> str:
        """Render events to formatted HTML output.
        
        Args:
            events: List of cached events to display
            status_info: Additional status information
            
        Returns:
            Formatted HTML string for web display
        """
        try:
            # Determine if we're in interactive mode
            interactive_mode = status_info.get('interactive_mode', False) if status_info else False
            
            # Get date information
            if interactive_mode and status_info.get('selected_date'):
                display_date = status_info['selected_date']
            else:
                display_date = datetime.now().strftime('%A, %B %d')
            
            # Build status line
            status_line = self._build_status_line(status_info)
            
            # Generate events content
            events_content = self._render_events_content(events, interactive_mode)
            
            # Generate navigation help if interactive
            nav_help = ""
            if interactive_mode:
                nav_help = self._render_navigation_help(status_info)
            
            # Build complete HTML
            html_content = self._build_html_template(
                display_date=display_date,
                status_line=status_line,
                events_content=events_content,
                nav_help=nav_help,
                interactive_mode=interactive_mode
            )
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to render events to HTML: {e}")
            return self._render_error_html(f"Error rendering calendar: {e}")
    
    def _build_status_line(self, status_info: Optional[dict]) -> str:
        """Build status information line.
        
        Args:
            status_info: Status information dictionary
            
        Returns:
            HTML status line
        """
        if not status_info:
            return ""
        
        status_parts = []
        
        # Last update time
        if status_info.get('last_update'):
            try:
                if isinstance(status_info['last_update'], str):
                    update_time = datetime.fromisoformat(status_info['last_update'].replace('Z', '+00:00'))
                else:
                    update_time = status_info['last_update']
                
                # Convert to Pacific timezone (GMT-8/PDT)
                pacific_tz = pytz.timezone('US/Pacific')
                if update_time.tzinfo is None:
                    update_time_utc = pytz.utc.localize(update_time)
                else:
                    update_time_utc = update_time.astimezone(pytz.utc)
                
                update_time_pacific = update_time_utc.astimezone(pacific_tz)
                status_parts.append(f"Updated: {update_time_pacific.strftime('%I:%M %p')}")
            except:
                pass
        
        # Data source indicator
        if status_info.get('is_cached'):
            status_parts.append('<span class="status-cached">📱 Cached Data</span>')
        else:
            status_parts.append('<span class="status-live">🌐 Live Data</span>')
        
        # Connection status
        if status_info.get('connection_status'):
            status_parts.append(f'📶 {status_info["connection_status"]}')
        
        return ' | '.join(status_parts) if status_parts else ""
    
    def _render_events_content(self, events: List[CachedEvent], interactive_mode: bool) -> str:
        """Render the main events content.
        
        Args:
            events: List of events to render
            interactive_mode: Whether in interactive mode
            
        Returns:
            HTML content for events
        """
        if not events:
            return '''
            <div class="no-events">
                <div class="no-events-icon">🎉</div>
                <h2>No meetings scheduled!</h2>
                <p>Enjoy your free time.</p>
            </div>
            '''
        
        content_parts = []
        
        # Group events
        current_events = [e for e in events if e.is_current()]
        upcoming_events = [e for e in events if e.is_upcoming()]
        
        # Current event section
        if current_events:
            content_parts.append('<section class="current-events">')
            content_parts.append('<h2 class="section-title">▶ Current Event</h2>')
            
            for event in current_events[:1]:  # Show only one current event
                content_parts.append(self._format_current_event_html(event))
            
            content_parts.append('</section>')
        
        # Upcoming events section
        if upcoming_events:
            content_parts.append('<section class="upcoming-events">')
            content_parts.append('<h2 class="section-title">📋 Next Up</h2>')
            
            for event in upcoming_events[:3]:  # Show next 3 events
                content_parts.append(self._format_upcoming_event_html(event))
            
            content_parts.append('</section>')
        
        # Later today section
        later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []
        if later_events:
            content_parts.append('<section class="later-events">')
            content_parts.append('<h2 class="section-title">⏰ Later Today</h2>')
            content_parts.append('<ul class="later-events-list">')
            
            for event in later_events[:5]:  # Show up to 5 more events
                # Location information - filter out Microsoft Teams Meeting text
                location_text = ""
                if event.location_display_name and "Microsoft Teams Meeting" not in event.location_display_name:
                    location_text = f' | 📍 {self._escape_html(event.location_display_name)}'
                elif event.is_online_meeting:
                    location_text = ' | 💻 Online'
                
                content_parts.append(f'''
                <li class="later-event">
                    <span class="event-title">{self._escape_html(event.subject)}</span>
                    <span class="event-time">{event.format_time_range()}{location_text}</span>
                </li>
                ''')
            
            content_parts.append('</ul>')
            content_parts.append('</section>')
        
        return '\n'.join(content_parts)
    
    def _format_current_event_html(self, event: CachedEvent) -> str:
        """Format a current event for HTML display.
        
        Args:
            event: Current event to format
            
        Returns:
            HTML string for the event
        """
        # Calculate duration
        duration_mins = (event.end_dt - event.start_dt).total_seconds() / 60
        duration_text = f" ({int(duration_mins)}min)" if duration_mins > 0 else ""
        
        # Location information - filter out Microsoft Teams Meeting text
        location_html = ""
        if event.location_display_name and "Microsoft Teams Meeting" not in event.location_display_name:
            location_html = f'<div class="event-location">📍 {self._escape_html(event.location_display_name)}</div>'
        elif event.is_online_meeting:
            location_html = '<div class="event-location online">💻 Online Meeting</div>'
        
        # Time remaining
        time_remaining_html = ""
        try:
            from ..utils.helpers import get_timezone_aware_now
            now = get_timezone_aware_now()
            time_left = (event.end_dt - now).total_seconds() / 60
            if time_left > 0:
                time_remaining_html = f'<div class="time-remaining">⏱️ {int(time_left)} minutes remaining</div>'
        except:
            pass
        
        return f'''
        <div class="current-event">
            <h3 class="event-title">{self._escape_html(event.subject)}</h3>
            <div class="event-time">{event.format_time_range()}{duration_text}</div>
            {location_html}
            {time_remaining_html}
        </div>
        '''
    
    def _format_upcoming_event_html(self, event: CachedEvent) -> str:
        """Format an upcoming event for HTML display.
        
        Args:
            event: Upcoming event to format
            
        Returns:
            HTML string for the event
        """
        # Location information - filter out Microsoft Teams Meeting text
        location_html = ""
        if event.location_display_name and "Microsoft Teams Meeting" not in event.location_display_name:
            location_html = f' | 📍 {self._escape_html(event.location_display_name)}'
        elif event.is_online_meeting:
            location_html = ' | 💻 Online'
        
        # Time until start
        time_until_html = ""
        time_until = event.time_until_start()
        if time_until is not None and time_until <= 60:  # Show if within 1 hour
            if time_until <= 5:
                time_until_html = f'<div class="time-until urgent">🔔 Starting in {time_until} minutes!</div>'
            else:
                time_until_html = f'<div class="time-until">⏰ In {time_until} minutes</div>'
        
        return f'''
        <div class="upcoming-event">
            <h4 class="event-title">{self._escape_html(event.subject)}</h4>
            <div class="event-details">{event.format_time_range()}{location_html}</div>
            {time_until_html}
        </div>
        '''
    
    def _render_navigation_help(self, status_info: Dict[str, Any]) -> str:
        """Render navigation help for interactive mode.
        
        Args:
            status_info: Status information containing navigation details
            
        Returns:
            HTML navigation help content
        """
        help_parts = [
            '<span class="nav-key">← →</span> Navigate',
            '<span class="nav-key">Space</span> Today',
            '<span class="nav-key">Home/End</span> Week',
            '<span class="nav-key">R</span> Refresh'
        ]
        
        # Add relative date info if available
        relative_info = ""
        if status_info.get('relative_description'):
            relative = status_info['relative_description']
            if relative != "Today":
                relative_info = f'<span class="relative-date">📍 {relative}</span> | '
        
        return f'''
        <div class="navigation-help">
            {relative_info}
            {' | '.join(help_parts)}
        </div>
        '''
    
    def _build_html_template(self, display_date: str, status_line: str,
                           events_content: str, nav_help: str, interactive_mode: bool) -> str:
        """Build the complete HTML template.
        
        Args:
            display_date: Formatted date string
            status_line: Status information HTML
            events_content: Main events content HTML
            nav_help: Navigation help HTML
            interactive_mode: Whether in interactive mode
            
        Returns:
            Complete HTML document
        """
        # Dynamic theme resource loading
        css_file = self._get_theme_css_file()
        js_file = self._get_theme_js_file()
        
        logger.info(f"HTML template using theme '{self.theme}' - CSS: {css_file}, JS: {js_file}")
        
        # Header navigation with arrow buttons and date
        header_navigation = ""
        if interactive_mode:
            header_navigation = f'''
            <div class="header-navigation">
                <button onclick="navigate('prev')" title="Previous Day" class="nav-arrow-left">←</button>
                <div class="header-date">{display_date}</div>
                <button onclick="navigate('next')" title="Next Day" class="nav-arrow-right">→</button>
            </div>
            '''
        else:
            header_navigation = f'''
            <div class="header-navigation">
                <div class="nav-arrow-left"></div>
                <div class="header-date">{display_date}</div>
                <div class="nav-arrow-right"></div>
            </div>
            '''
        
        # Footer navigation help
        footer_content = ""
        if interactive_mode and nav_help:
            footer_content = f'<footer class="footer">{nav_help}</footer>'
        
        return f'''<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>📅 Calendar Bot - {display_date}</title>
    <link rel="stylesheet" href="/static/{css_file}">
</head>
<body>
    <header class="calendar-header">
        {header_navigation}
        
        <div class="status-line">{status_line}</div>
    </header>
    
    <main class="calendar-content">
        {events_content}
    </main>
    
    {footer_content}
    
    <script src="/static/{js_file}"></script>
</body>
</html>'''
    
    def _get_theme_css_file(self) -> str:
        """Get the CSS file name for the current theme.
        
        Returns:
            CSS filename (e.g., 'style.css', 'eink-rpi.css')
        """
        if self.theme == "eink-rpi":
            return "eink-rpi.css"
        elif self.theme == "standard":
            return "standard.css"  # If standard theme exists
        else:  # Default to "eink" theme
            return "style.css"
    
    def _get_theme_js_file(self) -> str:
        """Get the JavaScript file name for the current theme.
        
        Returns:
            JavaScript filename (e.g., 'app.js', 'eink-rpi.js')
        """
        if self.theme == "eink-rpi":
            return "eink-rpi.js"
        elif self.theme == "standard":
            return "standard.js"  # If standard theme exists
        else:  # Default to "eink" theme
            return "app.js"
    
    def _get_theme_icon(self) -> str:
        """Get appropriate icon for current theme."""
        return "🎨" if self.theme == "eink" else "⚫"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            HTML-escaped text
        """
        if not text:
            return ""
        
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#x27;"))
    
    def render_error(self, error_message: str, 
                    cached_events: Optional[List[CachedEvent]] = None) -> str:
        """Render an error message with optional cached events.
        
        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show alongside error
            
        Returns:
            Formatted HTML error display
        """
        try:
            return self._render_error_html(error_message, cached_events)
        except Exception as e:
            logger.error(f"Failed to render error HTML: {e}")
            return f"<html><body><h1>Critical Error</h1><p>{self._escape_html(str(e))}</p></body></html>"
    
    def _render_error_html(self, error_message: str, 
                          cached_events: Optional[List[CachedEvent]] = None) -> str:
        """Render error HTML content.
        
        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show
            
        Returns:
            HTML error content
        """
        cached_content = ""
        if cached_events:
            cached_items = []
            for event in cached_events[:5]:
                location = ""
                if event.location_display_name:
                    location = f" | 📍 {self._escape_html(event.location_display_name)}"
                
                cached_items.append(f'''
                <li class="cached-event">
                    <span class="event-title">{self._escape_html(event.subject)}</span>
                    <span class="event-details">{event.format_time_range()}{location}</span>
                </li>
                ''')
            
            cached_content = f'''
            <section class="cached-data">
                <h2>📱 Showing Cached Data</h2>
                <ul class="cached-events-list">
                    {''.join(cached_items)}
                </ul>
            </section>
            '''
        else:
            cached_content = '<div class="no-cache">❌ No cached data available</div>'
        
        return f'''<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>📅 Calendar Bot - Connection Issue</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header class="calendar-header">
        <h1 class="calendar-title">📅 Microsoft 365 Calendar - {datetime.now().strftime('%A, %B %d')}</h1>
    </header>
    
    <main class="calendar-content">
        <section class="error-section">
            <div class="error-icon">⚠️</div>
            <h2 class="error-title">Connection Issue</h2>
            <p class="error-message">{self._escape_html(error_message)}</p>
        </section>
        
        {cached_content}
    </main>
    
    <script src="/static/app.js"></script>
</body>
</html>'''
    
    def render_authentication_prompt(self, verification_uri: str, 
                                   user_code: str) -> str:
        """Render authentication prompt for device code flow.
        
        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter
            
        Returns:
            Formatted HTML authentication prompt
        """
        return f'''<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>📅 Calendar Bot - Authentication Required</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header class="calendar-header">
        <h1 class="calendar-title">🔐 Authentication Required</h1>
    </header>
    
    <main class="calendar-content">
        <section class="auth-section">
            <h2>Microsoft 365 Authentication</h2>
            <p>To access your calendar, please complete authentication:</p>
            
            <div class="auth-steps">
                <div class="auth-step">
                    <span class="step-number">1.</span>
                    <span class="step-text">Visit: <a href="{verification_uri}" target="_blank">{verification_uri}</a></span>
                </div>
                <div class="auth-step">
                    <span class="step-number">2.</span>
                    <span class="step-text">Enter code: <code class="user-code">{user_code}</code></span>
                </div>
            </div>
            
            <div class="auth-status">
                <p>Waiting for authentication...</p>
                <div class="loading-spinner">⏳</div>
            </div>
        </section>
    </main>
</body>
</html>'''