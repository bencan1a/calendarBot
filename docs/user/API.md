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

### Theme API

#### Switch Theme
- **Endpoint**: `/api/theme`
- **Methods**: `GET`, `POST`
- **Description**: Switch between available calendar themes

**POST Request Body:**
```json
{
  "theme": "4x8|3x4"
}
```

**Available Themes:**
- `4x8`: Four-week view with 8-day width
- `3x4`: Three-week view with 4-day width

**Response:**
```json
{
  "status": "success",
  "theme": "4x8",
  "message": "Theme switched to 4x8"
}
```

### Layout API

#### Switch Layout
- **Endpoint**: `/api/layout`
- **Methods**: `GET`, `POST`
- **Description**: Change calendar layout configuration

**POST Request Body:**
```json
{
  "layout": "compact|expanded|minimal"
}
```

**Response:**
```json
{
  "status": "success",
  "layout": "compact",
  "message": "Layout switched to compact"
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

**Switch to 3x4 theme:**
```bash
curl -X POST http://localhost:8080/api/theme \
  -H "Content-Type: application/json" \
  -d '{"theme": "3x4"}'
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