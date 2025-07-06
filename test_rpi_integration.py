#!/usr/bin/env python3
"""Test script to verify RPI integration is working correctly."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_rpi_renderer_import():
    """Test that RPI renderer can be imported."""
    try:
        from calendarbot.display.rpi_html_renderer import RaspberryPiHTMLRenderer
        print("✅ RPI renderer import successful")
        return True
    except ImportError as e:
        print(f"❌ RPI renderer import failed: {e}")
        return False

def test_display_manager_rpi_support():
    """Test that display manager supports RPI mode."""
    try:
        from calendarbot.display.manager import DisplayManager
        from config.settings import CalendarBotSettings
        
        # Create settings with RPI mode
        settings = CalendarBotSettings()
        settings.display_type = "rpi"
        
        # Initialize display manager
        manager = DisplayManager(settings)
        
        # Check that RPI renderer was created
        from calendarbot.display.rpi_html_renderer import RaspberryPiHTMLRenderer
        if isinstance(manager.renderer, RaspberryPiHTMLRenderer):
            print("✅ Display manager RPI support working")
            return True
        else:
            print(f"❌ Display manager created {type(manager.renderer)} instead of RaspberryPiHTMLRenderer")
            return False
            
    except Exception as e:
        print(f"❌ Display manager RPI support failed: {e}")
        return False

def test_rpi_settings():
    """Test that RPI settings are available."""
    try:
        from config.settings import CalendarBotSettings
        
        settings = CalendarBotSettings()
        
        # Check RPI-specific settings exist
        required_attrs = [
            'rpi_enabled', 'rpi_display_width', 'rpi_display_height', 
            'rpi_refresh_mode', 'rpi_auto_theme'
        ]
        
        for attr in required_attrs:
            if not hasattr(settings, attr):
                print(f"❌ Missing RPI setting: {attr}")
                return False
        
        print("✅ RPI settings available")
        return True
        
    except Exception as e:
        print(f"❌ RPI settings test failed: {e}")
        return False

def test_rpi_theme_support():
    """Test that web server supports RPI themes."""
    try:
        from calendarbot.web.server import WebServer
        from calendarbot.display.manager import DisplayManager
        from calendarbot.cache.manager import CacheManager
        from config.settings import CalendarBotSettings
        
        settings = CalendarBotSettings()
        display_manager = DisplayManager(settings)
        cache_manager = CacheManager(settings)
        
        server = WebServer(settings, display_manager, cache_manager)
        
        # Test setting eink-rpi theme
        result = server.set_theme("eink-rpi")
        if result and server.theme == "eink-rpi":
            print("✅ Web server RPI theme support working")
            return True
        else:
            print("❌ Web server RPI theme support failed")
            return False
            
    except Exception as e:
        print(f"❌ Web server RPI theme test failed: {e}")
        return False

def test_rpi_command_line_args():
    """Test that command line argument parsing includes RPI options."""
    try:
        import main
        
        parser = main.create_parser()
        
        # Test parsing RPI arguments
        args = parser.parse_args(['--web', '--rpi', '--rpi-width', '800', '--rpi-height', '480'])
        
        if hasattr(args, 'rpi') and args.rpi:
            print("✅ RPI command line arguments working")
            return True
        else:
            print("❌ RPI command line arguments not found")
            return False
            
    except Exception as e:
        print(f"❌ RPI command line test failed: {e}")
        return False

def test_static_files_exist():
    """Test that RPI static files exist."""
    try:
        static_dir = Path("calendarbot/web/static")
        
        required_files = [
            static_dir / "eink-rpi.css",
            static_dir / "eink-rpi.js"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                print(f"❌ Missing static file: {file_path}")
                return False
        
        print("✅ RPI static files exist")
        return True
        
    except Exception as e:
        print(f"❌ Static files test failed: {e}")
        return False

def main():
    """Run all RPI integration tests."""
    print("🧪 Testing RPI Integration\n")
    
    tests = [
        test_rpi_renderer_import,
        test_rpi_settings,
        test_static_files_exist,
        test_display_manager_rpi_support,
        test_rpi_theme_support,
        test_rpi_command_line_args
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All RPI integration tests passed!")
        return 0
    else:
        print("❌ Some RPI integration tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())