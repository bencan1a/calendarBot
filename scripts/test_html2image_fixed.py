#!/usr/bin/env python3
"""
Test html2image with proper Chrome configuration for container environments.
"""

import os
import tempfile
from html2image import Html2Image

def test_html2image_with_proper_config():
    """Test html2image with container-friendly Chrome configuration."""
    
    print("🧪 Html2Image with Fixed Configuration")
    print("=" * 60)
    
    # Simple HTML to test
    simple_html = """
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Hello World</h1>
        <p>This is a test.</p>
    </body>
    </html>
    """
    
    # Chrome flags to fix container issues
    chrome_flags = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-extensions',
        '--virtual-time-budget=5000',
        '--run-all-compositor-stages-before-draw',
        '--disable-background-media-playback',
        '--disable-client-side-phishing-detection',
        '--disable-component-extensions-with-background-pages',
        '--disable-default-apps',
        '--disable-features=TranslateUI,BlinkGenPropertyTrees',
        '--disable-hang-monitor',
        '--disable-popup-blocking',
        '--disable-prompt-on-repost',
        '--disable-sync',
        '--force-color-profile=srgb',
        '--metrics-recording-only',
        '--no-first-run',
        '--safebrowsing-disable-auto-update',
        '--enable-automation',
        '--password-store=basic',
        '--use-mock-keychain',
        '--single-process'
    ]
    
    try:
        output_dir = "/tmp"
        
        # Create html2image instance with proper configuration
        hti = Html2Image(
            output_path=output_dir, 
            size=(400, 300),
            custom_flags=chrome_flags
        )
        
        print(f"✓ Html2Image created with {len(chrome_flags)} Chrome flags")
        print(f"  Output path: {hti.output_path}")
        
        # Test screenshot
        print("\n--- Test: Configured screenshot ---")
        filename = "fixed_test.png"
        
        # Before screenshot
        target_path = os.path.join(output_dir, filename)
        print(f"Target path: {target_path}")
        print(f"File exists before: {os.path.exists(target_path)}")
        
        # Take screenshot
        result = hti.screenshot(html_str=simple_html, save_as=filename)
        print(f"Screenshot result: {result}")
        
        # After screenshot
        print(f"File exists after: {os.path.exists(target_path)}")
        if os.path.exists(target_path):
            size = os.path.getsize(target_path)
            print(f"✅ SUCCESS: File created with size: {size} bytes")
            return True
        else:
            print(f"❌ FAILED: File not found at target location")
            
            # Check alternative locations
            html2image_path = os.path.join("/tmp/html2image", filename)
            if os.path.exists(html2image_path):
                size = os.path.getsize(html2image_path)
                print(f"✅ Found in html2image dir: {size} bytes")
                # Copy to expected location
                import shutil
                shutil.copy2(html2image_path, target_path)
                print(f"✅ Copied to target location")
                return True
                
            return False
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_html2image_with_proper_config()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")