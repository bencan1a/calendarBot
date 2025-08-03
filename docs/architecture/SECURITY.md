# Security Features

## User Authentication
CalendarBot supports secure authentication through multiple channels:

- **Google Calendar**: Uses secret iCal URLs for secure access
- **CalDAV**: Basic authentication with password validation

## Data Storage

- **SQLite Database**: Standard SQLite database for caching calendar events
- **Caching Layer**: Stores event metadata only (display fields remain client-side)

## Network Security

- **TLS Protocol**: HTTP/HTTPS strict connection requirements for all external APIs
- **SSL Validation**: Configurable SSL certificate validation

## Access Control

- **Single User Mode**: Basic access control for calendar data

## Security Monitoring

- **Security Event Logging**: Comprehensive logging of security events
- **Input Validation**: SSRF protection and input sanitization

## Security Testing

- **Security Unit Tests**: Automated tests for security features
- **SSRF Protection Tests**: Validation of URL security measures
