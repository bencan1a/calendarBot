# API Documentation

## Overview

CalendarBot uses a **custom HTTP server** implementation built on Python's `BaseHTTPRequestHandler`, not FastAPI. The web interface provides RESTful endpoints for calendar navigation, theming, and system control.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, no authentication is required for API endpoints.

## Endpoints

### Navigation API

#### Navigate to Date
- **Endpoint**: `/api/navigate`
- **Methods**: `GET`, `POST`
- **Description**: Navigate the calendar to a specific date

**POST Request Body:**
```json
{
  "direction": "next|prev|today|date",
  "date": "2024-01-15"  // Optional: required when direction is "date"
}
```

**Response:**
```json
{
  "status": "success",
  "current_date": "2024-01-15",
  "message": "Navigated to January 15, 2024"
}
```

**GET Parameters:**
- `direction`: Navigation direction (`next`, `prev`, `today`, `date`)
- `date`: Target date (ISO format, required for `direction=date`)

### Layout API

#### Switch Layout
- **Endpoint**: `/api/layout`
- **Methods**: `GET`, `POST`
- **Description**: Switch between available calendar layouts with dynamic discovery

**POST Request Body:**
```json
{
  "layout": "4x8|3x4|custom-layout"
}
```

**Available Layouts:**
- `4x8`: Standard desktop layout (480x800px)
- `3x4`: Compact layout for small displays (300x400px)
- `whats-next-view`: Specialized countdown layout for 300x400px displays with real-time meeting focus
- `custom-layout`: Any custom layout discovered in the layouts directory

**Response:**
```json
{
  "status": "success",
  "layout": "4x8",
  "layout_info": {
    "name": "4x8",
    "display_name": "4×8 Landscape",
    "version": "1.0.0",
    "capabilities": {
      "grid_dimensions": {"columns": 4, "rows": 8}
    }
  },
  "message": "Layout switched to 4x8"
}
```

#### Get Available Layouts
- **Endpoint**: `/api/layouts`
- **Methods**: `GET`
- **Description**: Retrieve list of all discovered layouts

**Response:**
```json
{
  "status": "success",
  "layouts": [
    {
      "name": "4x8",
      "display_name": "4×8 Landscape",
      "description": "Standard landscape layout",
      "version": "1.0.0",
      "capabilities": {
        "grid_dimensions": {"columns": 4, "rows": 8},
        "themes": ["standard", "dark", "eink"]
      }
    },
    {
      "name": "3x4",
      "display_name": "3×4 Compact",
      "description": "Compact layout for small displays",
      "version": "1.0.0",
      "capabilities": {
        "grid_dimensions": {"columns": 3, "rows": 4},
        "themes": ["standard", "eink"]
      }
    },
    {
      "name": "whats-next-view",
      "display_name": "What's Next View",
      "description": "Streamlined countdown layout optimized for 3×4 inch displays, focusing on the next upcoming meeting with real-time countdown timer",
      "version": "1.0.0",
      "capabilities": {
        "grid_dimensions": {"columns": 1, "rows": "auto"},
        "countdown_timer": true,
        "meeting_detection": true,
        "real_time_updates": true,
        "themes": ["standard", "eink"]
      }
    }
  ]
}
```

#### Validate Layout Resources
- **Endpoint**: `/api/layout/{layout_name}/validate`
- **Methods**: `GET`
- **Description**: Validate that a layout's resources are available

**Response:**
```json
{
  "status": "success",
  "layout": "4x8",
  "validation": {
    "layout_exists": true,
    "css_valid": true,
    "js_valid": true,
    "themes_available": ["standard", "dark", "eink"]
  }
}
```

### Theme API

#### Switch Theme
- **Endpoint**: `/api/theme`
- **Methods**: `GET`, `POST`
- **Description**: Switch between available themes for the current layout

**POST Request Body:**
```json
{
  "theme": "standard|dark|eink|high-contrast"
}
```

**Available Themes:**
- `standard`: Default light theme
- `dark`: Dark mode theme
- `eink`: High contrast e-ink optimized theme
- `high-contrast`: Accessibility-focused high contrast theme

**Response:**
```json
{
  "status": "success",
  "theme": "dark",
  "layout": "4x8",
  "message": "Theme switched to dark for layout 4x8"
}
```

### Data Refresh API

#### Refresh Calendar Data
- **Endpoint**: `/api/refresh`
- **Methods**: `GET`, `POST`
- **Description**: Trigger refresh of calendar data from all sources

**POST Request Body:**
```json
{
  "force": true,  // Optional: bypass cache
  "sources": ["google", "outlook"]  // Optional: specific sources
}
```

**Response:**
```json
{
  "status": "success",
  "refreshed_sources": ["google", "outlook"],
  "cache_cleared": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Status API

#### Get Server Status
- **Endpoint**: `/api/status`
- **Methods**: `GET`
- **Description**: Retrieve server health and configuration information

**Response:**
```json
{
  "status": "healthy",
  "uptime": 3600,
  "version": "1.0.0",
  "cache_status": {
    "entries": 150,
    "size_mb": 2.3,
    "hit_rate": 0.85
  },
  "sources": {
    "google": {
      "status": "connected",
      "last_sync": "2024-01-15T10:25:00Z"
    },
    "outlook": {
      "status": "connected", 
      "last_sync": "2024-01-15T10:20:00Z"
    }
  }
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "status": "error",
  "error_code": "INVALID_REQUEST",
  "message": "Invalid date format provided",
  "details": {
    "field": "date",
    "expected": "ISO 8601 format (YYYY-MM-DD)"
  }
}
```

### Common Error Codes

- `INVALID_REQUEST`: Malformed request data
- `INVALID_DATE`: Date format or value is invalid
- `INVALID_THEME`: Unknown theme specified
- `INVALID_LAYOUT`: Unknown layout specified
- `SOURCE_ERROR`: Calendar source connection failed
- `CACHE_ERROR`: Cache operation failed
- `INTERNAL_ERROR`: Server internal error

## Implementation Details

### Custom HTTP Server Architecture

The API is implemented using Python's `http.server.BaseHTTPRequestHandler` with custom routing logic in `calendarbot/web/server.py`. Key characteristics:

1. **Sync/Async Bridge**: Uses `ThreadPoolExecutor` to bridge synchronous HTTP handlers with asynchronous cache operations
2. **Input Validation**: Comprehensive request validation with security logging
3. **Error Handling**: Graceful error handling with detailed logging
4. **CORS Support**: Configurable CORS headers for web interface integration

### Request Processing Flow

```
HTTP Request → WebServer.do_GET/do_POST → Route Handler → Manager Layer → Cache/Sources → Response
```

### Security Features

- Input sanitization and validation
- Request size limits
- Rate limiting (configurable)
- Security headers in responses
- Comprehensive audit logging

## Examples

### Curl Examples

**Navigate to today:**
```bash
curl -X POST http://localhost:8080/api/navigate \
  -H "Content-Type: application/json" \
  -d '{"direction": "today"}'
```

**Switch to eink theme:**
```bash
curl -X POST http://localhost:8080/api/theme \
  -H "Content-Type: application/json" \
  -d '{"theme": "eink"}'
```

**Refresh calendar data:**
```bash
curl -X POST http://localhost:8080/api/refresh \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

**Get server status:**
```bash
curl http://localhost:8080/api/status
```

### JavaScript Examples

```javascript
// Navigate to specific date
const navigateToDate = async (date) => {
  const response = await fetch('/api/navigate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ direction: 'date', date })
  });
  return response.json();
};

// Switch theme
const switchTheme = async (theme) => {
  const response = await fetch('/api/theme', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme })
  });
  return response.json();
};

// Refresh data
const refreshData = async (force = false) => {
  const response = await fetch('/api/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  return response.json();
};

// Switch to whats-next-view layout (specialized countdown layout)
const switchToWhatsNextView = async () => {
  const response = await fetch('/api/layout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ layout: 'whats-next-view' })
  });
  return response.json();
};
```

## Layout-Specific API Behavior

### whats-next-view Layout Integration

The `whats-next-view` layout has specialized integration with CalendarBot's API endpoints to support its real-time countdown and meeting detection features:

#### Enhanced API Response Processing
When using whats-next-view layout, the JavaScript automatically:
- Parses meeting data from `/api/refresh` responses for countdown calculations
- Maintains real-time state for automatic meeting transitions
- Handles 1-second countdown updates and 60-second data refreshes
- Provides specialized error handling for meeting detection failures

#### API Usage Patterns
```javascript
// Example: whats-next-view automatic data processing
async function loadMeetingData() {
  try {
    const response = await fetch('/api/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await response.json();

    if (data.success && data.html) {
      // whats-next-view automatically parses HTML for meeting data
      parseMeetingDataFromHTML(data.html);
      detectCurrentMeeting(); // Identifies next/current meeting
      updateCountdown(); // Starts real-time countdown display
    }
  } catch (error) {
    showErrorState('Network error occurred');
  }
}
```

#### Real-Time Update Integration
The whats-next-view layout implements automatic polling:
- **Countdown Updates**: Every 1 second via `setInterval`
- **Data Refresh**: Every 60 seconds via `/api/refresh`
- **Meeting Transitions**: Automatic detection when meetings end/start
- **Error Recovery**: Graceful fallback to cached data on API failures

#### Accessibility API Integration
The layout includes accessibility features that work with API responses:
- **Screen Reader Announcements**: Uses ARIA live regions for countdown milestones
- **Keyboard Navigation**: API calls triggered by keyboard shortcuts (R, T, L, Space)
- **Focus Management**: Proper focus handling after API state changes