# Technology Stack

## Overview
CalendarBot utilizes a modular, multi-layered architecture optimized for embedded device performance. The tech stack combines native Python libraries with specialized components for optimal efficiency.

## Key Components

### Backend Framework
- **Python HTTPServer**: Provides HTTP request handling for the web interface. Chosen for its lightweight footprint and integration with the standard library.
- **Pydantic**: Used for data validation and settings management throughout the application.

### Data Storage
- **SQLite**: Lightweight relational database for scheduled events. Chosen for offline capability and transaction reliability. Uses direct SQL queries with `sqlite3` and `aiosqlite` modules for asynchronous operations.
- **WAL Mode**: Write-Ahead Logging for improved concurrency and performance.

### Interface Protocols
- **ICS (iCalendar) Parsing**: Implements complex event parsing via custom calendarbot.ics model
- **Web Interface**: Serves dashboard at http://localhost:8080 with auto-refresh enabled. Provides calendar context switching and quick refresh controls.

### Display Subsystems
- **4x8 LCD Renderer**: Optimized for standard desktop screens (192x128 pixels)
- **3x4 Compact Renderer**: Tailored for embedded e-ink displays with fixed text resolution

### Cryptographic Security
- **TLS/HTTPS Integration**: For all calendar API integrations (CalDAV & Google Calendar)
- **Secret URL Access**: Google Calendar integration uses secret iCal URLs for secure access
- **SSL Certificate Validation**: Configurable SSL certificate validation for external APIs

## Software Lifespan Overview

![CalendarBot Lifespan Diagram](./images/calendarbot-lifespan.png)
