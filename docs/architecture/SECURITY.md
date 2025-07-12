# Security Features

## User Authentication
CalendarBot supports secure authentication through multiple channels:

### OAuth 2.0 Integration
- Google Calendar: Uses refresh tokens and scope-limited access
- CalDAV: Password-based authentication tokens stored with AES256 encryption

### Encrypted Data Storage
- SQLite database uses encryption at rest via SQLCipher v4.3.0
- Caching layer stores event metadata only (display fields remain client-side)

### TLS Protocol Enforcement
- HTTP/HTTPS strict connection requirements for all external APIs
- Automatic certificate pinning enabled

## Role Management
- Admin Users: Full permissions + API key regeneration capability
- Guest Users: Read-only mode for shared calendar setups

## Incident Response Planning
- Implement emergency wipe procedures for compromised devices
- Maintain offline logs for forensic analysis

## Penetration Testing
- Bi-monthly external security audits performed by Certiphi Labs
- Latest report (v2) passed all OWASP Top 10 benchmarks
