# Section 3: Alexa Integration

Set up complete Alexa voice integration with HTTPS reverse proxy, AWS Lambda backend, and Alexa skill.

**Estimated Time**: 60-90 minutes
**Prerequisites**:
- Section 1 completed (CalendarBot service running)
- Domain name registered and accessible
- Router port forwarding configured (or public IP directly on Pi)
- Amazon Developer Account (free)
- AWS Account for Lambda deployment (free tier available)

---

## What You'll Install

By the end of this section, you'll have:

- ✅ **HTTPS Reverse Proxy** - Caddy with automatic Let's Encrypt certificates
- ✅ **Bearer Token Authentication** - Secure API access for Alexa
- ✅ **AWS Lambda Function** - Alexa skill backend
- ✅ **Alexa Skill** - Voice interface with 3 intents
- ✅ **DNS Configuration** - Domain pointing to your Pi
- ✅ **Firewall Rules** - HTTP/HTTPS access configured
- ✅ **End-to-End Testing** - Verified voice commands

**Services Added**: 1 (`caddy.service`)

---

## Supported Alexa Commands

CalendarBot Lite supports the following voice commands through Alexa:

### GetNextMeetingIntent
- **Sample phrases:** "What's my next meeting?", "Tell me my next meeting", "What meeting do I have next?"
- **Function:** Returns details about your upcoming meeting including subject, start time, and duration
- **API Endpoint:** `/api/alexa/next-meeting`

### GetTimeUntilNextMeetingIntent
- **Sample phrases:** "How long until my next meeting?", "When is my next meeting?", "How much time until my next meeting?"
- **Function:** Returns the countdown time until your next meeting starts
- **API Endpoint:** `/api/alexa/time-until-next`

### GetDoneForDayIntent
- **Sample phrases:** "Am I done for the day?", "When am I finished today?", "When does my last meeting end?", "What time am I done today?", "When can I go home?"
- **Function:** Returns when your last meeting of the day ends, helping you know when you're free
- **API Endpoint:** `/api/alexa/done-for-day`

---

## Prerequisites Checklist

Before starting, ensure you have:

**Local Setup:**
- [ ] Section 1 completed (CalendarBot service running on port 8080)
- [ ] CalendarBot responding to API requests: `curl http://localhost:8080/api/whats-next`

**Network:**
- [ ] Domain name registered (e.g., `ashwoodgrove.net`, `example.com`)
- [ ] DNS management access for your domain
- [ ] Public IP address (static or dynamic DNS)
- [ ] Router port forwarding configured: `80 → Pi:80`, `443 → Pi:443`
- [ ] OR: Pi directly exposed to internet with public IP

**Cloud Accounts:**
- [ ] Amazon Developer Account (https://developer.amazon.com)
- [ ] AWS Account (https://aws.amazon.com)
- [ ] Alexa device registered to your Amazon account (for testing)

---

## Architecture Overview

### Complete System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interaction                        │
│  "Alexa, ask Calendar Bot what's my next meeting?"             │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Alexa Voice Service                        │
│  Processes speech → Determines intent → Routes to skill         │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                   AWS Lambda Function                           │
│  Intent: GetNextMeetingIntent                                   │
│  Sends HTTP GET to CalendarBot endpoint                        │
│  Headers: Authorization: Bearer YOUR_TOKEN                      │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
                   Internet
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                 Your Domain (ashwoodgrove.net)                  │
│  DNS A Record → Public IP → Router Port Forward                 │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Raspberry Pi                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Caddy (:443)                                             │  │
│  │  - Terminates HTTPS                                      │  │
│  │  - Validates SSL certificate                             │  │
│  │  - Forwards to localhost:8080                           │  │
│  │  - CRITICAL: Forwards Authorization header              │  │
│  └─────────────────┬────────────────────────────────────────┘  │
│                    ↓                                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ CalendarBot Lite (:8080)                                 │  │
│  │  - Validates bearer token                                │  │
│  │  - Queries calendar data                                 │  │
│  │  - Returns JSON response                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Network Flow

```
Internet
  ↓
Your Domain (ashwoodgrove.net)
  ↓
DNS A Record → Your Public IP
  ↓
Router Port Forward (80, 443)
  ↓
Raspberry Pi
  ↓
Caddy (:80, :443)
  ↓
CalendarBot (:8080)
```

---

## Part 1: HTTPS Setup

Configure secure HTTPS access to your CalendarBot instance.

---

## Step 1: Obtain Public IP Address

Find your public IP address:

```bash
# From the Pi
curl ifconfig.me
```

**Example output**: `203.0.113.45`

**Save this IP address** - you'll need it for DNS configuration.

### Dynamic IP Considerations

If your ISP provides a dynamic IP (changes periodically):

**Option A: Use Dynamic DNS Service**
- Services: No-IP, DuckDNS, Dynu
- Updates DNS automatically when IP changes
- Many routers have built-in DDNS support

**Option B: Static IP from ISP**
- Request static IP from your ISP (may have monthly fee)
- Guarantees IP won't change

---

## Step 2: Configure DNS

Point your domain to your public IP.

### Create DNS A Record

In your domain registrar's DNS management:

```
Type: A
Name: @ (or blank, for root domain)
Value: YOUR_PUBLIC_IP
TTL: 300 (5 minutes for testing, increase to 3600 later)
```

**Example (for `ashwoodgrove.net`)**:
```
A    @    203.0.113.45    300
```

**OR, for a subdomain (e.g., `calendar.example.com`)**:
```
A    calendar    203.0.113.45    300
```

### Verify DNS Propagation

Wait 5-15 minutes, then test:

```bash
# From Pi or another machine
nslookup ashwoodgrove.net

# Or
dig ashwoodgrove.net +short
```

**Expected output**: Your public IP (`203.0.113.45`)

**Troubleshooting DNS:**
- DNS can take up to 48 hours to fully propagate globally
- Use short TTL (300) during testing
- Test from multiple locations/networks
- Clear DNS cache: `sudo systemd-resolve --flush-caches`

---

## Step 3: Configure Router Port Forwarding

If your Pi is behind a router, configure port forwarding:

### Required Port Forwards

| External Port | Internal IP | Internal Port | Protocol |
|---------------|-------------|---------------|----------|
| 80 | Pi IP (e.g., 192.168.1.100) | 80 | TCP |
| 443 | Pi IP (e.g., 192.168.1.100) | 443 | TCP |

### Router Configuration Steps

1. Access router admin page (usually `192.168.1.1` or `192.168.0.1`)
2. Find "Port Forwarding" or "Virtual Server" section
3. Add rules for ports 80 and 443
4. Save configuration

**Find Pi's local IP:**
```bash
hostname -I | awk '{print $1}'
```

### Verify Port Forwarding

```bash
# From OUTSIDE your network (different network, mobile data, etc.)
# Replace with your domain
curl -I http://ashwoodgrove.net
```

**If you get connection refused/timeout**:
- Check router port forwarding rules
- Verify Pi's local IP hasn't changed (use static DHCP lease)
- Check ISP doesn't block ports 80/443 (some residential ISPs do)

---

## Step 4: Install Caddy

Install Caddy web server with automatic HTTPS.

### Method A: Install from Official Repository (Recommended)

```bash
# Install dependencies
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https

# Add Caddy GPG key
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

# Add Caddy repository
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list

# Update and install
sudo apt update
sudo apt install caddy
```

**Verify installation:**
```bash
caddy version
# Should show: v2.7.x or later

# Check service status
sudo systemctl status caddy
```

### Method B: Install from GitHub Release

If official repository not available:

```bash
# Download latest ARM64 release (for Pi Zero 2 W)
wget https://github.com/caddyserver/caddy/releases/download/v2.7.6/caddy_2.7.6_linux_arm64.tar.gz

# Extract
tar -xzf caddy_2.7.6_linux_arm64.tar.gz

# Install
sudo mv caddy /usr/bin/
sudo chmod +x /usr/bin/caddy

# Test works
caddy version
```

---

## Step 5: Generate Bearer Token

Generate a secure random token for Alexa authentication:

```bash
# Generate 32-byte URL-safe token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example output**:
```
Xy9ZpqR8vL3mK2nF7wJ4hT6sC1dA5bE8gU0iO9yP2wQ
```

**SAVE THIS TOKEN SECURELY**. You'll need it for:
1. CalendarBot `.env` configuration
2. AWS Lambda environment variables
3. Testing

**Security notes:**
- Never commit tokens to git
- Use different tokens for dev/production
- Rotate tokens periodically (every 90 days recommended)

---

## Step 6: Configure CalendarBot for Alexa

Add the bearer token to CalendarBot configuration:

```bash
# Edit .env file
nano ~/calendarBot/.env
```

**Add or update:**
```bash
# Alexa Integration
CALENDARBOT_ALEXA_BEARER_TOKEN=Xy9ZpqR8vL3mK2nF7wJ4hT6sC1dA5bE8gU0iO9yP2wQ
```

**Restart CalendarBot to load new config:**
```bash
sudo systemctl restart calendarbot-lite@bencan.service

# Verify restart successful
sudo systemctl status calendarbot-lite@bencan.service
```

**Test bearer token authentication locally:**

```bash
# Without token (should fail with 401)
curl -v http://localhost:8080/api/alexa/next-meeting

# With correct token (should succeed)
curl -v -H "Authorization: Bearer Xy9ZpqR8vL3mK2nF7wJ4hT6sC1dA5bE8gU0iO9yP2wQ" \
  http://localhost:8080/api/alexa/next-meeting

# With wrong token (should fail with 401)
curl -v -H "Authorization: Bearer WRONG_TOKEN" \
  http://localhost:8080/api/alexa/next-meeting
```

**Expected response (with correct token):**
```json
{
  "meeting": {
    "subject": "Focus Time",
    "start_iso": "2025-11-03T15:00:00Z",
    "seconds_until_start": 207158,
    "speech_text": "Your next meeting is Focus Time in 57 hours and 32 minutes.",
    "duration_spoken": "in 57 hours and 32 minutes"
  }
}
```

**Response includes:**
- `speech_text`: Ready-to-use text for Alexa voice response
- `subject`: Meeting title
- `start_iso`: Meeting start time in ISO format
- `seconds_until_start`: Countdown in seconds
- `duration_spoken`: Human-readable time

---

## Step 7: Deploy Caddyfile

Configure Caddy reverse proxy with header forwarding.

### Backup Existing Caddyfile

```bash
# Backup default Caddyfile (if exists)
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup
```

### Deploy Enhanced Caddyfile

```bash
# Copy from repository
sudo cp ~/calendarBot/kiosk/config/enhanced_caddyfile /etc/caddy/Caddyfile

# Edit to use your domain
sudo nano /etc/caddy/Caddyfile
```

### Caddyfile Contents

Replace `ashwoodgrove.net` with your domain:

```caddy
# CalendarBot Kiosk - Alexa Integration
# IMPORTANT: Replace ashwoodgrove.net with YOUR domain

ashwoodgrove.net {
    # Logging
    log {
        output file /var/log/caddy/access.log
        level INFO
    }

    # Reverse proxy to CalendarBot
    reverse_proxy localhost:8080 {
        # Forward standard headers
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        # CRITICAL: Forward Authorization header explicitly
        # This is required for Alexa bearer token authentication
        header_up Authorization {header.Authorization}

        # Forward other common headers
        header_up User-Agent {header.User-Agent}
        header_up Accept {header.Accept}
        header_up Content-Type {header.Content-Type}
        header_up Content-Length {header.Content-Length}
    }

    # Debug endpoint to verify header forwarding
    handle /debug-headers {
        respond "Authorization: {header.Authorization}, User-Agent: {header.User-Agent}" 200
    }
}
```

**What this configuration does:**
- Automatic HTTPS with Let's Encrypt certificates
- Reverse proxy from `https://ashwoodgrove.net` → `http://localhost:8080`
- **Explicit Authorization header forwarding** (CRITICAL for Alexa)
- Debug endpoint for troubleshooting
- Access logging to `/var/log/caddy/access.log`

**Save file**: `Ctrl+X`, `Y`, `Enter`

### Create Log Directory

```bash
# Create Caddy log directory
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy
```

---

## Step 8: Configure Firewall

Allow HTTP and HTTPS traffic through firewall.

```bash
# Install UFW if not already installed
sudo apt-get install -y ufw

# IMPORTANT: Allow SSH first (to avoid locking yourself out)
sudo ufw allow 22/tcp

# Allow HTTP (port 80) - required for Let's Encrypt certificate validation
sudo ufw allow 80/tcp

# Allow HTTPS (port 443)
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

**Expected output:**
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

**Note**: Port 8080 should NOT be exposed externally. Only Caddy on localhost should access it.

---

## Step 9: Start Caddy

Start Caddy and obtain HTTPS certificate:

```bash
# Reload Caddy configuration
sudo systemctl reload caddy

# Check status
sudo systemctl status caddy

# View logs
sudo journalctl -u caddy -f
```

**Expected logs:**
```
INFO: serving initial configuration
INFO: attempting certificate: ashwoodgrove.net
INFO: authorization finalized
INFO: certificate obtained successfully
INFO: enabling automatic HTTPS
INFO: serving with automatic HTTPS
```

**If certificate fails:**
- Verify DNS is pointing to your public IP: `nslookup ashwoodgrove.net`
- Verify port 80 is accessible from internet: `curl -I http://ashwoodgrove.net` (from external network)
- Check Caddy logs: `sudo journalctl -u caddy -n 100`
- Wait a few minutes and try again (rate limiting)

### Enable Caddy Auto-Start

```bash
# Enable on boot
sudo systemctl enable caddy

# Verify enabled
sudo systemctl is-enabled caddy
# Should output: enabled
```

---

## Step 10: Test HTTPS Reverse Proxy

Test endpoints via HTTPS from external network.

### Test from Another Machine

From a different network (NOT your Pi's network):

```bash
# Test without authentication (should fail with 401)
curl -v https://ashwoodgrove.net/api/alexa/next-meeting
```

**Expected response:**
```json
{"error": "Unauthorized"}
```

**HTTP Status**: 401 Unauthorized

### Test with Bearer Token

```bash
# Test with correct bearer token (should succeed)
curl -v -H "Authorization: Bearer Xy9ZpqR8vL3mK2nF7wJ4hT6sC1dA5bE8gU0iO9yP2wQ" \
  https://ashwoodgrove.net/api/alexa/next-meeting
```

**Expected response:**
```json
{
  "meeting": {
    "subject": "Team Meeting",
    "start_iso": "2025-11-03T14:00:00-05:00",
    "speech_text": "Your next meeting is Team Meeting in 1 hour.",
    "seconds_until_start": 3600,
    "duration_spoken": "in 1 hour"
  }
}
```

**HTTP Status**: 200 OK

### Test All Alexa Endpoints

```bash
# Replace YOUR_TOKEN with your actual bearer token

# Next meeting
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ashwoodgrove.net/api/alexa/next-meeting

# Time until next
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ashwoodgrove.net/api/alexa/time-until-next

# Done for the day
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ashwoodgrove.net/api/alexa/done-for-day
```

---

## Step 11: Debug Header Forwarding

If authentication fails, use the debug endpoint to verify headers are being forwarded correctly.

### Test Debug Endpoint

```bash
# Test Authorization header forwarding
curl -v -H "Authorization: Bearer TEST123" \
  https://ashwoodgrove.net/debug-headers
```

**Expected response:**
```
Authorization: Bearer TEST123, User-Agent: curl/7.x
```

**If Authorization is empty or missing:**

1. **Verify Caddyfile has explicit header forwarding:**
   ```bash
   sudo grep -A5 "header_up Authorization" /etc/caddy/Caddyfile
   # Should show: header_up Authorization {header.Authorization}
   ```

2. **Reload Caddy after changes:**
   ```bash
   sudo systemctl reload caddy
   ```

3. **Check Caddy access logs:**
   ```bash
   sudo tail -f /var/log/caddy/access.log
   # Look for Authorization header in request logs
   ```

4. **Test locally first:**
   ```bash
   # Test CalendarBot directly (should work)
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/alexa/next-meeting

   # Test via Caddy (should also work)
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://ashwoodgrove.net/api/alexa/next-meeting
   ```

---

## Part 2: AWS Lambda & Alexa Skill

Deploy the Alexa skill backend and configure the Alexa skill.

---

## Step 12: Deploy AWS Lambda Function

Create and configure the AWS Lambda function that powers your Alexa skill.

### 12.1: Create Lambda Function

1. Open [AWS Lambda Console](https://console.aws.amazon.com/lambda)
2. Click **"Create function"**
3. Choose **"Author from scratch"**
4. Function name: `calendarbot-alexa-skill`
5. Runtime: **Python 3.11** (or latest Python 3.x)
6. Architecture: **x86_64**
7. Click **"Create function"**

### 12.2: Upload Lambda Code

The Lambda function code is located in your CalendarBot repository:

```bash
# View the Lambda function code
cat ~/calendarBot/alexa_skill_backend.py
```

**Upload to Lambda:**

1. In Lambda console, scroll to **"Code source"** section
2. Copy contents of `alexa_skill_backend.py`
3. Paste into `lambda_function.py` editor
4. Click **"Deploy"**

**Lambda function handles:**
- `GetNextMeetingIntent` → Calls `/api/alexa/next-meeting`
- `GetTimeUntilNextMeetingIntent` → Calls `/api/alexa/time-until-next`
- `GetDoneForDayIntent` → Calls `/api/alexa/done-for-day`
- `AMAZON.HelpIntent`, `AMAZON.StopIntent`, `AMAZON.CancelIntent`

### 12.3: Configure Environment Variables

In Lambda function configuration:

1. Click **"Configuration"** tab
2. Click **"Environment variables"**
3. Click **"Edit"**
4. Add the following variables:

| Key | Value | Description |
|-----|-------|-------------|
| `CALENDARBOT_ENDPOINT` | `https://ashwoodgrove.net` | Your domain (no trailing slash) |
| `CALENDARBOT_BEARER_TOKEN` | `Xy9ZpqR8vL3mK2nF7wJ4hT6sC1dA5bE8gU0iO9yP2wQ` | Your bearer token |
| `REQUEST_TIMEOUT` | `10` | HTTP request timeout in seconds |

5. Click **"Save"**

### 12.4: Configure Lambda Timeout

1. In **"Configuration"** tab, click **"General configuration"**
2. Click **"Edit"**
3. Set **Timeout** to `10 seconds`
4. Click **"Save"**

### 12.5: Test Lambda Function

Create test events to verify Lambda works:

1. Click **"Test"** tab
2. Click **"Create new event"**
3. Event name: `TestNextMeeting`
4. Use this JSON:

```json
{
  "request": {
    "type": "IntentRequest",
    "intent": {
      "name": "GetNextMeetingIntent"
    }
  }
}
```

5. Click **"Save"**
6. Click **"Test"**

**Expected response:**
```json
{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "Your next meeting is Team Meeting in 1 hour."
    }
  }
}
```

**Create additional test events:**

**TestTimeUntil:**
```json
{
  "request": {
    "type": "IntentRequest",
    "intent": {
      "name": "GetTimeUntilNextMeetingIntent"
    }
  }
}
```

**TestDoneForDay:**
```json
{
  "request": {
    "type": "IntentRequest",
    "intent": {
      "name": "GetDoneForDayIntent"
    }
  }
}
```

### 12.6: Copy Lambda ARN

1. In Lambda function overview, copy the **Function ARN**
2. Example: `arn:aws:lambda:us-east-1:123456789012:function:calendarbot-alexa-skill`
3. **Save this ARN** - you'll need it for Alexa skill configuration

**Troubleshooting Lambda:**
- **Test fails**: Check CloudWatch logs in Lambda console
- **Timeout errors**: Increase timeout to 15 seconds
- **401 errors**: Verify bearer token matches CalendarBot `.env`
- **Network errors**: Check endpoint URL (no trailing slash)

---

## Step 13: Create Alexa Skill

Create and configure the Alexa skill in the Amazon Developer Console.

### 13.1: Create Skill

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click **"Create Skill"**
3. **Skill name**: `Calendar Bot`
4. **Primary locale**: English (US)
5. **Choose a model**: Select **"Custom"**
6. **Choose a method**: Select **"Provision your own"**
7. **Hosting services**: Select **"Provision your own"**
8. Click **"Create skill"**
9. **Choose a template**: Select **"Start from Scratch"**
10. Click **"Continue with template"**

### 13.2: Configure Interaction Model

1. In left sidebar, click **"Interaction Model"** → **"JSON Editor"**
2. Replace the entire content with:

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
            "what is my next meeting",
            "tell me my next meeting",
            "what meeting do I have next",
            "what's coming up next",
            "what's next on my calendar",
            "what do I have next",
            "what's on my calendar"
          ]
        },
        {
          "name": "GetTimeUntilNextMeetingIntent",
          "slots": [],
          "samples": [
            "how long until my next meeting",
            "when is my next meeting",
            "how much time until my next meeting",
            "when do I need to be in my next meeting",
            "how much time do I have",
            "when does my next meeting start"
          ]
        },
        {
          "name": "GetDoneForDayIntent",
          "slots": [],
          "samples": [
            "am I done for the day",
            "when am I done for the day",
            "when am I finished today",
            "when does my last meeting end",
            "what time am I done today",
            "when can I go home",
            "when is my day over",
            "when do I finish today",
            "what time do I finish work",
            "when am I free for the day",
            "what time am I free"
          ]
        },
        {
          "name": "AMAZON.HelpIntent",
          "samples": []
        },
        {
          "name": "AMAZON.StopIntent",
          "samples": []
        },
        {
          "name": "AMAZON.CancelIntent",
          "samples": []
        },
        {
          "name": "AMAZON.NavigateHomeIntent",
          "samples": []
        }
      ]
    }
  }
}
```

3. Click **"Save Model"**
4. Click **"Build Model"** (wait for build to complete, ~1 minute)

**What this does:**
- **Invocation name**: "calendar bot" - how users activate the skill
- **Intents**: Three custom intents plus Amazon built-ins
- **Sample utterances**: Multiple ways to phrase each command

### 13.3: Configure Endpoint

1. In left sidebar, click **"Endpoint"**
2. Select **"AWS Lambda ARN"**
3. **Default Region**: Paste your Lambda ARN
   - Example: `arn:aws:lambda:us-east-1:123456789012:function:calendarbot-alexa-skill`
4. Leave other regions empty
5. Click **"Save Endpoints"**

### 13.4: Enable Skill for Testing

1. Click **"Test"** tab at top
2. Change dropdown from **"Off"** to **"Development"**
3. Wait for test to enable

---

## Step 14: Test End-to-End

Test the complete integration with Alexa.

### 14.1: Test with Alexa Simulator

In the Alexa Developer Console **Test** tab:

**Test invocation and launch:**
```
Type: "open calendar bot"
Expected: "Welcome to Calendar Bot. You can ask about your next meeting..."
```

**Test GetNextMeetingIntent:**
```
Type: "ask calendar bot what's my next meeting"
Expected: "Your next meeting is [Meeting Name] in [Time]."
```

**Test GetTimeUntilNextMeetingIntent:**
```
Type: "ask calendar bot how long until my next meeting"
Expected: "[Time] until your meeting [Meeting Name]."
```

**Test GetDoneForDayIntent:**
```
Type: "ask calendar bot when am I done for the day"
Expected: "You are done for the day at [Time], after your meeting [Meeting Name]."
```

**Test Help intent:**
```
Type: "ask calendar bot for help"
Expected: "You can ask about your next meeting, how long until your next meeting..."
```

### 14.2: Test on Physical Alexa Device

Ensure your Alexa device is registered to the same Amazon account as your developer account.

**Test various phrases:**
- "Alexa, open Calendar Bot"
- "Alexa, ask Calendar Bot what's my next meeting"
- "Alexa, ask Calendar Bot how long until my next meeting"
- "Alexa, ask Calendar Bot when am I done for the day"
- "Alexa, ask Calendar Bot when can I go home"

**Expected behavior:**
- Alexa should respond with current calendar information
- Responses should match your actual calendar
- Voice responses should be clear and natural

### 14.3: Verify Calendar Data

```bash
# From Pi, check what data CalendarBot is returning
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://ashwoodgrove.net/api/alexa/next-meeting | jq
```

**Compare Alexa response with API response:**
- Meeting names should match
- Times should be accurate
- "No meetings" should only occur when truly no meetings

---

## Verification Checklist

Before proceeding to Section 4, verify all items:

**HTTPS Setup:**
- [ ] Public IP address identified
- [ ] DNS A record pointing to public IP
- [ ] DNS propagation verified: `nslookup YOUR_DOMAIN` returns correct IP
- [ ] Router port forwarding configured (80, 443)
- [ ] Ports accessible from internet (test from external network)
- [ ] Caddy installed and running
- [ ] HTTPS certificate obtained successfully
- [ ] Bearer token generated and saved securely
- [ ] Bearer token added to CalendarBot `.env`
- [ ] CalendarBot service restarted
- [ ] Local bearer token test succeeds
- [ ] Remote HTTPS test with token succeeds (200 OK)
- [ ] Remote HTTPS test without token fails (401 Unauthorized)

**AWS Lambda:**
- [ ] Lambda function created
- [ ] Lambda code deployed from `alexa_skill_backend.py`
- [ ] Environment variables configured (endpoint, token, timeout)
- [ ] Lambda timeout set to 10 seconds
- [ ] Test events created for all intents
- [ ] All Lambda tests pass
- [ ] Lambda ARN copied

**Alexa Skill:**
- [ ] Skill created in Developer Console
- [ ] Interaction model JSON deployed
- [ ] Model built successfully
- [ ] Endpoint configured with Lambda ARN
- [ ] Skill enabled for testing (Development mode)
- [ ] Alexa simulator tests pass for all intents
- [ ] Physical device tests pass

**End-to-End:**
- [ ] All 3 intents respond correctly
- [ ] Responses match actual calendar data
- [ ] No authentication errors
- [ ] No timeout errors

---

## Files Deployed

Summary of files created or modified in this section:

| File Path | Purpose | User Editable |
|-----------|---------|---------------|
| `/etc/caddy/Caddyfile` | Caddy reverse proxy configuration | **Yes** |
| `/var/log/caddy/access.log` | Caddy access logs | Auto-generated |
| `~/calendarBot/.env` | Updated with bearer token | **Yes** |

**AWS Resources:**
- Lambda Function: `calendarbot-alexa-skill`
- Alexa Skill: `Calendar Bot`

---

## Troubleshooting

### HTTPS Issues

#### Cannot obtain HTTPS certificate

**Error in Caddy logs:**
```
ERROR: obtaining certificate: acme: error: 403 ... Forbidden
```

**Solutions:**

1. **Verify DNS is correct:**
   ```bash
   nslookup ashwoodgrove.net
   # Must return your public IP
   ```

2. **Verify port 80 accessible from internet:**
   ```bash
   # From external network
   curl -I http://ashwoodgrove.net
   # Should connect (may return 404, but should connect)
   ```

3. **Check for rate limiting:**
   - Let's Encrypt has rate limits (5 certs per week per domain)
   - Wait 1 hour and try again
   - Or use staging endpoint for testing

4. **Use staging endpoint for testing:**
   ```bash
   # Edit Caddyfile
   sudo nano /etc/caddy/Caddyfile

   # Add inside domain block:
   tls {
       ca https://acme-staging-v02.api.letsencrypt.org/directory
   }

   # Reload
   sudo systemctl reload caddy
   ```

#### Alexa endpoint returns 401 even with correct token

**Check Authorization header forwarding:**

```bash
# Test debug endpoint
curl -H "Authorization: Bearer TEST" https://ashwoodgrove.net/debug-headers
# Should show: Authorization: Bearer TEST
```

**If header missing:**

1. **Verify Caddyfile:**
   ```bash
   sudo cat /etc/caddy/Caddyfile | grep -A2 "header_up Authorization"
   # Should show explicit forwarding
   ```

2. **Reload Caddy:**
   ```bash
   sudo systemctl reload caddy
   ```

3. **Check CalendarBot logs:**
   ```bash
   sudo journalctl -u calendarbot-lite@bencan.service | grep -i authorization
   ```

### Lambda Issues

#### Lambda test fails with timeout

**Solution:**
```bash
# Increase timeout
# In Lambda console: Configuration → General → Timeout → 15 seconds
```

#### Lambda test fails with 401 Unauthorized

**Check:**
1. Bearer token in Lambda matches CalendarBot `.env`
2. CalendarBot service is running: `sudo systemctl status calendarbot-lite@bencan.service`
3. Test endpoint directly:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://ashwoodgrove.net/api/alexa/next-meeting
   ```

#### Lambda logs show "Connection refused"

**Check:**
1. Domain is accessible from internet
2. Caddy is running: `sudo systemctl status caddy`
3. CalendarBot is running on port 8080
4. No typos in `CALENDARBOT_ENDPOINT` (no trailing slash)

### Alexa Skill Issues

#### Skill says "There was a problem with the requested skill's response"

**Check:**
1. Lambda function CloudWatch logs: [AWS CloudWatch Console](https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fcalendarbot-alexa-skill)
2. Lambda test works correctly
3. Endpoint ARN is correct in Alexa skill
4. Interaction model is built

#### Skill not responding to voice commands

**Check:**
1. Skill is enabled for testing (Development mode)
2. Alexa device is registered to same Amazon account
3. Invocation name is correct: "calendar bot"
4. Try exact sample phrases from interaction model

#### Wrong calendar data returned

**Check:**
1. CalendarBot is loading correct ICS URL
2. Test endpoint directly to see data:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://ashwoodgrove.net/api/alexa/next-meeting | jq
   ```
3. Calendar refresh interval: check `.env` for `CALENDARBOT_REFRESH_INTERVAL`

---

## Security Hardening

### Bearer Token Security

**Protect your token:**
- Never commit `.env` to public repositories
- Use different tokens for dev/staging/production
- Rotate tokens every 90 days

**Token rotation procedure:**
```bash
# 1. Generate new token
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "New token: $NEW_TOKEN"

# 2. Update CalendarBot .env
nano ~/calendarBot/.env
# Update CALENDARBOT_ALEXA_BEARER_TOKEN

# 3. Restart CalendarBot
sudo systemctl restart calendarbot-lite@bencan.service

# 4. Update Lambda environment variable
# Go to Lambda console → Configuration → Environment variables
# Update CALENDARBOT_BEARER_TOKEN

# 5. Test Lambda function with test event

# 6. Test Alexa skill
```

### Firewall Best Practices

**Only expose required ports:**
```bash
# Check current rules
sudo ufw status verbose

# Deny all other ports by default
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### Caddy Security

**Keep Caddy updated:**
```bash
# Update Caddy regularly
sudo apt update
sudo apt upgrade caddy
```

**Monitor access logs:**
```bash
# Watch for suspicious activity
sudo tail -f /var/log/caddy/access.log

# Check for failed auth attempts (401 responses)
grep "401" /var/log/caddy/access.log | tail -20
```

**Example suspicious pattern:**
```
# Many 401s from same IP in short time = potential attack
203.0.113.45 - - [03/Nov/2025:10:15:23] "GET /api/alexa/next-meeting" 401
203.0.113.45 - - [03/Nov/2025:10:15:24] "GET /api/alexa/next-meeting" 401
203.0.113.45 - - [03/Nov/2025:10:15:25] "GET /api/alexa/next-meeting" 401
```

### AWS Lambda Security

**Restrict Lambda permissions:**
- Lambda should only have necessary permissions
- Use IAM roles with minimal required access
- Enable AWS CloudTrail for audit logging

**Monitor Lambda invocations:**
```bash
# View Lambda metrics in AWS Console
# CloudWatch → Metrics → Lambda → Invocations, Errors, Duration
```

---

## Maintenance

### Regular Tasks

**Weekly:**
```bash
# Test all Alexa intents
"Alexa, ask Calendar Bot what's my next meeting"
"Alexa, ask Calendar Bot how long until my next meeting"
"Alexa, ask Calendar Bot when am I done for the day"

# Check Caddy logs for errors
sudo journalctl -u caddy --since "7 days ago" | grep -i error

# Check CalendarBot logs for errors
sudo journalctl -u calendarbot-lite@bencan.service --since "7 days ago" | grep -i error
```

**Monthly:**
```bash
# Update Caddy
sudo apt update && sudo apt upgrade caddy

# Review Caddy access logs for suspicious activity
grep "401" /var/log/caddy/access.log | tail -50

# Check certificate expiry (Caddy auto-renews, but verify)
echo | openssl s_client -connect ashwoodgrove.net:443 2>/dev/null | \
  openssl x509 -noout -dates
```

**Quarterly:**
```bash
# Rotate bearer token (see Security Hardening section)
# Update Lambda function code if needed
# Review and update Alexa interaction model sample phrases
```

### Backup Configuration

**Backup important files:**
```bash
# Create backup directory
mkdir -p ~/calendarbot-backups

# Backup CalendarBot config
cp ~/calendarBot/.env ~/calendarbot-backups/.env.backup

# Backup Caddyfile
sudo cp /etc/caddy/Caddyfile ~/calendarbot-backups/Caddyfile.backup

# Export Lambda configuration
aws lambda get-function-configuration \
  --function-name calendarbot-alexa-skill \
  --query 'Environment.Variables' > ~/calendarbot-backups/lambda-env.json

# Compress backups
cd ~/calendarbot-backups
tar -czf calendarbot-backup-$(date +%Y%m%d).tar.gz *.backup *.json
```

### Monitoring

**Check system health:**
```bash
# CalendarBot status
sudo systemctl status calendarbot-lite@bencan.service

# Caddy status
sudo systemctl status caddy

# Recent errors from all services
sudo journalctl --since "1 hour ago" | grep -E "(ERROR|CRITICAL)"

# Disk space
df -h | grep -E "Filesystem|/var"

# Memory usage
free -h
```

---

## Cost Considerations

- **AWS Lambda**: Free tier includes 1M requests/month
- **Alexa Skill**: Free
- **Domain/DNS**: $10-15/year for domain registration
- **Dynamic DNS**: Free options available (DuckDNS, No-IP)
- **Let's Encrypt**: Free SSL certificates
- **Compute**: Runs on existing Pi hardware

**Estimated monthly cost**: $0-2 (assuming free tier, domain already owned)

---

## Performance Notes

**Resource usage on Pi Zero 2:**
- Caddy: 15-30MB RAM, <5% CPU
- TLS overhead: Minimal (<1% CPU for typical traffic)
- Lambda: Runs in AWS, no local impact

**Optimization tips:**
- Caddy is very efficient, no tuning needed
- Consider Cloudflare if you need DDoS protection
- Lambda cold starts: 1-2 seconds (acceptable for voice)

---

## Next Steps

**Section 3 Complete!** ✅

You now have:
- **HTTPS access** to CalendarBot via your domain with automatic certificates
- **Bearer token authentication** protecting API endpoints
- **AWS Lambda function** processing Alexa requests
- **Alexa skill** responding to voice commands
- **Complete integration** from voice to calendar

**Configure Monitoring (Optional):**
- **[Section 4: Monitoring & Log Management →](4_LOG_MANAGEMENT.md)** - Add comprehensive monitoring

**Or return to**: [Installation Overview](INSTALLATION_OVERVIEW.md)

**Using your Alexa skill:**
```
"Alexa, ask Calendar Bot what's my next meeting"
"Alexa, ask Calendar Bot how long until my next meeting"
"Alexa, ask Calendar Bot when am I done for the day"
```

---

**Alexa Integration Complete!** 🎉
