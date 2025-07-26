# CalendarBot e-Paper Display Integration

This package provides integration with Waveshare e-Paper displays for the CalendarBot project.
It supports the Waveshare 4.2inch e-Paper Module (B) v2 (400x300 pixels, black/white/red).

## Package Structure

```
calendarbot_epaper/
├── __init__.py                 # Package initialization
├── display/                    # Display abstraction layer
│   ├── __init__.py
│   ├── abstraction.py          # Display abstraction layer interfaces
│   ├── capabilities.py         # Display capabilities model
│   └── region.py               # Region model for partial updates
├── drivers/                    # Display drivers
│   ├── __init__.py
│   ├── eink_driver.py          # Base e-ink driver interface
│   └── waveshare/              # Waveshare-specific drivers
│       ├── __init__.py
│       ├── epd4in2b_v2.py      # Waveshare 4.2inch e-Paper Module (B) v2 driver
│       └── utils.py            # Utility functions for Waveshare drivers
├── rendering/                  # Rendering utilities
│   └── __init__.py
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── logging.py              # Logging utilities
│   └── image_processing.py     # Image processing utilities
├── setup.py                    # Package setup file
└── requirements.txt            # Package dependencies
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Raspberry Pi with SPI enabled
- Waveshare 4.2inch e-Paper Module (B) v2

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/calendarbot/calendarbot_epaper.git
   cd calendarbot_epaper
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

## Usage

### Basic Usage

```python
from calendarbot_epaper.drivers.waveshare.epd4in2b_v2 import EPD4in2bV2
from calendarbot_epaper.utils.image_processing import create_text_image, convert_image_to_epaper_format

# Initialize display
display = EPD4in2bV2()
display.initialize()

# Get display capabilities
capabilities = display.get_capabilities()
print(f"Display capabilities: {capabilities}")

# Create text image
image = create_text_image(
    "Hello, CalendarBot!",
    capabilities.width,
    capabilities.height,
    font_size=36,
    text_color="black",
    bg_color="white",
    align="center"
)

# Convert image to e-Paper format
buffer = convert_image_to_epaper_format(image)

# Display text
display.render(buffer)

# Shutdown display when done
display.shutdown()
```

### Test Script

The package includes a test script that can be used to verify the functionality of the e-Paper display:

```bash
python calendarbot_epaper/test_epaper.py --test-pattern
```

or

```bash
python calendarbot_epaper/test_epaper.py --text "Hello, CalendarBot!"
```

## Integration with CalendarBot

To integrate this package with CalendarBot, add it as a dependency in CalendarBot's setup.py or requirements.txt:

```python
# In setup.py
install_requires=[
    # ...
    "calendarbot_epaper",
    # ...
]
```

Then, import and use the package in CalendarBot:

```python
from calendarbot_epaper.drivers.waveshare.epd4in2b_v2 import EPD4in2bV2
from calendarbot_epaper.utils.image_processing import convert_image_to_epaper_format

# Initialize display
display = EPD4in2bV2()
display.initialize()

# Render content to display
# ...

# Shutdown display when done
display.shutdown()
```

## Future Development

The following components are planned for future development:

- Diff-based update detector for optimizing refresh frequency
- Refresh strategy manager for managing e-ink display refreshes
- Text rendering optimizer for e-ink displays
- E-ink WhatsNext renderer for CalendarBot's WhatsNext view

## License

This project is licensed under the MIT License - see the LICENSE file for details.
