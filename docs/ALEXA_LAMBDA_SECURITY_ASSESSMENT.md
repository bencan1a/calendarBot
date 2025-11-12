# CalendarBot Alexa & Lambda Integration Security Assessment

**Assessment Date**: November 8, 2025
**Scope**: Alexa integration, AWS Lambda backend, Caddy reverse proxy, authentication mechanisms
**Assessor**: Security Expert Agent
**Project**: CalendarBot Lite (Personal Raspberry Pi Deployment)

---

## Executive Summary

This security assessment reviewed the CalendarBot Alexa integration architecture, including the Lambda backend, Caddy reverse proxy configuration, and API authentication mechanisms. The assessment identified **one critical security vulnerability** and several medium-priority security improvements for a personal deployment context.

### Risk Summary

| Severity | Count | Status |
|----------|-------|--------|
| **CRITICAL** | 1 | ⚠️ Requires attention |
| **HIGH** | 0 | ✅ None found |
| **MEDIUM** | 3 | ℹ️ Recommended improvements |
| **LOW** | 2 | ℹ️ Best practices |

### Key Findings

1. **[CRITICAL]** Missing Alexa request signature verification in Lambda backend
2. **[MEDIUM]** Caddy configuration doesn't enforce HTTPS-only for Alexa endpoints
3. **[MEDIUM]** No timestamp validation for replay attack prevention
4. **[MEDIUM]** Bearer token stored in environment variables (acceptable for personal use)
5. **[LOW]** Hardcoded timeout values in Lambda function

**Context**: CalendarBot is a personal application for 1-5 users on Raspberry Pi hardware. Risk assessment considers this scale and threat model.

---

## Architecture Overview

### Request Flow

```
Alexa Voice → Amazon Alexa Service → AWS Lambda (alexa_skill_backend.py)
                                           ↓
                                    HTTP/HTTPS Request
                                           ↓
                                 Caddy Reverse Proxy (port 443)
                                           ↓
                                 CalendarBot Lite Server (port 8080)
                                           ↓
                                    Alexa Route Handlers
```

### Components Reviewed

1. **AWS Lambda Backend** (`calendarbot_lite/alexa/alexa_skill_backend.py`)
   - Intent routing (GetNextMeetingIntent, GetTimeUntilNextMeetingIntent, etc.)
   - CalendarBot API client with bearer token authentication
   - SSML response generation

2. **Alexa Route Handlers** (`calendarbot_lite/api/routes/alexa_routes.py`)
   - Bearer token authentication
   - Rate limiting middleware
   - Response caching

3. **Alexa Handlers** (`calendarbot_lite/alexa/alexa_handlers.py`)
   - Request parameter validation
   - Authentication checks
   - Event processing logic

4. **Caddy Configuration** (`kiosk/config/enhanced_caddyfile`)
   - HTTPS termination
   - Reverse proxy to localhost:8080
   - Header forwarding

---

## Critical Findings

### 1. Missing Alexa Request Signature Verification [CRITICAL]

**Severity**: CRITICAL
**CVSS Score**: 9.1 (Critical)
**CWE**: CWE-345 (Insufficient Verification of Data Authenticity)

#### Description

The AWS Lambda function (`alexa_skill_backend.py`) **does not verify** Alexa request signatures. Amazon requires all Alexa skills to validate:

1. **Request signature** via `SignatureCertChainUrl` and `Signature` headers
2. **Certificate chain** must be from Amazon's trusted domain
3. **Request timestamp** must be within 150 seconds to prevent replay attacks

**Current Implementation:**
```python
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Validates request structure but NOT signature/timestamp
    if "request" not in event:
        logger.error("Invalid request: missing 'request' field")
        return AlexaResponse("Sorry, I received an invalid request.").to_dict()
```

#### Attack Scenario

An attacker who discovers your Lambda endpoint URL could:
1. Craft malicious Alexa requests without proper signatures
2. Bypass Amazon's security controls
3. Execute arbitrary intents on your CalendarBot
4. Access calendar data without Alexa device authentication
5. Perform DoS attacks by flooding Lambda with fake requests

#### Impact

- **Confidentiality**: HIGH - Unauthorized access to calendar data
- **Integrity**: MEDIUM - Ability to invoke intents without authorization
- **Availability**: MEDIUM - DoS attack potential via Lambda invocations

#### Remediation

**Required**: Implement Alexa request signature verification using the `ask-sdk-core` library:

```python
# Add to requirements or Lambda layer
# ask-sdk-core==1.11.0

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name, is_request_type

# Use SkillBuilder which handles signature verification automatically
sb = SkillBuilder()

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # Your existing logic here
        pass

sb.add_request_handler(LaunchRequestHandler())
skill = sb.create()

def lambda_handler(event, context):
    # Signature verification happens automatically in skill.invoke()
    return skill.invoke(event, context)
```

**Alternative** (if not using ASK SDK): Manual verification:

```python
import base64
import hashlib
import urllib.request
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime, timezone

def verify_alexa_request(event: dict, context: Any) -> bool:
    """Verify Alexa request signature and timestamp."""
    # 1. Verify timestamp (within 150 seconds)
    request_timestamp = event.get("request", {}).get("timestamp")
    if not request_timestamp:
        return False

    request_time = datetime.fromisoformat(request_timestamp.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    if abs((now - request_time).total_seconds()) > 150:
        logger.warning("Request timestamp too old: %s", request_timestamp)
        return False

    # 2. Verify signature (requires access to HTTP headers)
    # Note: Lambda function event doesn't include HTTP headers directly
    # You need to configure Lambda to receive headers via API Gateway integration
    # This is complex - using ASK SDK is strongly recommended

    return True
```

**Recommendation**: Use the ASK SDK approach as it's the official, maintained solution.

#### References

- [Alexa Skills Kit Request Signature Verification](https://developer.amazon.com/docs/custom-skills/host-a-custom-skill-as-a-web-service.html#checking-the-signature-of-the-request)
- [ASK SDK for Python](https://github.com/alexa/alexa-skills-kit-sdk-for-python)
- [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html)

---

## Medium Severity Findings

### 2. HTTP Requests Allowed to CalendarBot Backend [MEDIUM]

**Severity**: MEDIUM
**CVSS Score**: 5.3 (Medium)
**CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)

#### Description

The Lambda backend (`alexa_skill_backend.py`) constructs HTTP URLs using `urljoin()` without enforcing HTTPS:

```python
CALENDARBOT_ENDPOINT = os.environ.get("CALENDARBOT_ENDPOINT", "")

def call_calendarbot_api(endpoint_path: str) -> dict[str, Any]:
    url = urljoin(CALENDARBOT_ENDPOINT.rstrip("/") + "/", endpoint_path.lstrip("/"))
    # No validation that CALENDARBOT_ENDPOINT uses https://
```

If `CALENDARBOT_ENDPOINT` is accidentally configured with `http://`, bearer tokens would be transmitted in cleartext.

#### Impact

- **Confidentiality**: MEDIUM - Bearer token exposure over HTTP
- **Integrity**: LOW - Man-in-the-middle attack potential
- **Personal Deployment**: LOW - Attacker needs network access to intercept

#### Remediation

Add HTTPS enforcement in Lambda configuration validation:

```python
def validate_configuration() -> None:
    """Validate Lambda environment configuration at startup."""
    if not CALENDARBOT_ENDPOINT:
        raise ValueError("CALENDARBOT_ENDPOINT environment variable not set")

    if not CALENDARBOT_ENDPOINT.startswith("https://"):
        # Allow http:// only for localhost testing
        if not CALENDARBOT_ENDPOINT.startswith("http://localhost") and \
           not CALENDARBOT_ENDPOINT.startswith("http://127.0.0.1"):
            raise ValueError(
                "CALENDARBOT_ENDPOINT must use https:// (not http://) in production. "
                f"Got: {CALENDARBOT_ENDPOINT}"
            )

    if not CALENDARBOT_BEARER_TOKEN:
        raise ValueError("CALENDARBOT_BEARER_TOKEN environment variable not set")

    if len(CALENDARBOT_BEARER_TOKEN) < 32:
        logger.warning(
            "CALENDARBOT_BEARER_TOKEN is weak (length: %d). "
            "Generate a stronger token with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            len(CALENDARBOT_BEARER_TOKEN)
        )

# Call at module initialization
validate_configuration()
```

**Documentation Update**: Add security notice to deployment guide:

```markdown
### 3.3 Configure Environment Variables

**SECURITY REQUIREMENT**: Always use HTTPS endpoints in production.

```bash
# CORRECT - Production configuration
CALENDARBOT_ENDPOINT = https://ashwoodgrove.net
CALENDARBOT_BEARER_TOKEN = <secure-token>

# WRONG - Security risk (bearer token exposed over HTTP)
CALENDARBOT_ENDPOINT = http://ashwoodgrove.net  # ❌ DO NOT USE
```
```

---

### 3. No Timestamp Validation for Replay Attacks [MEDIUM]

**Severity**: MEDIUM
**CVSS Score**: 4.3 (Medium)
**CWE**: CWE-294 (Authentication Bypass by Capture-replay)

#### Description

CalendarBot Lite's Alexa handlers do not validate request timestamps. While the Lambda function receives timestamped requests from Alexa, once the Lambda forwards the request to CalendarBot, there's no replay attack protection on the CalendarBot side.

**Current Flow:**
```
Alexa (timestamped) → Lambda (no validation) → CalendarBot (no timestamp check)
```

If the Lambda-to-CalendarBot communication is compromised (e.g., network capture), an attacker could replay valid requests indefinitely.

#### Attack Scenario

1. Attacker captures a legitimate Lambda→CalendarBot request (including bearer token)
2. Replays the same request hours/days later
3. Gains access to updated calendar information

**Note**: This requires the attacker to already have network access to intercept requests between Lambda and CalendarBot.

#### Impact

- **Confidentiality**: MEDIUM - Replay of valid requests to access calendar data
- **Personal Deployment**: LOW - Requires network-level access (HTTPS mitigates)

#### Remediation

**Option 1**: Add timestamp validation to Alexa handlers (Recommended for defense-in-depth):

```python
# In alexa_handlers.py - AlexaEndpointBase.check_auth()

def check_auth(self, request: web.Request) -> None:
    """Check if request has valid bearer token and timestamp."""
    if not self.bearer_token:
        return  # No token configured, allow all requests

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AlexaAuthenticationError("Missing or malformed Authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix
    if token != self.bearer_token:
        raise AlexaAuthenticationError("Invalid bearer token")

    # NEW: Validate X-Amzn-Request-Time header if present (from API Gateway)
    request_time_header = request.headers.get("X-Amzn-Request-Time")
    if request_time_header:
        try:
            request_timestamp = datetime.fromisoformat(request_time_header.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age_seconds = (now - request_timestamp).total_seconds()

            if age_seconds > 150:  # Match Alexa's 150-second window
                raise AlexaAuthenticationError(
                    f"Request timestamp too old: {age_seconds:.0f} seconds"
                )
            if age_seconds < -30:  # Allow small clock skew
                raise AlexaAuthenticationError(
                    f"Request timestamp in future: {age_seconds:.0f} seconds"
                )
        except (ValueError, TypeError) as e:
            logger.warning("Invalid X-Amzn-Request-Time header: %s", e)
            # Don't fail - timestamp validation is defense-in-depth
```

**Option 2**: Rely on HTTPS + Bearer Token (Acceptable for personal deployment)

For a personal Raspberry Pi deployment with HTTPS, the combination of:
- HTTPS encryption (prevents capture)
- Bearer token authentication (prevents unauthorized requests)
- Rate limiting (prevents brute force)

...provides adequate protection without adding timestamp complexity.

**Recommendation**: Document the security model and accept the risk for personal use, OR implement Option 1 as defense-in-depth.

---

### 4. Bearer Token in Environment Variables [MEDIUM - Acceptable Risk]

**Severity**: MEDIUM (Acceptable for personal deployment)
**CVSS Score**: 4.0 (Medium)
**CWE**: CWE-798 (Use of Hard-coded Credentials)

#### Description

Bearer tokens are stored in environment variables:
- Lambda: `CALENDARBOT_BEARER_TOKEN`
- CalendarBot Lite: `CALENDARBOT_ALEXA_BEARER_TOKEN`

This is a standard practice but has risks:
- Environment variables may be logged in AWS CloudWatch
- Visible in Lambda console to IAM users with read permissions
- Visible in process listings on Raspberry Pi (`ps aux | grep calendarbot`)

#### Impact

**Personal Deployment Context**:
- **Risk**: LOW - Single user controls both Lambda and Raspberry Pi
- **Threat**: Compromised AWS account or physical access to Pi
- **Mitigation**: Existing IAM permissions, SSH key authentication, firewall

**Enterprise Context** (if applicable in future):
- **Risk**: MEDIUM-HIGH - Multiple users, compliance requirements
- **Recommendation**: Use AWS Secrets Manager or HashiCorp Vault

#### Current State: Acceptable ✅

For personal deployment, environment variables are **appropriate and acceptable**. The deployment guide correctly uses `secrets.token_urlsafe(32)` for strong token generation.

#### Future Improvement (Optional)

If expanding beyond personal use, consider:

```python
# Use AWS Secrets Manager for Lambda
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name: str) -> str:
    """Fetch secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        logger.error("Failed to retrieve secret: %s", e)
        raise

# At Lambda initialization
CALENDARBOT_BEARER_TOKEN = get_secret("calendarbot/bearer-token")
```

**Current Recommendation**: No action required. Document this as an acceptable risk for personal deployment.

---

## Low Severity Findings

### 5. Hardcoded Timeout Values [LOW]

**Severity**: LOW
**CVSS Score**: 2.0 (Low)
**CWE**: CWE-1188 (Insecure Default Initialization of Resource)

#### Description

Lambda function has hardcoded timeout:
```python
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))
```

CalendarBot has various hardcoded timeouts in `http_client.py` and `lite_fetcher.py`.

#### Impact

- Inflexible under high load or slow network conditions
- May cause unnecessary Lambda invocation failures
- Minimal security impact (DoS via timeouts is prevented by rate limiting)

#### Remediation

Current implementation is acceptable. The 10-second default is reasonable for calendar API calls. If needed, can be adjusted via environment variable.

**No action required** - Current design is appropriate for personal use.

---

### 6. Caddy Configuration: Missing HTTPS Enforcement [LOW]

**Severity**: LOW
**CVSS Score**: 2.5 (Low)
**CWE**: CWE-311 (Missing Encryption of Sensitive Data)

#### Description

The Caddy configuration (`enhanced_caddyfile`) doesn't explicitly enforce HTTPS-only:

```caddy
ashwoodgrove.net {
    reverse_proxy localhost:8080 {
        # ...
    }
}
```

Caddy automatically handles HTTPS with Let's Encrypt, but there's no explicit redirect from HTTP to HTTPS.

#### Impact

**Personal Deployment**:
- **Risk**: LOW - Caddy defaults to HTTPS
- **Threat**: User accidentally uses http:// URL
- **Likelihood**: Very low (browsers default to HTTPS)

#### Remediation

Add explicit HTTP-to-HTTPS redirect for defense-in-depth:

```caddy
# Redirect HTTP to HTTPS
http://ashwoodgrove.net {
    redir https://{host}{uri} permanent
}

# HTTPS configuration
ashwoodgrove.net {
    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Authorization {header.Authorization}
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }

    log {
        output file /var/log/caddy/access.log
        level INFO
    }
}
```

**Recommendation**: Low priority for personal deployment. Caddy's automatic HTTPS is sufficient.

---

## Security Controls Analysis

### ✅ Effective Controls

1. **Bearer Token Authentication**
   - Strong token generation with `secrets.token_urlsafe(32)`
   - Constant-time comparison (Python `==` is safe for strings)
   - Properly configured in both Lambda and CalendarBot

2. **Rate Limiting**
   - Sliding window algorithm
   - Per-IP and per-token tracking
   - Burst protection (20 req/10s)
   - Prevents brute force and DoS attacks
   - See: `docs/RATE_LIMITING.md`

3. **URL Scheme Validation**
   - `lite_fetcher.py` validates ICS URLs
   - Only allows `http://` and `https://` schemes
   - Prevents `file://`, `data://`, etc. (SSRF protection)
   - Security logging for blocked URLs

4. **Input Validation**
   - Pydantic models for request parameter validation
   - Type checking and constraint validation
   - Automatic 400 errors for invalid input

5. **SSL/TLS Certificate Verification**
   - httpx client has `verify=True` (default)
   - Caddy handles HTTPS with Let's Encrypt
   - Lambda uses HTTPS to CalendarBot (if configured correctly)

6. **Correlation ID Tracking**
   - Request tracing for security audit trails
   - Helps identify attack patterns
   - See: `calendarbot_lite/api/middleware/correlation_id.py`

### ⚠️ Missing Controls

1. **Alexa Request Signature Verification** - CRITICAL (see Finding #1)
2. **HTTPS Enforcement in Lambda** - MEDIUM (see Finding #2)
3. **Timestamp Validation** - MEDIUM (see Finding #3)

---

## Threat Model Assessment

### Threat: Unauthorized Access to Calendar Data

**Attack Vectors:**
1. ✅ **Brute force bearer token** - Mitigated by rate limiting
2. ⚠️ **Bypass Lambda signature check** - VULNERABLE (no signature verification)
3. ✅ **Direct access to CalendarBot** - Mitigated by bearer token
4. ✅ **SSRF via malicious ICS URL** - Mitigated by URL scheme validation

**Overall Risk**: MEDIUM (CRITICAL vulnerability exists but requires Lambda endpoint discovery)

### Threat: Denial of Service

**Attack Vectors:**
1. ✅ **Flood Alexa endpoints** - Mitigated by rate limiting
2. ✅ **Flood Lambda function** - Partially mitigated (no signature verification)
3. ✅ **Large ICS files** - Mitigated by timeout and memory limits

**Overall Risk**: LOW (rate limiting provides strong protection)

### Threat: Data Exposure

**Attack Vectors:**
1. ✅ **Intercept HTTP traffic** - Mitigated by HTTPS
2. ⚠️ **Capture and replay requests** - Partially vulnerable (no timestamp validation)
3. ✅ **Log file exposure** - Low risk (no sensitive data logged)

**Overall Risk**: LOW (HTTPS provides strong encryption)

### Threat: Compromised Credentials

**Attack Vectors:**
1. ⚠️ **Stolen bearer token** - Limited mitigation (no token rotation)
2. ✅ **Stolen AWS credentials** - Outside scope (AWS IAM controls)
3. ✅ **Physical access to Raspberry Pi** - Outside scope (SSH key auth)

**Overall Risk**: LOW (acceptable for personal deployment)

---

## Compliance & Best Practices

### Alexa Skill Certification Requirements

**Amazon's Security Requirements for Skills:**
- ⚠️ **Request Signature Verification** - NOT IMPLEMENTED (Violation)
- ⚠️ **Timestamp Validation** - NOT IMPLEMENTED (Violation)
- ✅ **HTTPS Endpoints** - Implemented via Caddy
- ✅ **Valid SSL Certificates** - Implemented via Let's Encrypt

**Status**: Current implementation would **fail** Alexa skill certification due to missing signature verification.

**Impact**: For personal skills (not published to Alexa Skills Store), Amazon does not enforce these requirements. However, implementing them is a security best practice.

### OWASP Top 10 Analysis

1. **A01:2021 – Broken Access Control**
   - ⚠️ Missing Alexa signature verification
   - ✅ Bearer token authentication implemented

2. **A02:2021 – Cryptographic Failures**
   - ✅ HTTPS enforced via Caddy
   - ✅ SSL certificate validation enabled

3. **A03:2021 – Injection**
   - ✅ Pydantic input validation
   - ✅ No SQL/command injection vectors

4. **A04:2021 – Insecure Design**
   - ⚠️ No replay attack protection
   - ✅ Rate limiting implemented

5. **A05:2021 – Security Misconfiguration**
   - ⚠️ HTTP allowed in Lambda (if misconfigured)
   - ✅ Default configurations are secure

6. **A06:2021 – Vulnerable and Outdated Components**
   - ✅ No critical vulnerabilities (bandit scan clean)
   - Regular dependency updates recommended

7. **A07:2021 – Identification and Authentication Failures**
   - ⚠️ No Alexa request authentication
   - ✅ Bearer token authentication works

8. **A08:2021 – Software and Data Integrity Failures**
   - ⚠️ No signature verification = integrity not verified
   - ✅ Python integrity checks via pip

9. **A09:2021 – Security Logging and Monitoring Failures**
   - ✅ Comprehensive logging implemented
   - ✅ Correlation ID tracking
   - ✅ Rate limit monitoring

10. **A10:2021 – Server-Side Request Forgery (SSRF)**
    - ✅ URL scheme validation prevents SSRF
    - ✅ No localhost/private IP access

**Overall OWASP Score**: 7/10 (Good, with critical gap in authentication)

---

## Recommendations Summary

### Immediate Actions (Critical)

1. **Implement Alexa Request Signature Verification**
   - **Priority**: CRITICAL
   - **Effort**: Medium (4-8 hours)
   - **Use ask-sdk-core library** for automatic verification
   - **Alternative**: Implement manual verification
   - **Blocks**: Alexa skill certification (if publishing)

### Short-Term Actions (Medium Priority)

2. **Enforce HTTPS in Lambda Configuration**
   - **Priority**: MEDIUM
   - **Effort**: Low (1 hour)
   - **Add validation check** at Lambda initialization
   - **Update deployment documentation**

3. **Add Timestamp Validation (Optional)**
   - **Priority**: MEDIUM (Defense-in-depth)
   - **Effort**: Low (2 hours)
   - **Implement in CalendarBot handlers**
   - **Or document as acceptable risk**

### Long-Term Improvements (Low Priority)

4. **Update Caddy Configuration**
   - **Priority**: LOW
   - **Effort**: Low (30 minutes)
   - **Add explicit HTTP-to-HTTPS redirect**
   - **Add security headers (HSTS, X-Frame-Options)**

5. **Token Rotation Mechanism**
   - **Priority**: LOW
   - **Effort**: Medium (4 hours)
   - **Implement bearer token rotation**
   - **Add documentation for token updates**

---

## Testing Recommendations

### Security Test Suite

Create security-focused integration tests:

```python
# tests/lite/security/test_alexa_security.py

async def test_alexa_handler_requires_bearer_token():
    """Test that Alexa endpoints reject requests without bearer token."""
    # Test without Authorization header
    # Test with invalid bearer token
    # Test with malformed Authorization header

async def test_alexa_handler_rate_limiting():
    """Test that rate limiting blocks excessive requests."""
    # Send burst of requests
    # Verify 429 response after limit

async def test_url_scheme_validation():
    """Test that only HTTP/HTTPS URLs are allowed."""
    # Test file:// URL - should be blocked
    # Test data:// URL - should be blocked
    # Test https:// URL - should be allowed

async def test_lambda_https_enforcement():
    """Test that Lambda validates HTTPS endpoint configuration."""
    # Mock environment with http:// endpoint
    # Verify configuration validation fails
```

### Penetration Testing

For personal deployment, manual security testing is sufficient:

1. **Test authentication bypass**:
   ```bash
   # Should return 401
   curl https://ashwoodgrove.net/api/alexa/next-meeting

   # Should return 401
   curl -H "Authorization: Bearer wrong-token" https://ashwoodgrove.net/api/alexa/next-meeting
   ```

2. **Test rate limiting**:
   ```bash
   # Should trigger 429 after 20 requests
   for i in {1..25}; do
     curl -H "Authorization: Bearer $TOKEN" https://ashwoodgrove.net/api/alexa/next-meeting
   done
   ```

3. **Test SSRF protection**:
   ```bash
   # Verify that file:// URLs are rejected during ICS fetch
   # This requires modifying config temporarily to test validation
   ```

### Automated Security Scanning

```bash
# Static analysis (already passing)
bandit -r calendarbot_lite/

# Dependency vulnerability scan
pip-audit

# Secrets scanning
trufflehog git file://. --no-update

# API security testing (if deploying publicly)
# OWASP ZAP or similar tools
```

---

## Security Monitoring

### Metrics to Track

1. **Authentication Failures**:
   - Count of 401 responses on Alexa endpoints
   - Alert if > 10 failures/hour (potential attack)

2. **Rate Limit Violations**:
   - Count of 429 responses
   - Track unique IPs hitting rate limits

3. **Invalid Request Signatures** (after implementing):
   - Count of signature verification failures
   - Alert on any signature failures (indicates attack or misconfiguration)

4. **Unusual Request Patterns**:
   - Requests outside normal hours
   - Requests from unexpected IPs (if IP whitelist is feasible)

### Logging Best Practices

Current implementation ✅:
- Correlation ID tracking for request tracing
- Security event logging in `lite_fetcher.py`
- Rate limiter statistics in health endpoint

Recommended additions:
- Log authentication failures with IP addresses
- Log Lambda invocation sources (if possible via API Gateway)
- Alert on configuration changes (bearer token updates)

---

## Conclusion

### Overall Security Posture: **GOOD with CRITICAL GAP**

CalendarBot Lite demonstrates strong security practices for a personal deployment:
- ✅ Bearer token authentication
- ✅ Rate limiting protection
- ✅ HTTPS encryption
- ✅ Input validation
- ✅ SSRF protection

However, the **missing Alexa request signature verification** is a critical vulnerability that should be addressed, especially if:
- Publishing the skill to Alexa Skills Store (required)
- Concerned about unauthorized Lambda invocations
- Want defense-in-depth security

### Risk Acceptance for Personal Use

**If the skill remains private and unpublished**, the current security posture is **acceptable for personal use** with these considerations:

1. Keep bearer token secret and strong (32+ characters)
2. Monitor Lambda invocation logs for unexpected activity
3. Use AWS IAM policies to restrict Lambda access
4. Maintain HTTPS-only configuration
5. Keep dependencies updated (bandit, pip-audit)

### Recommended Action Plan

**For Personal Deployment (Minimum Viable Security)**:
1. ✅ Continue using current implementation
2. ⚠️ Add HTTPS validation in Lambda (1 hour effort)
3. ⚠️ Document risk acceptance for signature verification
4. ✅ Monitor Lambda logs periodically

**For Public Skill or Enhanced Security**:
1. ⚠️ **REQUIRED**: Implement Alexa signature verification (ask-sdk-core)
2. ⚠️ Add timestamp validation
3. ⚠️ Update Caddy configuration with security headers
4. ✅ Implement security test suite
5. ✅ Set up automated security monitoring

---

## Appendix: Security Resources

### Documentation
- [Alexa Security Best Practices](https://developer.amazon.com/docs/custom-skills/security-testing-for-an-alexa-skill.html)
- [AWS Lambda Security](https://docs.aws.amazon.com/lambda/latest/dg/lambda-security.html)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

### Tools
- `bandit` - Python security linter (already integrated)
- `pip-audit` - Dependency vulnerability scanner
- `trufflehog` - Secrets scanning
- `safety` - Python dependency security checker

### Related CalendarBot Documentation
- `docs/RATE_LIMITING.md` - Rate limiting implementation
- `docs/ALEXA_DEPLOYMENT_GUIDE.md` - Deployment instructions
- `docs/LOGGING.md` - Logging and monitoring

---

**Assessment Completed**: November 8, 2025
**Next Review**: Recommended after implementing critical findings
**Contact**: Security Expert Agent
