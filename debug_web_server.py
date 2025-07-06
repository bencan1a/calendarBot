#!/usr/bin/env python3
"""Debug script to validate WebServer parameter issues."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_webserver_params():
    """Test WebServer parameter validation."""
    try:
        from calendarbot.web.server import WebServer
        from config.settings import settings
        
        print("=== WebServer Constructor Signature Analysis ===")
        import inspect
        sig = inspect.signature(WebServer.__init__)
        print(f"Expected parameters: {list(sig.parameters.keys())}")
        
        print(f"\n=== Settings Web Configuration ===")
        print(f"settings.web_host: {settings.web_host}")
        print(f"settings.web_port: {settings.web_port}")
        print(f"settings.web_theme: {settings.web_theme}")
        
        print(f"\n=== Testing Invalid Constructor Call ===")
        try:
            # This mimics the current broken call in main.py
            web_server = WebServer(
                cache_manager=None,
                display_manager=None,
                navigation_handler=None,  # Wrong parameter name
                host="localhost",         # Invalid parameter
                port=8080                # Invalid parameter
            )
        except Exception as e:
            print(f"Expected error: {e}")
            
        print(f"\n=== Testing Correct Constructor Call ===")
        try:
            # This should work
            web_server = WebServer(
                settings=settings,        # Required first parameter
                display_manager=None,     # Can be None for testing
                cache_manager=None,       # Can be None for testing
                navigation_state=None     # Correct parameter name
            )
            print("✅ Correct constructor call succeeded")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            
        print(f"\n=== WebServer Method Analysis ===")
        print(f"start() method is async: {inspect.iscoroutinefunction(WebServer.start)}")
        
    except Exception as e:
        print(f"Debug script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_webserver_params()