"""Raspberry Pi e-ink HTML renderer for 800x480px displays."""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from .html_renderer import HTMLRenderer
from ..cache.models import CachedEvent

logger = logging.getLogger(__name__)


class RaspberryPiHTMLRenderer(HTMLRenderer):
    """HTML renderer optimized for Raspberry Pi e-ink displays (800x480px).
    
    Extends the base HTMLRenderer with RPI-specific layout and components:
    - CSS Grid layout with header, content, and navigation areas
    - Bottom navigation bar with previous/next day buttons and centered date display
    - Component-based event cards optimized for e-ink contrast
    - Touch-friendly navigation elements
    - Fixed 800x480 viewport dimensions
    """
    
    def __init__(self, settings):
        """Initialize RPI HTML renderer.
        
        Args:
            settings: Application settings
        """
        super().__init__(settings)
        # Override theme for RPI e-ink display
        self.theme = 'eink-rpi'
        
        logger.debug("RPI HTML renderer initialized for 800x480px e-ink display")
    
    def _build_html_template(self, display_date: str, status_line: str, 
                           events_content: str, nav_help: str, interactive_mode: bool) -> str:
        """Build the complete HTML template optimized for RPI e-ink display.
        
        Args:
            display_date: Formatted date string
            status_line: Status information HTML
            events_content: Main events content HTML
            nav_help: Navigation help HTML (unused in RPI layout)
            interactive_mode: Whether in interactive mode
            
        Returns:
            Complete HTML document with RPI e-ink layout
        """
        # Generate navigation controls for header
        header_nav_controls = self._generate_header_navigation(interactive_mode)
        
        # Generate bottom navigation bar
        bottom_navigation = self._generate_bottom_navigation(display_date, interactive_mode)
        
        # Theme toggle for header
        theme_toggle = self._generate_theme_toggle()
        
        return f'''<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=800, height=480, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - {display_date}</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            {header_nav_controls}
            
            <div class="header-main">
                <h1 class="calendar-title">📅 Calendar</h1>
                {self._render_status_line_html(status_line)}
            </div>
            
            {theme_toggle}
        </header>
        
        <main class="calendar-content">
            {events_content}
        </main>
        
        {bottom_navigation}
    </div>
    
    <script src="/static/app.js"></script>
    <script src="/static/eink-rpi.js"></script>
</body>
</html>'''
    
    def _generate_header_navigation(self, interactive_mode: bool) -> str:
        """Generate header navigation controls for RPI layout.
        
        Args:
            interactive_mode: Whether in interactive mode
            
        Returns:
            HTML for header navigation controls
        """
        if not interactive_mode:
            return '<div class="nav-controls"></div>'
        
        return '''
        <div class="nav-controls">
            <button onclick="navigate('today')" class="btn-base btn-navigation" 
                    title="Jump to Today" aria-label="Jump to Today">
                📅
            </button>
        </div>
        '''
    
    def _generate_bottom_navigation(self, display_date: str, interactive_mode: bool) -> str:
        """Generate bottom navigation bar for RPI layout.
        
        Args:
            display_date: Current display date string
            interactive_mode: Whether in interactive mode
            
        Returns:
            HTML for bottom navigation bar
        """
        if not interactive_mode:
            # Static display without navigation
            return f'''
            <nav class="calendar-navigation">
                <div class="nav-prev"></div>
                <div class="nav-date-display">{display_date}</div>
                <div class="nav-next"></div>
            </nav>
            '''
        
        return f'''
        <nav class="calendar-navigation">
            <button onclick="navigate('prev')" class="btn-base btn-navigation nav-prev" 
                    title="Previous Day" aria-label="Previous Day">
                ‹
            </button>
            
            <div class="nav-date-display" role="status" aria-live="polite">
                {display_date}
            </div>
            
            <button onclick="navigate('next')" class="btn-base btn-navigation nav-next" 
                    title="Next Day" aria-label="Next Day">
                ›
            </button>
        </nav>
        '''
    
    def _generate_theme_toggle(self) -> str:
        """Generate theme toggle button for header.
        
        Returns:
            HTML for theme toggle button
        """
        return '''
        <div class="theme-controls">
            <button onclick="toggleTheme()" class="theme-toggle" 
                    title="Toggle Theme" aria-label="Toggle Theme">
                🎨
            </button>
        </div>
        '''
    
    def _render_status_line_html(self, status_line: str) -> str:
        """Render status line with appropriate styling for RPI layout.
        
        Args:
            status_line: Status information HTML
            
        Returns:
            Formatted status line HTML
        """
        if not status_line:
            return ""
        
        return f'<div class="status-line">{status_line}</div>'
    
    def _render_events_content(self, events: List[CachedEvent], interactive_mode: bool) -> str:
        """Render events content optimized for RPI e-ink display.
        
        Args:
            events: List of events to render
            interactive_mode: Whether in interactive mode
            
        Returns:
            HTML content for events using component-based structure
        """
        if not events:
            return self._render_no_events_rpi()
        
        content_parts = []
        
        # Group events
        current_events = [e for e in events if e.is_current()]
        upcoming_events = [e for e in events if e.is_upcoming()]
        
        # Current event section
        if current_events:
            content_parts.append(self._render_current_events_section_rpi(current_events))
        
        # Upcoming events section
        if upcoming_events:
            content_parts.append(self._render_upcoming_events_section_rpi(upcoming_events))
        
        # Later events section (compact list)
        later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []
        if later_events:
            content_parts.append(self._render_later_events_section_rpi(later_events))
        
        return '\n'.join(content_parts)
    
    def _render_no_events_rpi(self) -> str:
        """Render no events state for RPI display.
        
        Returns:
            HTML for no events state
        """
        return '''
        <div class="no-events">
            <div class="no-events-icon">🎉</div>
            <h2>No meetings scheduled!</h2>
            <p>Enjoy your free time.</p>
        </div>
        '''
    
    def _render_current_events_section_rpi(self, current_events: List[CachedEvent]) -> str:
        """Render current events section with RPI component styling.
        
        Args:
            current_events: List of current events
            
        Returns:
            HTML for current events section
        """
        section_parts = [
            '<section class="current-events">',
            '<h2 class="section-title">▶ Current Event</h2>'
        ]
        
        # Show only the first current event for RPI layout
        event = current_events[0]
        section_parts.append(self._format_current_event_rpi(event))
        
        section_parts.append('</section>')
        return '\n'.join(section_parts)
    
    def _render_upcoming_events_section_rpi(self, upcoming_events: List[CachedEvent]) -> str:
        """Render upcoming events section with RPI component styling.
        
        Args:
            upcoming_events: List of upcoming events
            
        Returns:
            HTML for upcoming events section
        """
        section_parts = [
            '<section class="upcoming-events">',
            '<h2 class="section-title">📋 Next Up</h2>'
        ]
        
        # Show next 3 events for RPI layout
        for event in upcoming_events[:3]:
            section_parts.append(self._format_upcoming_event_rpi(event))
        
        section_parts.append('</section>')
        return '\n'.join(section_parts)
    
    def _render_later_events_section_rpi(self, later_events: List[CachedEvent]) -> str:
        """Render later events section as compact list for RPI display.
        
        Args:
            later_events: List of later events
            
        Returns:
            HTML for later events section
        """
        section_parts = [
            '<section class="later-events">',
            '<h2 class="section-title">⏰ Later Today</h2>',
            '<ul class="later-events-list">'
        ]
        
        # Show up to 5 later events in compact format
        for event in later_events[:5]:
            section_parts.append(f'''
            <li class="later-event">
                <span class="event-title">{self._escape_html(event.subject)}</span>
                <span class="event-time">{event.format_time_range()}</span>
            </li>
            ''')
        
        section_parts.extend(['</ul>', '</section>'])
        return '\n'.join(section_parts)
    
    def _format_current_event_rpi(self, event: CachedEvent) -> str:
        """Format current event with RPI component styling.
        
        Args:
            event: Current event to format
            
        Returns:
            HTML string for the current event card
        """
        # Calculate duration
        duration_mins = (event.end_dt - event.start_dt).total_seconds() / 60
        duration_text = f" ({int(duration_mins)}min)" if duration_mins > 0 else ""
        
        # Location information
        location_html = self._format_event_location_rpi(event)
        
        # Time remaining
        time_remaining_html = self._format_time_remaining_rpi(event)
        
        return f'''
        <div class="current-event card-current" data-event-id="{event.id}" 
             role="article" aria-label="Current Event">
            <h3 class="event-title">{self._escape_html(event.subject)}</h3>
            <div class="event-time">{event.format_time_range()}{duration_text}</div>
            {location_html}
            {time_remaining_html}
        </div>
        '''
    
    def _format_upcoming_event_rpi(self, event: CachedEvent) -> str:
        """Format upcoming event with RPI component styling.
        
        Args:
            event: Upcoming event to format
            
        Returns:
            HTML string for the upcoming event card
        """
        # Location information
        location_text = ""
        if event.location_display_name:
            location_text = f' | 📍 {self._escape_html(event.location_display_name)}'
        elif event.is_online_meeting:
            location_text = ' | 💻 Online'
        
        # Time until start
        time_until_html = self._format_time_until_rpi(event)
        
        return f'''
        <div class="upcoming-event card-upcoming" data-event-id="{event.id}" 
             role="article" aria-label="Upcoming Event">
            <h4 class="event-title">{self._escape_html(event.subject)}</h4>
            <div class="event-details">{event.format_time_range()}{location_text}</div>
            {time_until_html}
        </div>
        '''
    
    def _format_event_location_rpi(self, event: CachedEvent) -> str:
        """Format event location for RPI display.
        
        Args:
            event: Event with location information
            
        Returns:
            HTML for event location
        """
        if event.location_display_name:
            return f'<div class="event-location">📍 {self._escape_html(event.location_display_name)}</div>'
        elif event.is_online_meeting:
            return '<div class="event-location online">💻 Online Meeting</div>'
        return ""
    
    def _format_time_remaining_rpi(self, event: CachedEvent) -> str:
        """Format time remaining for current event in RPI display.
        
        Args:
            event: Current event
            
        Returns:
            HTML for time remaining
        """
        try:
            from ..utils.helpers import get_timezone_aware_now
            now = get_timezone_aware_now()
            time_left = (event.end_dt - now).total_seconds() / 60
            if time_left > 0:
                return f'<div class="time-remaining">⏱️ {int(time_left)} minutes remaining</div>'
        except Exception:
            pass
        return ""
    
    def _format_time_until_rpi(self, event: CachedEvent) -> str:
        """Format time until start for upcoming event in RPI display.
        
        Args:
            event: Upcoming event
            
        Returns:
            HTML for time until start
        """
        time_until = event.time_until_start()
        if time_until is not None and time_until <= 60:  # Show if within 1 hour
            if time_until <= 5:
                return f'<div class="time-until urgent">🔔 Starting in {time_until} minutes!</div>'
            else:
                return f'<div class="time-until">⏰ In {time_until} minutes</div>'
        return ""
    
    def _render_error_html(self, error_message: str, 
                          cached_events: Optional[List[CachedEvent]] = None) -> str:
        """Render error HTML content for RPI display.
        
        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show
            
        Returns:
            HTML error content with RPI layout
        """
        cached_content = ""
        if cached_events:
            cached_items = []
            for event in cached_events[:3]:  # Limit for RPI display
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
    <meta name="viewport" content="width=800, height=480, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Connection Issue</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">📅 Calendar - {datetime.now().strftime('%A, %B %d')}</h1>
            </div>
            <div class="theme-controls"></div>
        </header>
        
        <main class="calendar-content">
            <section class="error-section">
                <div class="error-icon">⚠️</div>
                <h2 class="error-title">Connection Issue</h2>
                <p class="error-message">{self._escape_html(error_message)}</p>
            </section>
            
            {cached_content}
        </main>
        
        <nav class="calendar-navigation">
            <div class="nav-prev"></div>
            <div class="nav-date-display">Error</div>
            <div class="nav-next"></div>
        </nav>
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>'''
    
    def render_authentication_prompt(self, verification_uri: str, 
                                   user_code: str) -> str:
        """Render authentication prompt optimized for RPI e-ink display.
        
        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter
            
        Returns:
            Formatted HTML authentication prompt with RPI layout
        """
        return f'''<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=800, height=480, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Authentication Required</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">🔐 Authentication Required</h1>
            </div>
            <div class="theme-controls"></div>
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
        
        <nav class="calendar-navigation">
            <div class="nav-prev"></div>
            <div class="nav-date-display">Auth</div>
            <div class="nav-next"></div>
        </nav>
    </div>
</body>
</html>'''