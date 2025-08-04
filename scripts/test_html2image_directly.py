#!/usr/bin/env python3
"""
Direct test of html2image to understand the file creation issue.
"""

import os
import tempfile
from html2image import Html2Image

def test_html2image_directly():
    """Test html2image directly to understand file creation issues."""
    
    print("🧪 Direct html2image Test")
    print("=" * 50)
    
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
    
    # Create html2image instance
    try:
        output_dir = "/tmp"
        hti = Html2Image(output_path=output_dir, size=(400, 300))
        print(f"✓ Html2Image created with output_path: {output_dir}")
        print(f"  Output path: {hti.output_path}")
        
        # Test 1: Direct screenshot
        print("\n--- Test 1: Direct screenshot ---")
        filename = "direct_test.png"
        
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
            print(f"File size: {size} bytes")
        
        # Check html2image directory
        html2image_dir = "/tmp/html2image"
        print(f"\nhtml2image directory exists: {os.path.exists(html2image_dir)}")
        if os.path.exists(html2image_dir):
            files = os.listdir(html2image_dir)
            print(f"Files in html2image dir: {files}")
            for f in files:
                if f.endswith('.png'):
                    full_path = os.path.join(html2image_dir, f)
                    size = os.path.getsize(full_path)
                    print(f"  Found PNG: {f} ({size} bytes)")
        
        # Check if file might be elsewhere
        print(f"\nSearching for {filename} in /tmp...")
        for root, dirs, files in os.walk("/tmp"):
            for file in files:
                if file == filename:
                    full_path = os.path.join(root, file)
                    size = os.path.getsize(full_path)
                    print(f"  Found at: {full_path} ({size} bytes)")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_html2image_directly()