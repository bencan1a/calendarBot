#!/usr/bin/env python3
"""
Diagnostic script to identify the root cause of HTML-to-PNG conversion issues.

This script will test various aspects of the HTML-to-PNG pipeline to determine
why images contain "Your file couldn't be accessed" instead of rendered content.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_html_content_generation():
    """Test HTML content generation from HTMLRenderer."""
    print("\n=== Testing HTML Content Generation ===")
    
    try:
        # Import required modules
        from calendarbot.display.html_renderer import HTMLRenderer
        
        # Create a mock settings object
        class MockSettings:
            web_layout = "whats-next-view"
        
        settings = MockSettings()
        renderer = HTMLRenderer(settings)
        
        # Generate HTML content with empty events to test template generation
        html_content = renderer.render_events([], {"interactive_mode": False})
        
        print(f"✓ HTML content generated successfully")
        print(f"  Content length: {len(html_content)} characters")
        
        # Check for resource paths
        resource_paths = []
        if "/static/" in html_content:
            import re
            paths = re.findall(r'(?:href|src)="([^"]*)"', html_content)
            resource_paths = [p for p in paths if p.startswith("/static/")]
            
        print(f"  Found {len(resource_paths)} resource paths:")
        for path in resource_paths[:5]:  # Show first 5
            print(f"    - {path}")
            # Check if these paths exist on filesystem
            file_path = Path(f"calendarbot/web{path}")
            exists = file_path.exists()
            print(f"      File exists: {exists}")
        
        if resource_paths:
            print("  ⚠️  HTML contains server-dependent resource paths")
            print("     These paths require a web server to resolve")
        
        # Save HTML content for inspection
        with open("debug_html_content.html", "w") as f:
            f.write(html_content)
        print(f"  💾 HTML content saved to debug_html_content.html")
        
        return html_content, resource_paths
        
    except Exception as e:
        print(f"❌ Failed to generate HTML content: {e}")
        logger.exception("HTML content generation failed")
        return None, []

def test_simple_html_conversion():
    """Test HTML-to-PNG conversion with simple HTML."""
    print("\n=== Testing Simple HTML Conversion ===")
    
    try:
        from calendarbot.display.epaper.utils.html_to_png import create_converter
        
        # Create simple HTML without external resources
        simple_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Test</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: white; 
                    color: black; 
                    padding: 20px;
                }
                .test-content {
                    text-align: center;
                    padding: 50px;
                    border: 2px solid #333;
                }
            </style>
        </head>
        <body>
            <div class="test-content">
                <h1>Simple Test Content</h1>
                <p>This is a test of HTML-to-PNG conversion</p>
                <p>No external resources required</p>
            </div>
        </body>
        </html>
        """
        
        # Create converter
        converter = create_converter(size=(400, 300))
        if not converter:
            print("❌ Failed to create HTML-to-PNG converter")
            return False
        
        print("✓ HTML-to-PNG converter created successfully")
        
        # Convert simple HTML
        result_path = converter.convert_html_to_png(
            html_content=simple_html,
            output_filename="simple_test.png"
        )
        
        if result_path and os.path.exists(result_path):
            print(f"✓ Simple HTML converted successfully: {result_path}")
            print(f"  File size: {os.path.getsize(result_path)} bytes")
            return True
        else:
            print(f"❌ Simple HTML conversion failed")
            return False
            
    except Exception as e:
        print(f"❌ Simple HTML conversion error: {e}")
        logger.exception("Simple HTML conversion failed")
        return False

def test_complex_html_conversion(html_content: str):
    """Test HTML-to-PNG conversion with complex HTML containing resource paths."""
    print("\n=== Testing Complex HTML Conversion ===")
    
    try:
        from calendarbot.display.epaper.utils.html_to_png import create_converter
        
        if not html_content:
            print("❌ No HTML content provided")
            return False
        
        # Create converter
        converter = create_converter(size=(400, 300))
        if not converter:
            print("❌ Failed to create HTML-to-PNG converter")
            return False
        
        print("✓ HTML-to-PNG converter created successfully")
        
        # Convert complex HTML (this should fail with resource loading issues)
        result_path = converter.convert_html_to_png(
            html_content=html_content,
            output_filename="complex_test.png"
        )
        
        if result_path and os.path.exists(result_path):
            print(f"✓ Complex HTML converted: {result_path}")
            print(f"  File size: {os.path.getsize(result_path)} bytes")
            
            # Check if image contains error message
            try:
                from PIL import Image
                img = Image.open(result_path)
                print(f"  Image dimensions: {img.size}")
                print(f"  Image mode: {img.mode}")
                
                # Save a copy for inspection
                img.save("debug_complex_conversion.png")
                print("  💾 Image saved as debug_complex_conversion.png for inspection")
                
            except Exception as img_error:
                print(f"  ⚠️  Could not analyze image: {img_error}")
            
            return True
        else:
            print(f"❌ Complex HTML conversion failed")
            return False
            
    except Exception as e:
        print(f"❌ Complex HTML conversion error: {e}")
        logger.exception("Complex HTML conversion failed")
        return False

def test_resource_path_resolution():
    """Test if resource paths can be resolved."""
    print("\n=== Testing Resource Path Resolution ===")
    
    # Test common resource paths
    test_paths = [
        "calendarbot/web/static/shared/css/settings-panel.css",
        "calendarbot/web/static/shared/js/settings-api.js",
        "calendarbot/web/static/layouts/whats-next-view/whats-next-view.css",
        "calendarbot/web/static/layouts/whats-next-view/whats-next-view.js"
    ]
    
    existing_paths = []
    missing_paths = []
    
    for path in test_paths:
        file_path = Path(path)
        if file_path.exists():
            existing_paths.append(path)
            print(f"✓ Found: {path}")
        else:
            missing_paths.append(path)
            print(f"❌ Missing: {path}")
    
    print(f"\nResource Path Summary:")
    print(f"  Existing: {len(existing_paths)}")
    print(f"  Missing: {len(missing_paths)}")
    
    if missing_paths:
        print(f"  ⚠️  Missing resource files could cause 'file couldn't be accessed' errors")
    
    return existing_paths, missing_paths

def main():
    """Main diagnostic function."""
    print("🔍 HTML-to-PNG Issue Diagnostic Script")
    print("="*50)
    
    # Test 1: HTML content generation
    html_content, resource_paths = test_html_content_generation()
    
    # Test 2: Resource path resolution
    existing_paths, missing_paths = test_resource_path_resolution()
    
    # Test 3: Simple HTML conversion (should work)
    simple_conversion_success = test_simple_html_conversion()
    
    # Test 4: Complex HTML conversion (likely to fail)
    complex_conversion_success = False
    if html_content:
        complex_conversion_success = test_complex_html_conversion(html_content)
    
    # Summary and diagnosis
    print("\n" + "="*50)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("="*50)
    
    print(f"Simple HTML conversion: {'✓ PASS' if simple_conversion_success else '❌ FAIL'}")
    print(f"Complex HTML conversion: {'✓ PASS' if complex_conversion_success else '❌ FAIL'}")
    print(f"Resource paths found in HTML: {len(resource_paths)}")
    print(f"Missing resource files: {len(missing_paths)}")
    
    # Diagnosis
    if simple_conversion_success and not complex_conversion_success:
        print("\n🎯 DIAGNOSIS:")
        print("The HTML-to-PNG converter works with simple HTML but fails with complex HTML.")
        if resource_paths:
            print("LIKELY CAUSE: Resource path resolution issues")
            print("  • HTML contains server-dependent paths (/static/...)")
            print("  • html2image cannot resolve these paths without a web server")
            print("  • Browser shows 'Your file couldn't be accessed' for missing resources")
        else:
            print("LIKELY CAUSE: HTML content or formatting issues")
        
        print("\nRECOMMENDED FIXES:")
        print("1. Generate standalone HTML with inline CSS/JS")
        print("2. Use absolute file paths for resources")
        print("3. Create a specialized HTML template for html2image")
        
    elif not simple_conversion_success:
        print("\n🎯 DIAGNOSIS:")
        print("LIKELY CAUSE: HTML-to-PNG converter configuration issues")
        print("  • html2image installation or browser configuration problems")
        print("  • Output path or permissions issues")
        
    else:
        print("\n🎯 DIAGNOSIS:")
        print("Both simple and complex HTML conversion work.")
        print("The issue might be elsewhere in the pipeline.")

if __name__ == "__main__":
    main()