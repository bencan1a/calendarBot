#!/usr/bin/env python3
"""
Debug script to diagnose the HTML-to-PNG conversion issue in epaper mode.

This script will:
1. Generate the actual HTML content being passed to html2image
2. Check for missing resource files (CSS/JS)
3. Test browser access to resources
4. Validate html2image configuration
"""

import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_static_resources() -> dict[str, bool]:
    """Check if static layout resources exist and are accessible."""
    logger.info("🔍 Checking static layout resources...")

    base_path = Path("calendarbot/web/static/layouts/whats-next-view")
    resources = {
        "layout.json": base_path / "layout.json",
        "CSS file": base_path / "whats-next-view.css",
        "JS file": base_path / "whats-next-view.js",
    }

    results = {}
    for name, path in resources.items():
        exists = path.exists()
        results[name] = exists
        if exists:
            logger.info(f"✅ {name}: Found at {path}")
            # Check file size and permissions
            try:
                stat = path.stat()
                logger.info(f"   Size: {stat.st_size} bytes, Mode: {oct(stat.st_mode)}")
            except Exception as e:
                logger.warning(f"   Could not stat file: {e}")
        else:
            logger.error(f"❌ {name}: Missing at {path}")

    return results


def generate_sample_html() -> str:
    """Generate sample HTML content similar to what epaper mode would create."""
    logger.info("🔍 Generating sample HTML content...")

    try:
        # Import the actual renderer components
        import sys

        sys.path.append(".")

        from datetime import datetime

        from calendarbot.display.whats_next_logic import WhatsNextLogic
        from calendarbot.display.whats_next_renderer import WhatsNextRenderer

        # Create mock settings
        class MockSettings:
            web_layout = "whats-next-view"
            timezone = "America/Los_Angeles"

        settings = MockSettings()

        # Create renderer and logic
        renderer = WhatsNextRenderer(settings)
        logic = WhatsNextLogic(settings)

        # Create mock events
        mock_events = []

        # Create view model
        view_model = logic.create_view_model(mock_events, {"last_update": datetime.now()})

        # Generate HTML
        html_content = renderer.render(view_model)

        logger.info(f"✅ Generated HTML content ({len(html_content)} characters)")
        logger.debug(f"HTML preview (first 500 chars):\n{html_content[:500]}...")

        return html_content

    except Exception as e:
        logger.exception(f"❌ Failed to generate HTML content: {e}")

        # Fallback: create minimal HTML that would trigger the issue
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>E-Paper Test</title>
            <link rel="stylesheet" href="calendarbot/web/static/layouts/whats-next-view/whats-next-view.css">
            <script src="calendarbot/web/static/layouts/whats-next-view/whats-next-view.js"></script>
        </head>
        <body>
            <div class="calendar-container">
                <h1>Test Content</h1>
                <p>This should render properly if CSS loads.</p>
            </div>
        </body>
        </html>
        """
        logger.info("📝 Using fallback HTML content")
        return fallback_html


def test_html2image_conversion(html_content: str) -> Optional[str]:
    """Test html2image conversion with detailed logging."""
    logger.info("🔍 Testing html2image conversion...")

    try:
        from calendarbot.display.epaper.utils.html_to_png import (
            create_converter,
            is_html2image_available,
        )

        if not is_html2image_available():
            logger.error("❌ html2image is not available")
            return None

        # Create output directory
        output_dir = Path("epaper_test_output")
        output_dir.mkdir(exist_ok=True)

        logger.info(f"📁 Using output directory: {output_dir}")

        # Create converter with detailed logging
        converter = create_converter(size=(400, 300), output_path=str(output_dir))

        if converter is None:
            logger.error("❌ Failed to create HTML converter")
            return None

        logger.info(f"✅ Created HTML converter: {type(converter)}")
        logger.info(f"   Output path: {converter.output_path}")

        # Log browser flags being used
        if hasattr(converter, "hti") and converter.hti:
            logger.info("🔧 Browser configuration:")
            custom_flags = getattr(converter.hti, "custom_flags", [])
            for flag in custom_flags[:10]:  # Log first 10 flags
                logger.info(f"   {flag}")
            if len(custom_flags) > 10:
                logger.info(f"   ... and {len(custom_flags) - 10} more flags")

        # Test conversion
        logger.info("🔄 Starting HTML-to-PNG conversion...")
        result_path = converter.convert_html_to_png(
            html_content=html_content, output_filename="debug_test.png"
        )

        if result_path and Path(result_path).exists():
            file_size = Path(result_path).stat().st_size
            logger.info(f"✅ Conversion successful: {result_path} ({file_size} bytes)")
            return result_path
        logger.error(f"❌ Conversion failed or file not found: {result_path}")

        # List files in output directory for debugging
        try:
            files = list(output_dir.iterdir())
            logger.info(f"📂 Files in output directory: {[f.name for f in files]}")
        except Exception as e:
            logger.warning(f"Could not list output directory: {e}")

        return None

    except Exception as e:
        logger.exception(f"❌ HTML-to-PNG conversion failed: {e}")
        return None


def analyze_png_content(png_path: str) -> None:
    """Analyze the generated PNG to check for error content."""
    logger.info(f"🔍 Analyzing PNG content: {png_path}")

    try:
        import pytesseract
        from PIL import Image

        # Open and analyze the image
        with Image.open(png_path) as img:
            logger.info(f"📊 Image info: {img.size} pixels, mode: {img.mode}")

            # Try to extract text to see if it contains error messages
            try:
                extracted_text = pytesseract.image_to_string(img)
                if "ERR" in extracted_text.upper() or "FILE NOT FOUND" in extracted_text.upper():
                    logger.error(f"❌ Found error text in image: {extracted_text.strip()}")
                else:
                    logger.info(f"✅ Image text looks normal: {extracted_text.strip()[:100]}...")
            except Exception as e:
                logger.warning(
                    f"Could not extract text from image (pytesseract not available): {e}"
                )

            # Check if image is mostly uniform (suggests rendering failure)
            import numpy as np

            img_array = np.array(img.convert("L"))  # Convert to grayscale
            std_dev = np.std(img_array)

            if std_dev < 10:  # Very low variation suggests solid color/error
                logger.warning(
                    f"⚠️  Image has very low variation (std dev: {std_dev:.2f}) - possible rendering failure"
                )
            else:
                logger.info(
                    f"✅ Image has good variation (std dev: {std_dev:.2f}) - likely rendered correctly"
                )

    except ImportError:
        logger.warning("PIL or pytesseract not available for image analysis")
    except Exception as e:
        logger.exception(f"Failed to analyze PNG content: {e}")


def main():
    """Main diagnostic function."""
    logger.info("🚀 Starting epaper HTML-to-PNG diagnostic...")

    print("\n" + "=" * 60)
    print("EPAPER HTML-TO-PNG DIAGNOSTIC")
    print("=" * 60)

    # Step 1: Check static resources
    print("\n📁 STEP 1: Checking static resources...")
    resource_status = check_static_resources()
    missing_resources = [name for name, exists in resource_status.items() if not exists]

    if missing_resources:
        print(f"⚠️  Missing resources detected: {', '.join(missing_resources)}")
    else:
        print("✅ All static resources found")

    # Step 2: Generate HTML content
    print("\n📝 STEP 2: Generating HTML content...")
    html_content = generate_sample_html()

    # Save HTML for inspection
    html_file = Path("epaper_test_output/debug_generated.html")
    html_file.parent.mkdir(exist_ok=True)
    html_file.write_text(html_content)
    print(f"💾 Saved HTML to: {html_file}")

    # Step 3: Test HTML-to-PNG conversion
    print("\n🖼️  STEP 3: Testing HTML-to-PNG conversion...")
    png_path = test_html2image_conversion(html_content)

    # Step 4: Analyze results
    print("\n🔍 STEP 4: Analysis...")
    if png_path:
        analyze_png_content(png_path)
        print(f"📊 Generated PNG available at: {png_path}")
    else:
        print("❌ No PNG generated - conversion failed")

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    if missing_resources:
        print("🔴 LIKELY ISSUE: Missing static resources")
        print(f"   Missing files: {', '.join(missing_resources)}")
        print("   Action: Check layout file paths and ensure resources exist")
    elif not png_path:
        print("🔴 LIKELY ISSUE: HTML-to-PNG conversion failure")
        print("   Possible causes: Browser security restrictions, html2image config")
        print("   Action: Check browser flags and snap permissions")
    else:
        print("🟡 CONVERSION WORKS BUT CHECK CONTENT")
        print("   PNG was generated - check if it contains error messages")
        print(f"   Examine: {png_path}")

    print("\n📋 Next steps:")
    print("   1. Review the generated HTML file for missing resource references")
    print("   2. Check the PNG output for 'ERR FILE NOT FOUND' text")
    print("   3. Consider browser security configuration if snap is in use")


if __name__ == "__main__":
    main()
