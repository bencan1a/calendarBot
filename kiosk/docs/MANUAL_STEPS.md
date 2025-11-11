# CalendarBot Kiosk - Manual Setup Steps

This document covers configuration steps that **cannot be automated** by the installation script and must be completed manually.

These steps are only required for **Section 3: Alexa Integration**. If you're only deploying the local kiosk (Sections 1+2), you can skip this document.

---

## Prerequisites

Before proceeding, ensure:
- ✅ The automated installer has completed successfully
- ✅ You have the bearer token generated during installation
- ✅ You have a domain name registered
- ✅ You have an Amazon Developer Account
- ✅ You have an AWS Account

---

## Step 1: Configure DNS

### What You Need
- Your domain name (e.g., `ashwoodgrove.net`)
- Your Raspberry Pi's public IP address

### Find Your Public IP

On your Raspberry Pi:
```bash
curl ifconfig.me
```

Example output: `203.0.113.45`

### Create DNS A Record

Log into your domain registrar (e.g., GoDaddy, Namecheap, Cloudflare) and create an A record:

| Field | Value |
|-------|-------|
| **Type** | A |
| **Name** | @ (for root domain) or subdomain |
| **Value** | Your public IP (e.g., `203.0.113.45`) |
| **TTL** | 300 (5 minutes recommended for testing) |

### Verify DNS Propagation

Wait 5-15 minutes, then test:

```bash
# Method 1: nslookup
nslookup ashwoodgrove.net

# Method 2: dig
dig ashwoodgrove.net +short

# Should return your public IP
```

**Note:** DNS propagation can take up to 24-48 hours globally, but typically completes within 15-30 minutes.

---

## Step 2: Configure Router Port Forwarding

### What You Need
- Access to your router's admin interface
- Your Raspberry Pi's **local IP address** (e.g., `192.168.1.100`)

### Find Your Pi's Local IP

```bash
hostname -I | awk '{print $1}'
```

Example output: `192.168.1.100`

### Configure Port Forwarding

Log into your router's admin interface (typically `192.168.1.1` or `192.168.0.1`) and create port forwarding rules:

| Service Name | External Port | Internal IP | Internal Port | Protocol |
|--------------|---------------|-------------|---------------|----------|
| CalendarBot-HTTP | 80 | 192.168.1.100 | 80 | TCP |
| CalendarBot-HTTPS | 443 | 192.168.1.100 | 443 | TCP |

**Important Notes:**
- Replace `192.168.1.100` with your Pi's actual local IP
- Some routers call this "Virtual Server" or "NAT Forwarding"
- Ensure rules are **enabled** after creation

### Common Router Admin URLs
- Netgear: `http://routerlogin.net`
- Linksys: `http://myrouter.local`
- TP-Link: `http://tplinkwifi.net`
- Generic: `http://192.168.1.1` or `http://192.168.0.1`

### Verify Port Forwarding

From an **external network** (e.g., mobile phone with WiFi disabled):

```bash
# Test HTTP (before HTTPS certificate)
curl http://YOUR_DOMAIN/health

# Should return JSON response from CalendarBot
```

---

## Step 3: Verify HTTPS Certificate Acquisition

The automated installer configures Caddy to automatically obtain HTTPS certificates from Let's Encrypt. However, this only works **after DNS and port forwarding are configured**.

### Monitor Certificate Acquisition

On your Raspberry Pi:

```bash
# Watch Caddy logs in real-time
sudo journalctl -u caddy -f

# Look for messages like:
# "certificate obtained successfully"
```

### Test HTTPS Access

From an **external network**:

```bash
# Test HTTPS with bearer token
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  https://ashwoodgrove.net/api/alexa/next-meeting

# Should return JSON event data
```

### Troubleshooting Certificate Issues

If certificates fail to acquire:

1. **Check DNS**: Ensure DNS points to your public IP
2. **Check Port 80**: Let's Encrypt requires port 80 for verification
3. **Check Firewall**: Ensure UFW allows ports 80, 443, and 8080
4. **Check Caddy Logs**: `sudo journalctl -u caddy -n 50`

**Rate Limits:** Let's Encrypt has a rate limit of **5 certificates per domain per week**. Use staging for testing:

```bash
# Edit Caddyfile to use staging (for testing only)
sudo nano /etc/caddy/Caddyfile

# Add after domain name:
ashwoodgrove.net {
    tls {
        ca https://acme-staging-v02.api.letsencrypt.org/directory
    }
    # ... rest of config
}

sudo systemctl reload caddy
```

**Remove staging configuration** before production use!

---

## Step 4: Deploy AWS Lambda Function

### Prerequisites
- AWS Account (free tier available)
- AWS CLI installed (optional, can use console)

### 4.1: Create Lambda Function

1. **Log into AWS Console**: https://console.aws.amazon.com/lambda/

2. **Create Function**:
   - Click **Create function**
   - Select: **Author from scratch**
   - Function name: `calendarbot-alexa-skill`
   - Runtime: **Python 3.11** or later
   - Architecture: **x86_64**
   - Click **Create function**

3. **Copy Lambda ARN**:
   - At the top of the page, copy the ARN (looks like):
     ```
     arn:aws:lambda:us-east-1:123456789012:function:calendarbot-alexa-skill
     ```
   - **Save this ARN** - you'll need it for the Alexa skill

### 4.2: Upload Lambda Code

**Option A: Console Upload**

1. Find the Lambda code in your repository:
   ```bash
   cat ~/calendarbot/calendarbot_lite/alexa_skill_backend.py
   ```

2. In AWS Console, scroll to **Code source**

3. Replace `lambda_function.py` content with the code from `alexa_skill_backend.py`

4. Click **Deploy**

**Option B: ZIP Upload** (for larger dependencies)

```bash
cd ~/calendarbot/calendarbot_lite
zip lambda_function.zip alexa_skill_backend.py

# Upload via console: Code source → Upload from → .zip file
```

### 4.3: Configure Environment Variables

1. In Lambda console, go to **Configuration** → **Environment variables**

2. Click **Edit** → **Add environment variable**

3. Add the following variables:

| Key | Value |
|-----|-------|
| `CALENDARBOT_ENDPOINT` | `https://ashwoodgrove.net` (no trailing slash) |
| `CALENDARBOT_BEARER_TOKEN` | Your bearer token from installation |
| `REQUEST_TIMEOUT` | `10` |

4. Click **Save**

### 4.4: Configure Timeout

1. Go to **Configuration** → **General configuration**
2. Click **Edit**
3. Set **Timeout** to: `10 seconds`
4. Click **Save**

### 4.5: Test Lambda Function

1. Go to **Test** tab

2. Create new test event:
   - Event name: `TestNextMeeting`
   - Template: **alexa-skills-kit-start-session** (or paste JSON below)

```json
{
  "version": "1.0",
  "session": {
    "new": true,
    "sessionId": "test-session",
    "application": {
      "applicationId": "test-app"
    },
    "user": {
      "userId": "test-user"
    }
  },
  "context": {},
  "request": {
    "type": "IntentRequest",
    "requestId": "test-request",
    "locale": "en-US",
    "timestamp": "2025-01-01T00:00:00Z",
    "intent": {
      "name": "GetNextMeetingIntent",
      "confirmationStatus": "NONE"
    }
  }
}
```

3. Click **Test**

4. **Expected Response**:
   ```json
   {
     "version": "1.0",
     "response": {
       "outputSpeech": {
         "type": "PlainText",
         "text": "Your next meeting is [EVENT NAME] at [TIME]"
       },
       "shouldEndSession": true
     }
   }
   ```

### Troubleshooting Lambda Issues

**Error: "Task timed out after 3.00 seconds"**
- Increase timeout to 10 seconds (see 4.4 above)
- Check network connectivity from Lambda to your domain

**Error: "401 Unauthorized"**
- Verify `CALENDARBOT_BEARER_TOKEN` matches .env file
- Check Caddyfile forwards Authorization header

**Error: "Connection refused"**
- Verify DNS and port forwarding are correct
- Test HTTPS endpoint from external network first

---

## Step 5: Create Alexa Skill

### Prerequisites
- Amazon Developer Account (free): https://developer.amazon.com/
- Lambda ARN from Step 4

### 5.1: Create Skill

1. **Log into Alexa Developer Console**: https://developer.amazon.com/alexa/console/ask

2. **Create Skill**:
   - Click **Create Skill**
   - Skill name: **Calendar Bot** (or your preferred name)
   - Primary locale: **English (US)**
   - Choose a model: **Custom**
   - Choose a method to host your skill's backend: **Provision your own**
   - Click **Create skill**

3. **Choose Template**:
   - Select: **Start from Scratch**
   - Click **Continue with template**

### 5.2: Configure Interaction Model

1. In the left sidebar, click **Interaction Model** → **JSON Editor**

2. Paste the following interaction model:

```json
{
  "interactionModel": {
    "languageModel": {
      "invocationName": "calendar bot",
      "intents": [
        {
          "name": "GetNextMeetingIntent",
          "slots": [],
          "samples": [
            "what's my next meeting",
            "tell me my next meeting",
            "what's next",
            "what's coming up",
            "what do I have next"
          ]
        },
        {
          "name": "GetTimeUntilNextMeetingIntent",
          "slots": [],
          "samples": [
            "how long until my next meeting",
            "when is my next meeting",
            "how much time do I have",
            "how much time until my next meeting"
          ]
        },
        {
          "name": "GetDoneForDayIntent",
          "slots": [],
          "samples": [
            "when am I done for the day",
            "when can I go home",
            "when is my last meeting",
            "when do I finish"
          ]
        },
        {
          "name": "AMAZON.CancelIntent",
          "samples": []
        },
        {
          "name": "AMAZON.HelpIntent",
          "samples": []
        },
        {
          "name": "AMAZON.StopIntent",
          "samples": []
        }
      ],
      "types": []
    }
  }
}
```

3. Click **Save Model**

4. Click **Build Model** (this may take 30-60 seconds)

5. Wait for "Model built successfully" message

### 5.3: Configure Endpoint

1. In the left sidebar, click **Endpoint**

2. Select: **AWS Lambda ARN**

3. **Default Region**: Paste your Lambda ARN from Step 4
   ```
   arn:aws:lambda:us-east-1:123456789012:function:calendarbot-alexa-skill
   ```

4. Click **Save Endpoints**

### 5.4: Add Lambda Trigger (Important!)

Go back to AWS Lambda console:

1. Open your `calendarbot-alexa-skill` function

2. Click **Add trigger**

3. Select: **Alexa Skills Kit**

4. **Skill ID Verification**: Disabled (for testing) or paste your Alexa Skill ID
   - To find Skill ID: Alexa Console → Your Skill → **View Skill ID** (top right)

5. Click **Add**

### 5.5: Enable Testing

1. In Alexa Console, click **Test** tab

2. Change **Skill testing is enabled in**: **Development**

### 5.6: Test in Simulator

In the Alexa Simulator (Test tab), type or speak:

```
ask calendar bot what's my next meeting
```

**Expected Response**: Alexa should speak your next calendar event

**Additional Test Phrases**:
```
ask calendar bot how long until my next meeting
ask calendar bot when am I done for the day
```

### 5.7: Test on Physical Alexa Device

If you have an Alexa device registered to the same Amazon account:

1. Say: **"Alexa, ask Calendar Bot what's my next meeting"**

2. Alexa should respond with your next event

**Note:** Skills in Development mode are only available to the account that created them.

### Troubleshooting Alexa Skill Issues

**"There was a problem with the requested skill's response"**
- Check Lambda logs: AWS Console → Lambda → Monitor → View logs in CloudWatch
- Verify Lambda test works before testing Alexa skill
- Check endpoint ARN is correct

**"Calendar Bot isn't responding"**
- Verify skill testing is enabled
- Rebuild interaction model
- Check Lambda trigger is configured

**Response is delayed or times out**
- Increase Lambda timeout to 10 seconds
- Check network latency to your domain
- Verify CalendarBot service is running on Pi

**Wrong calendar data**
- Verify `CALENDARBOT_ICS_URL` in .env is correct
- Check CalendarBot API directly: `curl https://YOUR_DOMAIN/api/alexa/next-meeting -H "Authorization: Bearer TOKEN"`

---

## Step 6: Verify Complete Alexa Integration

### End-to-End Test Flow

1. **Test CalendarBot API locally** (on Pi):
   ```bash
   curl -s http://localhost:8080/api/alexa/next-meeting | jq
   ```
   Should return JSON event data

2. **Test via HTTPS with authentication** (from external network):
   ```bash
   curl -s -H "Authorization: Bearer YOUR_TOKEN" \
     https://ashwoodgrove.net/api/alexa/next-meeting | jq
   ```
   Should return same JSON data

3. **Test Lambda function** (AWS Console):
   - Use test event from Step 4.5
   - Should return Alexa response with event data

4. **Test Alexa skill** (Developer Console):
   - Type: "ask calendar bot what's my next meeting"
   - Should return spoken response

5. **Test physical Alexa device**:
   - Say: "Alexa, ask Calendar Bot what's my next meeting"
   - Should speak your next event

### Monitoring Alexa Requests

**On Raspberry Pi** (watch CalendarBot logs):
```bash
sudo journalctl -u calendarbot-lite@USERNAME.service -f
```

**In AWS** (watch Lambda logs):
- AWS Console → Lambda → Monitor → View logs in CloudWatch

**Test Bearer Token Security**:
```bash
# Without token (should fail with 401)
curl -s https://ashwoodgrove.net/api/alexa/next-meeting

# With token (should succeed with 200)
curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  https://ashwoodgrove.net/api/alexa/next-meeting
```

---

## Security Considerations

### Bearer Token Security

- ✅ **Never commit bearer tokens to git**
- ✅ Store token securely (password manager, AWS Secrets Manager)
- ✅ Rotate token periodically (every 90 days recommended)
- ✅ Use HTTPS only (never HTTP for authenticated endpoints)

### Rotating Bearer Token

If you need to change the bearer token:

1. **Generate new token** (on Pi):
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update CalendarBot .env**:
   ```bash
   nano ~/calendarbot/.env
   # Update CALENDARBOT_ALEXA_BEARER_TOKEN
   sudo systemctl restart calendarbot-lite@USERNAME.service
   ```

3. **Update AWS Lambda environment variables**:
   - AWS Console → Lambda → Configuration → Environment variables
   - Update `CALENDARBOT_BEARER_TOKEN`
   - Click Save

4. **Test end-to-end** to verify

### Firewall Best Practices

- ✅ Only expose ports 80 (HTTP) and 443 (HTTPS)
- ✅ Keep SSH port 22 open for remote management
- ✅ Consider using non-standard SSH port (e.g., 2222)
- ✅ Enable fail2ban for SSH brute-force protection

---

## Certificate Renewal

Caddy automatically renews Let's Encrypt certificates **30 days before expiration**. No manual intervention required.

### Verify Auto-Renewal

```bash
# Check certificate expiration
echo | openssl s_client -connect ashwoodgrove.net:443 2>/dev/null | \
  openssl x509 -noout -dates

# Check Caddy renewal logs
sudo journalctl -u caddy | grep -i "renew"
```

### Manual Certificate Renewal (if needed)

```bash
# Reload Caddy to trigger renewal check
sudo systemctl reload caddy

# Watch logs
sudo journalctl -u caddy -f
```

---

## Deployment Checklist

Use this checklist to verify all manual steps are complete:

- [ ] DNS A record created and verified
- [ ] Router port forwarding configured (80, 443)
- [ ] HTTPS certificate acquired successfully
- [ ] Bearer token saved securely
- [ ] AWS Lambda function created and tested
- [ ] Lambda environment variables configured
- [ ] Lambda timeout set to 10 seconds
- [ ] Alexa skill created
- [ ] Interaction model uploaded and built
- [ ] Endpoint configured with Lambda ARN
- [ ] Lambda trigger added for Alexa Skills Kit
- [ ] Skill testing enabled
- [ ] Tested in Alexa simulator
- [ ] Tested on physical Alexa device
- [ ] End-to-end flow verified
- [ ] Bearer token security verified

---

## Support

### Useful Log Commands

```bash
# CalendarBot service logs
sudo journalctl -u calendarbot-lite@USERNAME.service -f

# Caddy logs
sudo journalctl -u caddy -f

# Watchdog logs
sudo journalctl -u calendarbot-kiosk-watchdog@USERNAME.service -f

# System logs (all CalendarBot services)
sudo journalctl -u calendarbot-* -f
```

### Useful Test Commands

```bash
# Test local API
curl http://localhost:8080/health

# Test HTTPS (external)
curl -s https://ashwoodgrove.net/health | jq

# Test authenticated endpoint
curl -s -H "Authorization: Bearer TOKEN" \
  https://ashwoodgrove.net/api/alexa/next-meeting | jq

# Check DNS
dig ashwoodgrove.net +short

# Check certificate
echo | openssl s_client -connect ashwoodgrove.net:443 2>/dev/null | \
  openssl x509 -noout -text

# Check service status
sudo systemctl status calendarbot-lite@USERNAME.service
sudo systemctl status caddy
```

### Common Issues

See [3_ALEXA_INTEGRATION.md](3_ALEXA_INTEGRATION.md) for detailed troubleshooting guides.

---

**Last Updated**: 2025-11-03
**Automated Installer Version**: 1.0.0
