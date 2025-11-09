# Security Recommendations - Quick Reference

**Assessment Date**: November 8, 2025  
**Full Report**: See [ALEXA_LAMBDA_SECURITY_ASSESSMENT.md](ALEXA_LAMBDA_SECURITY_ASSESSMENT.md)

---

## Executive Summary

CalendarBot's Alexa integration has **strong baseline security** but is missing **one critical control**: Alexa request signature verification. For personal, unpublished skills, the current implementation is functional but doesn't meet Amazon's certification requirements.

**Current Security Status**: ✅ Good (with critical gap for public skills)

---

## Priority Findings

### 🔴 CRITICAL: Missing Alexa Request Signature Verification

**Status**: Not implemented  
**Risk**: Unauthorized Lambda invocations, bypass of Amazon security controls  
**Required For**: Publishing skill to Alexa Skills Store  
**Effort**: Medium (4-8 hours)

**Quick Fix**: Use `ask-sdk-core` library for automatic signature verification:

```python
# Install ask-sdk-core in Lambda
# pip install ask-sdk-core

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

sb = SkillBuilder()

class NextMeetingIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("GetNextMeetingIntent")(handler_input)
    
    def handle(self, handler_input):
        # Call your existing handle_get_next_meeting_intent() logic
        response_data = handle_get_next_meeting_intent()
        return handler_input.response_builder.speak(
            response_data.speech_text
        ).set_card(
            SimpleCard("Next Meeting", response_data.speech_text)
        ).response

sb.add_request_handler(NextMeetingIntentHandler())
# ... add other handlers ...

skill = sb.create()

def lambda_handler(event, context):
    return skill.invoke(event, context)  # Signature verification happens here
```

**Decision Point**: 
- ✅ Implementing skill for personal use only? **Can defer** (document risk)
- ⚠️ Planning to publish skill? **Must implement immediately**

---

### 🟡 MEDIUM: HTTPS Not Enforced in Lambda Configuration

**Status**: Can accept HTTP URLs  
**Risk**: Bearer token exposure if misconfigured  
**Effort**: Low (1 hour)

**Quick Fix**: Add validation in `alexa_skill_backend.py`:

```python
# Add at module level (after imports)
def validate_configuration() -> None:
    """Validate Lambda environment configuration."""
    if not CALENDARBOT_ENDPOINT:
        raise ValueError("CALENDARBOT_ENDPOINT not set")
    
    # Enforce HTTPS (allow http://localhost for local testing only)
    if not CALENDARBOT_ENDPOINT.startswith("https://"):
        if not CALENDARBOT_ENDPOINT.startswith("http://localhost"):
            raise ValueError(
                f"CALENDARBOT_ENDPOINT must use https:// in production. "
                f"Got: {CALENDARBOT_ENDPOINT}"
            )
    
    if not CALENDARBOT_BEARER_TOKEN:
        raise ValueError("CALENDARBOT_BEARER_TOKEN not set")

# Call immediately
validate_configuration()
```

**Impact**: Prevents accidental HTTP configuration that would expose bearer token.

---

### 🟡 MEDIUM: No Timestamp Validation (Replay Attacks)

**Status**: Not implemented  
**Risk**: Captured requests can be replayed  
**Effort**: Low (2 hours) OR document as acceptable risk

**Quick Fix Option 1** - Add to `alexa_handlers.py`:

```python
from datetime import datetime, timezone

def check_auth(self, request: web.Request) -> None:
    """Check bearer token and timestamp."""
    # Existing bearer token check...
    
    # Add timestamp validation
    request_time_header = request.headers.get("X-Amzn-Request-Time")
    if request_time_header:
        try:
            request_timestamp = datetime.fromisoformat(
                request_time_header.replace('Z', '+00:00')
            )
            now = datetime.now(timezone.utc)
            age_seconds = (now - request_timestamp).total_seconds()
            
            if age_seconds > 150:  # Alexa's window
                raise AlexaAuthenticationError("Request too old")
        except ValueError:
            pass  # Invalid timestamp, continue (defense-in-depth)
```

**Quick Fix Option 2** - Document risk acceptance:

For personal deployment with HTTPS, the combination of:
- ✅ HTTPS encryption (prevents capture)
- ✅ Bearer token authentication
- ✅ Rate limiting

...provides adequate protection. Replay attacks require network access.

**Recommendation**: Document as acceptable risk OR implement for defense-in-depth.

---

## Current Security Strengths ✅

These controls are **already implemented and effective**:

1. **Bearer Token Authentication** - Strong 32-character tokens
2. **Rate Limiting** - 100 req/min per IP, 20 req/10s burst protection
3. **HTTPS Encryption** - Caddy with Let's Encrypt certificates
4. **URL Scheme Validation** - Prevents SSRF attacks
5. **Input Validation** - Pydantic models prevent injection
6. **SSL Certificate Verification** - Enabled for all HTTP clients
7. **Correlation ID Tracking** - Request tracing for security audits

---

## Quick Security Checklist

### Deployment Security

- [x] Strong bearer token generated with `secrets.token_urlsafe(32)`
- [x] Bearer token stored in environment variables (not in code)
- [x] HTTPS configured with valid Let's Encrypt certificate
- [x] Rate limiting enabled on Alexa endpoints
- [ ] ⚠️ Alexa signature verification implemented (if publishing)
- [ ] ⚠️ HTTPS enforcement in Lambda configuration
- [x] Firewall configured (Pi deployment)

### Configuration Security

```bash
# Verify secure configuration
✅ CALENDARBOT_ALEXA_BEARER_TOKEN set (32+ chars)
✅ CALENDARBOT_ICS_URL uses https://
✅ Caddy listens on port 443 (HTTPS)
✅ CalendarBot binds to 0.0.0.0:8080 (internal)
⚠️ Lambda CALENDARBOT_ENDPOINT uses https://
```

### Monitoring Security

```bash
# Check for attacks
curl http://localhost:8080/api/health | jq '.rate_limiting'
# Look for: high rejection_rate (> 5%)

# Check authentication failures
journalctl -u calendarbot-lite | grep "401\|Authentication failed"

# Check AWS Lambda logs
aws logs tail /aws/lambda/calendarbot-alexa-skill --follow
```

---

## Risk Acceptance for Personal Use

**If your CalendarBot is**:
- ✅ For personal use only (not published to Skills Store)
- ✅ Protected by strong bearer token
- ✅ Behind HTTPS with valid certificate
- ✅ Rate limited
- ✅ Monitored via logs

**Then current implementation is ACCEPTABLE** with these caveats:
1. Document that signature verification is not implemented
2. Monitor Lambda invocation logs for unexpected activity
3. Rotate bearer token if suspected compromise
4. Keep dependencies updated (`pip-audit`, `bandit`)

---

## Implementation Priority

**For Personal Deployment**:
```
Priority 1: ⚠️ Add HTTPS validation in Lambda (1 hour)
Priority 2: ℹ️ Document risk acceptance for signature verification
Priority 3: ℹ️ Optional: Add timestamp validation for defense-in-depth
```

**For Public/Certified Skill**:
```
Priority 1: 🔴 REQUIRED: Implement Alexa signature verification (4-8 hours)
Priority 2: ⚠️ Add HTTPS validation in Lambda (1 hour)
Priority 3: ⚠️ Add timestamp validation (2 hours)
Priority 4: ℹ️ Add security test suite
```

---

## Testing Your Security

### Quick Security Tests

```bash
# 1. Test authentication is enforced
curl https://ashwoodgrove.net/api/alexa/next-meeting
# Expected: 401 Unauthorized

# 2. Test rate limiting works
for i in {1..25}; do
  curl -H "Authorization: Bearer $TOKEN" https://ashwoodgrove.net/api/alexa/next-meeting
done
# Expected: 429 Too Many Requests after ~20 requests

# 3. Test HTTPS is working
curl -v https://ashwoodgrove.net/api/whats-next 2>&1 | grep "SSL"
# Expected: See SSL certificate info

# 4. Run security scanner
cd /home/runner/work/calendarBot/calendarBot
. venv/bin/activate
bandit -r calendarbot_lite/
# Expected: No high/critical issues
```

---

## When to Re-assess Security

**Triggers for security review**:
1. Publishing skill to Alexa Skills Store
2. Adding new users (beyond personal use)
3. Major dependency updates (Python, aiohttp, httpx)
4. Exposure of bearer token (requires rotation)
5. Unusual activity in Lambda/server logs
6. Every 6 months (routine review)

---

## Quick Reference Links

- **Full Security Assessment**: [ALEXA_LAMBDA_SECURITY_ASSESSMENT.md](ALEXA_LAMBDA_SECURITY_ASSESSMENT.md)
- **Rate Limiting Docs**: [RATE_LIMITING.md](RATE_LIMITING.md)
- **Deployment Guide**: [ALEXA_DEPLOYMENT_GUIDE.md](ALEXA_DEPLOYMENT_GUIDE.md)
- **Alexa Security Requirements**: [Amazon Developer Docs](https://developer.amazon.com/docs/custom-skills/host-a-custom-skill-as-a-web-service.html)
- **ASK SDK Python**: [GitHub](https://github.com/alexa/alexa-skills-kit-sdk-for-python)

---

## Support

**Questions about security**:
1. Review full assessment: `docs/ALEXA_LAMBDA_SECURITY_ASSESSMENT.md`
2. Check existing issues: Search "security" in GitHub issues
3. Run security scan: `bandit -r calendarbot_lite/`
4. Check logs for attacks: `journalctl -u calendarbot-lite | grep -i "auth\|401"`

---

**Last Updated**: November 8, 2025  
**Assessment**: Security Expert Agent  
**Status**: Production-ready for personal use (with documented risks)
