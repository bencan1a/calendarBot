#!/usr/bin/env python3
"""Test script for interactive navigation components."""

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from calendarbot.ui.navigation import NavigationState
from calendarbot.ui.keyboard import KeyboardHandler, KeyCode
from calendarbot.cache.models import CachedEvent


def test_navigation_state():
    """Test navigation state functionality."""
    print("Testing NavigationState...")
    
    nav = NavigationState()
    print(f"Initial date: {nav.selected_date}")
    print(f"Is today: {nav.is_today()}")
    print(f"Display date: {nav.get_display_date()}")
    
    # Test navigation
    nav.navigate_forward()
    print(f"After forward: {nav.get_display_date()}")
    
    nav.navigate_backward(2)
    print(f"After backward 2: {nav.get_display_date()}")
    
    nav.jump_to_today()
    print(f"After jump to today: {nav.get_display_date()}")
    
    # Test week navigation
    nav.jump_to_start_of_week()
    print(f"Start of week: {nav.get_display_date()}")
    
    nav.jump_to_end_of_week()
    print(f"End of week: {nav.get_display_date()}")
    
    print("NavigationState test completed ✓")


def test_keyboard_handler():
    """Test keyboard handler setup."""
    print("\nTesting KeyboardHandler...")
    
    keyboard = KeyboardHandler()
    
    # Test handler registration
    def test_callback():
        print("Test callback called")
    
    keyboard.register_key_handler(KeyCode.LEFT_ARROW, test_callback)
    keyboard.register_key_handler(KeyCode.RIGHT_ARROW, test_callback)
    keyboard.register_key_handler(KeyCode.SPACE, test_callback)
    keyboard.register_key_handler(KeyCode.ESCAPE, test_callback)
    
    help_text = keyboard.get_help_text()
    print(f"Help text: {help_text}")
    
    print("KeyboardHandler test completed ✓")


def create_test_event(subject: str, start_offset_hours: int = 0) -> CachedEvent:
    """Create a test cached event."""
    now = datetime.now()
    start_time = now + timedelta(hours=start_offset_hours)
    end_time = start_time + timedelta(hours=1)
    
    return CachedEvent(
        id=f"test_{subject.lower().replace(' ', '_')}",
        graph_id=f"graph_{subject.lower()}",
        subject=subject,
        body_preview=f"Test event: {subject}",
        start_datetime=start_time.isoformat(),
        end_datetime=end_time.isoformat(),
        start_timezone="UTC",
        end_timezone="UTC",
        is_all_day=False,
        show_as="busy",
        is_cancelled=False,
        is_organizer=True,
        location_display_name="Test Location",
        location_address="123 Test St",
        is_online_meeting=False,
        online_meeting_url=None,
        web_link="https://example.com",
        is_recurring=False,
        series_master_id=None,
        cached_at=now.isoformat(),
        last_modified=now.isoformat()
    )


def test_console_renderer():
    """Test console renderer with interactive mode."""
    print("\nTesting ConsoleRenderer...")
    
    from calendarbot.display.console_renderer import ConsoleRenderer
    from config.settings import settings
    
    renderer = ConsoleRenderer(settings)
    
    # Create test events
    events = [
        create_test_event("Team Meeting", 1),
        create_test_event("Lunch Break", 4),
        create_test_event("Project Review", 6)
    ]
    
    # Test regular mode
    regular_status = {
        'last_update': datetime.now().isoformat(),
        'is_cached': False,
        'connection_status': 'Online'
    }
    
    regular_output = renderer.render_events(events, regular_status)
    print("Regular mode output:")
    print(regular_output[:200] + "..." if len(regular_output) > 200 else regular_output)
    
    # Test interactive mode
    interactive_status = {
        'last_update': datetime.now().isoformat(),
        'is_cached': False,
        'connection_status': 'Online',
        'interactive_mode': True,
        'selected_date': 'TODAY - Saturday, July 05',
        'relative_description': 'Today',
        'navigation_help': '← → Navigate | Space: Today | ESC: Exit'
    }
    
    interactive_output = renderer.render_events(events, interactive_status)
    print("\nInteractive mode output:")
    print(interactive_output[:300] + "..." if len(interactive_output) > 300 else interactive_output)
    
    print("ConsoleRenderer test completed ✓")


async def main():
    """Run all tests."""
    print("Starting interactive navigation component tests...\n")
    
    try:
        test_navigation_state()
        test_keyboard_handler()
        test_console_renderer()
        
        print("\n" + "="*50)
        print("All tests completed successfully! ✓")
        print("="*50)
        
        print("\nInteractive navigation features:")
        print("• Arrow key navigation (← →)")
        print("• Jump to today (Space)")
        print("• Week navigation (Home/End)")
        print("• Exit interactive mode (ESC)")
        print("• Background ICS data fetching")
        print("• Enhanced display with navigation status")
        
        print("\nTo test interactive mode:")
        print("python main.py --interactive")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)