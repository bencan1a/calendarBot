# Rate Limiting for Alexa Endpoints

## Overview

CalendarBot Lite implements lightweight, in-memory rate limiting to protect Alexa integration endpoints from Denial of Service (DoS) attacks. The implementation uses a sliding window algorithm for accurate request tracking without requiring external dependencies like Redis.

## Design Philosophy

Following the project's principle of keeping things simple for personal deployments on resource-constrained hardware (Raspberry Pi Zero 2W):

- **In-Memory Only**: No external database or cache required
- **Minimal Footprint**: ~1KB memory per tracked IP/token
- **Single-Instance**: Designed for standalone deployment
- **Automatic Management**: Background cleanup of expired entries
- **Zero Configuration**: Works out of the box with sensible defaults

## How It Works

### Sliding Window Algorithm

Rate limiting uses a sliding window approach:
1. Each request timestamp is recorded
2. When checking limits, only requests within the window are counted
3. Requests older than the window are automatically excluded
4. This provides accurate rate limiting without time-bucketing edge cases

### Dual Tracking

Two independent rate limits are enforced:

1. **Per-IP Limiting**: Tracks requests by client IP address
   - Protects against IP-based attacks
   - Default: 100 requests/minute

2. **Per-Token Limiting**: Tracks requests by bearer token
   - Protects against compromised token abuse
   - Default: 500 requests/minute

3. **Burst Protection**: Short-window rapid-fire protection
   - Prevents burst attacks
   - Default: 20 requests in 10 seconds

A request must pass ALL three checks to be allowed.

## Configuration

Rate limits can be customized via environment variables:

```bash
# In .env file
CALENDARBOT_RATE_LIMIT_PER_IP=100        # Requests per minute per IP
CALENDARBOT_RATE_LIMIT_PER_TOKEN=500     # Requests per minute per bearer token
CALENDARBOT_RATE_LIMIT_BURST=20          # Max requests in burst window
CALENDARBOT_RATE_LIMIT_BURST_WINDOW=10   # Burst window in seconds
```

## Protected Endpoints

Rate limiting is automatically applied to all Alexa API endpoints:

- `GET /api/alexa/next-meeting` - Next meeting information
- `GET /api/alexa/time-until-next` - Time until next meeting
- `GET /api/alexa/done-for-day` - End of day status
- `GET /api/alexa/launch-summary` - Launch summary
- `GET /api/alexa/morning-summary` - Morning summary

## HTTP Response Headers

All responses include rate limit information:

```
X-RateLimit-Limit-IP: 100
X-RateLimit-Remaining-IP: 95
X-RateLimit-Reset: 47
```

When rate limited (HTTP 429):

```
HTTP/1.1 429 Too Many Requests
Retry-After: 10
Content-Type: application/json

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please slow down.",
  "retry_after": 10
}
```

## Monitoring

Rate limiter statistics are available via the health endpoint:

```bash
curl http://localhost:8080/api/health | jq .rate_limiting
```

Response:
```json
{
  "total_requests": 1234,
  "rejected_requests": 5,
  "rejection_rate": 0.004,
  "tracked_ips": 3,
  "tracked_tokens": 1,
  "config": {
    "per_ip_limit": 100,
    "per_token_limit": 500,
    "burst_limit": 20,
    "burst_window_seconds": 10
  }
}
```

## Testing Rate Limits

### Manual Testing with curl

Test IP-based rate limiting:

```bash
# Make multiple rapid requests
for i in {1..25}; do
  curl -s -w "Status: %{http_code}\n" http://localhost:8080/api/alexa/next-meeting
done

# Should see HTTP 429 after burst limit (20 requests)
```

Test token-based rate limiting:

```bash
# With bearer token
for i in {1..25}; do
  curl -s -w "Status: %{http_code}\n" \
    -H "Authorization: Bearer your-token" \
    http://localhost:8080/api/alexa/next-meeting
done
```

### Automated Tests

Run the comprehensive test suite:

```bash
# Unit tests (17 tests)
pytest tests/lite/test_rate_limiter.py -v

# Integration tests (9 tests)
pytest tests/lite/test_rate_limit_integration.py -v

# All rate limiting tests
pytest tests/lite/test_rate_limi*.py -v
```

## Architecture

### Core Components

1. **RateLimiter** (`rate_limiter.py`)
   - Sliding window tracking
   - Thread-safe asyncio operations
   - Background cleanup task
   - Statistics collection

2. **Middleware** (`rate_limit_middleware.py`)
   - Handler wrapper for easy integration
   - Header injection
   - 429 response formatting

3. **Integration** (`server.py`, `alexa_routes.py`)
   - Automatic initialization
   - Graceful degradation if module unavailable
   - Health endpoint integration

### Memory Usage

Approximate memory footprint:
- Base RateLimiter: ~1KB
- Per tracked IP: ~500 bytes (for 100 requests)
- Per tracked token: ~500 bytes (for 100 requests)
- Total for 10 IPs + 2 tokens: ~7KB

This is negligible even on Raspberry Pi Zero 2W (1GB RAM).

### Cleanup Strategy

A background task runs every 5 minutes (configurable) to remove entries with:
- No requests in the last 5 minutes
- All request timestamps expired from windows

This prevents unbounded memory growth over long server uptimes.

## Limitations

### Single-Instance Only

Rate limiting state is in-memory and not shared across instances. For distributed deployments:
- Consider external storage (Redis) - requires code modification
- Use load balancer rate limiting instead
- Accept per-instance limits (100 req/min × N instances)

For personal CalendarBot deployments, single-instance is the expected configuration.

### Clock Drift

Relies on system clock for timestamps. If the system clock jumps significantly:
- Forward jump: May temporarily allow more requests
- Backward jump: May temporarily block valid requests

For Raspberry Pi deployments, ensure NTP is configured:
```bash
timedatectl set-ntp true
```

## Security Considerations

### What Rate Limiting Protects Against

✅ **Protected:**
- Brute force attacks on authentication endpoints
- Resource exhaustion from excessive requests
- Accidental runaway client scripts
- Basic DoS attacks

❌ **Not Protected:**
- Distributed DoS (DDoS) from many IPs - use upstream protection
- Application-layer attacks that stay under limits
- Compromised legitimate credentials

### Defense in Depth

Rate limiting is one layer. Also implement:
- Strong bearer token authentication (`CALENDARBOT_ALEXA_BEARER_TOKEN`)
- HTTPS/TLS in production
- Firewall rules limiting public exposure
- Regular security updates

## Troubleshooting

### Rate Limit Too Strict

Increase limits in `.env`:
```bash
CALENDARBOT_RATE_LIMIT_PER_IP=200
CALENDARBOT_RATE_LIMIT_BURST=50
```

### Rate Limiter Not Working

Check logs for initialization:
```bash
# Should see:
# INFO: RateLimiter initialized: per_ip=100/min, per_token=500/min, burst=20/10s
# INFO: Registered 5 Alexa routes with rate limiting

journalctl -u calendarbot-lite -f | grep -i rate
```

### High Rejection Rate

Check statistics:
```bash
curl -s http://localhost:8080/api/health | jq '.rate_limiting'
```

If rejection rate > 5%, consider:
- Increasing limits
- Investigating client behavior
- Checking for misconfigured automation

### Memory Concerns

Monitor tracked entries:
```bash
# Check number of tracked IPs/tokens
curl -s http://localhost:8080/api/health | \
  jq '.rate_limiting.tracked_ips, .rate_limiting.tracked_tokens'
```

If numbers grow unbounded, check cleanup task is running:
```bash
# Should see periodic "Cleaned up N expired entries" in logs
journalctl -u calendarbot-lite -f | grep cleanup
```

## Performance Impact

Benchmarks on Raspberry Pi Zero 2W:

- **Latency overhead**: < 1ms per request
- **Memory overhead**: ~5-10KB typical usage
- **CPU overhead**: Negligible (< 1% CPU)

Rate limiting has minimal performance impact on normal operation.

## Future Enhancements

Potential improvements (not currently implemented):

- [ ] Configurable window sizes (currently fixed at 60s)
- [ ] Per-route custom limits
- [ ] Rate limit whitelist/blacklist
- [ ] Persistent storage option (SQLite)
- [ ] Distributed rate limiting (Redis)
- [ ] Rate limit bypass for health checks

For personal deployments, current implementation is sufficient.

## References

- [RFC 6585 - Additional HTTP Status Codes](https://tools.ietf.org/html/rfc6585#section-4) (429 Too Many Requests)
- [IETF Draft - RateLimit Header Fields](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)
- Project issue: #[issue-number]

---

**Implementation Date**: November 2025  
**Tested On**: Raspberry Pi Zero 2W, Python 3.12+
