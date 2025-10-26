# Alexa Integration Deployment Guide

This guide walks through setting up the complete Alexa integration for CalendarBot Lite.

## Supported Alexa Commands

CalendarBot Lite supports the following voice commands through Alexa:

### GetNextMeetingIntent
- **Sample phrases:** "What's my next meeting?", "Tell me my next meeting", "What meeting do I have next?"
- **Function:** Returns details about your upcoming meeting including subject, start time, and duration

### GetTimeUntilNextMeetingIntent
- **Sample phrases:** "How long until my next meeting?", "When is my next meeting?", "How much time until my next meeting?"
- **Function:** Returns the countdown time until your next meeting starts

### GetDoneForDayIntent
- **Sample phrases:** "Am I done for the day?", "When am I finished today?", "When does my last meeting end?", "What time am I done today?", "When can I go home?"
- **Function:** Returns when your last meeting of the day ends, helping you know when you're free

## Prerequisites

- CalendarBot Lite running and configured with calendar sources
- Amazon Developer Account (free)
- AWS Account for Lambda deployment (free tier available)
- Domain name or dynamic DNS (for HTTPS endpoint)
- Basic familiarity with command line tools

## Step 1: Configure CalendarBot Lite

### 1.1 Generate Bearer Token

```bash
# Generate a secure random token
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567
```

### 1.2 Update Configuration

Add to your root `.env` file (CalendarBot Lite uses environment variables, not YAML config):

```bash
# .env (in project root directory)

# Calendar Configuration
CALENDARBOT_ICS_URL=https://your-calendar-url.com/calendar.ics
CALENDARBOT_REFRESH_INTERVAL=300

# Server Configuration
CALENDARBOT_SERVER_BIND=0.0.0.0
CALENDARBOT_SERVER_PORT=8080

# Alexa Integration Bearer Token
CALENDARBOT_ALEXA_BEARER_TOKEN=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567
```

**Security Note**: Keep this token secret. Never commit the `.env` file to version control (it should be in `.gitignore`).

### 1.3 Test Local Server

```bash
# Activate virtual environment
. venv/bin/activate

# Start server (should show startup logs)
python -m calendarbot_lite

# Wait for server to start (you should see "Running on http://..." message)
```

In another terminal, test the endpoints:

```bash
# First, check if server is responding
curl http://localhost:8080/api/whats-next

# Then test Alexa endpoints (replace YOUR_TOKEN with your actual token from .env)
curl -H "Authorization: Bearer your-bearer-token" http://localhost:8080/api/alexa/next-meeting

curl -H "Authorization: Bearer your-bearer-token" http://localhost:8080/api/alexa/time-until-next

curl -H "Authorization: Bearer your-bearer-token" http://localhost:8080/api/alexa/done-for-day
```

**Expected Response:**
```json
{
  "meeting": {
    "subject": "Focus Time",
    "start_iso": "2025-10-27T15:00:00Z",
    "seconds_until_start": 207158,
    "speech_text": "Your next meeting is Focus Time in 57 hours and 32 minutes.",
    "duration_spoken": "in 57 hours and 32 minutes"
  }
}
```

The response includes:
- **`meeting.speech_text`**: Ready-to-use text for Alexa voice response
- **`meeting.subject`**: Meeting title/subject
- **`meeting.start_iso`**: Meeting start time in ISO format
- **`meeting.seconds_until_start`**: Countdown in seconds
- **`meeting.duration_spoken`**: Human-readable time until meeting

**Troubleshooting:**
- If server won't start: Check that venv is activated and dependencies are installed
- If you get 404: Server started but endpoints not found - check server logs
- If you get 401: Bearer token mismatch - verify CALENDARBOT_ALEXA_BEARER_TOKEN in .env
- If you get empty response: No calendar events loaded - check CALENDARBOT_ICS_URL in .env

## Step 2: Set Up HTTPS Endpoint

### Option A: Caddy with Automatic HTTPS (Recommended)

#### 2.1 Install Caddy

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo apt-key add -
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# On macOS
brew install caddy
```

#### 2.2 Configure Caddy

Create `/etc/caddy/Caddyfile` (remove any existing content):

```caddy
ashwoodgrove.net {
    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Authorization {header.Authorization}
    }
    log {
        output file /var/log/caddy/access.log
    }
}
```

**Important**: Remove any default lines like:
```caddy
# Remove these if present:
# root * /usr/share/caddy
# file_server
```

**Key Change**: The `header_up Authorization {header.Authorization}` line ensures the Authorization header is properly forwarded to CalendarBot Lite.

#### 2.3 Start Caddy

```bash
sudo systemctl enable --now caddy
sudo systemctl status caddy
```

#### 2.4 Test HTTPS Reverse Proxy

Before setting up Lambda, verify that Caddy is properly forwarding external HTTPS requests:

**Step 1: Ensure both services are running**
```bash
# In terminal 1: Start CalendarBot Lite
. venv/bin/activate
python -m calendarbot_lite

# In terminal 2: Check Caddy status
sudo systemctl status caddy
```

**Step 2: Test external HTTPS access**

First, verify the basic endpoint works locally:
```bash
# Test locally first (should work without auth)
curl http://localhost:8080/api/whats-next

# If you get 401 locally, there might be an auth issue with the base endpoint
```

Then test through HTTPS:
```bash
# Test through Caddy (replace with your domain)
curl -k https://ashwoodgrove.net/api/whats-next

# If you get 401: The /api/whats-next endpoint might require authentication
```

**Step 3: Test Alexa endpoints with HTTPS**
```bash
# Test the Alexa endpoints through Caddy (replace with your actual domain and token)
curl -k -H "Authorization: Bearer Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA" https://your-domain.com/api/alexa/next-meeting

curl -k -H "Authorization: Bearer Uc39FIpUYa2BDIMjOUDyhzQk53qhQjHFxTpw-9P7wkA" https://your-domain.com/api/alexa/done-for-day

# Should return:
# {"meeting": {"subject": "...", "speech_text": "...", ...}}
# or {"speech_text": "You are done for the day at...", ...}
```

**Troubleshooting:**
- **Connection refused**: Check if Caddy is running and listening on port 443
- **404 from Caddy**: Reverse proxy not configured correctly
- **502 Bad Gateway**: CalendarBot Lite is not running on localhost:8080
- **Certificate errors**: Normal for testing with `-k` flag; Caddy will get proper certs automatically

**Expected Success**: You should see the same JSON responses as the local tests, but accessed via HTTPS through your domain.

### Option B: ngrok (Development/Testing)

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Create tunnel
ngrok http 8080

# Note the HTTPS URL (e.g., https://abc123.ngrok.io)
```

## Step 3: Deploy Alexa Skill Backend

### 3.1 Create Lambda Function

1. Open AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. Function name: `calendarbot-alexa-skill`
5. Runtime: `Python 3.11`
6. Click "Create function"

### 3.2 Upload Code

Copy the contents of `alexa_skill_backend.py` into the Lambda function editor.

### 3.3 Configure Environment Variables

In Lambda function configuration, add environment variables:

```
CALENDARBOT_ENDPOINT = https://your-domain.com
CALENDARBOT_BEARER_TOKEN = abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567
REQUEST_TIMEOUT = 10
```

### 3.4 Test Lambda Function

Use the Lambda test feature with these test events:

**Test GetNextMeetingIntent:**
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

**Test GetTimeUntilNextMeetingIntent:**
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

**Test GetDoneForDayIntent:**
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

Expected response should include `speech_text` field.

## Step 4: Create Alexa Skill

### 4.1 Create Skill in Developer Console

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click "Create Skill"
3. Skill name: "Calendar Bot"
4. Primary locale: English (US)
5. Choose "Custom" model
6. Choose "Alexa-Hosted (Python)" or "Provision your own"
7. Click "Create skill"

### 4.2 Configure Interaction Model

1. In the left sidebar, click "Interaction Model" > "JSON Editor"
2. Replace content with:

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
            "what's next on my calendar"
          ]
        },
        {
          "name": "GetTimeUntilNextMeetingIntent",
          "slots": [],
          "samples": [
            "how long until my next meeting",
            "when is my next meeting",
            "how much time until my next meeting",
            "when do I need to be in my next meeting"
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
            "when am I free for the day"
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
        }
      ]
    }
  }
}
```

3. Click "Save Model"
4. Click "Build Model"

### 4.3 Configure Endpoint

1. Click "Endpoint" in left sidebar
2. Select "AWS Lambda ARN"
3. Enter your Lambda function ARN (copy from Lambda console)
4. Click "Save Endpoints"

## Step 5: Test Integration

### 5.1 Test with Alexa Simulator

1. In Alexa Developer Console, click "Test"
2. Enable testing for "Development"
3. Test the different intents:
   - "ask calendar bot what's my next meeting"
   - "ask calendar bot how long until my next meeting"
   - "ask calendar bot am I done for the day"
4. Verify responses match your calendar

### 5.2 Test on Device

1. Ensure your Alexa device is registered to the same Amazon account
2. Test with various phrases:
   - "Alexa, ask Calendar Bot what's my next meeting"
   - "Alexa, ask Calendar Bot when am I done for the day"
   - "Alexa, ask Calendar Bot how long until my next meeting"
3. Verify the responses

## Step 6: Adding "Done for the Day" Functionality

### 6.1 New Intent Configuration

The `GetDoneForDayIntent` has been added to support "done for the day" queries. If you're updating an existing Alexa skill, you'll need to add this intent to your interaction model.

**Required Changes to Interaction Model:**

1. In Alexa Developer Console, go to "Interaction Model" > "JSON Editor"
2. Add the `GetDoneForDayIntent` to your existing intents array (as shown in Section 4.2)
3. Save and build the model

**API Endpoint:**
- **Path:** `/api/alexa/done-for-day`
- **Method:** GET
- **Headers:** `Authorization: Bearer <your-token>`

**Sample Response:**
```json
{
  "speech_text": "You are done for the day at 5:00 PM, after your meeting with the Marketing Team.",
  "ssml": "<speak>You are done for the day at <say-as interpret-as='time'>17:00</say-as>, after your meeting with the Marketing Team.</speak>",
  "end_time_iso": "2025-10-26T17:00:00Z",
  "last_meeting": {
    "subject": "Marketing Team Meeting",
    "end_time_iso": "2025-10-26T17:00:00Z"
  }
}
```

### 6.2 Testing the New Functionality

**Test with cURL:**
```bash
# Test the done-for-day endpoint directly
curl -H "Authorization: Bearer your-bearer-token" \
     https://your-domain.com/api/alexa/done-for-day
```

**Test with Alexa Simulator:**
- "ask calendar bot am I done for the day"
- "ask calendar bot when am I finished today"
- "ask calendar bot what time am I done today"

**Expected Behavior:**
- If you have meetings today: Returns the end time of your last meeting
- If you have no meetings today: Returns a message indicating you have no meetings
- If all meetings are finished: Returns a message about being done for the day

## Step 7: Security Hardening

### 6.1 Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for Let's Encrypt)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 6.2 Update Bearer Token Regularly

```bash
# Generate new token
NEW_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Update CalendarBot config
sed -i "s/alexa_bearer_token: .*/alexa_bearer_token: \"$NEW_TOKEN\"/" calendarbot_lite/config.yaml

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name calendarbot-alexa-skill \
  --environment Variables="{CALENDARBOT_ENDPOINT=https://your-domain.com,CALENDARBOT_BEARER_TOKEN=$NEW_TOKEN,REQUEST_TIMEOUT=10}"

# Restart CalendarBot
sudo systemctl restart calendarbot-lite
```

### 6.3 Monitor Logs

```bash
# CalendarBot logs
journalctl -u calendarbot-lite -f

# Caddy logs
tail -f /var/log/caddy/access.log

# AWS Lambda logs (check CloudWatch)
```

## Troubleshooting

### CalendarBot Issues

**Server won't start**:
```bash
# Check port availability
sudo netstat -tlnp | grep :8080

# Check configuration
python -c "from calendarbot_lite.config_loader import load_config; print(load_config())"
```

**Bearer token errors**:
```bash
# Test authentication manually for all endpoints
curl -v -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/alexa/next-meeting

curl -v -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/alexa/time-until-next

curl -v -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/alexa/done-for-day
```

### HTTPS Issues

**Certificate problems with Caddy**:
```bash
# Check Caddy status
sudo systemctl status caddy

# View Caddy logs
sudo journalctl -u caddy -f

# Test DNS resolution
dig your-domain.com
```

**ngrok tunnel issues**:
```bash
# Check ngrok status
curl http://localhost:4040/api/tunnels

# Restart tunnel
pkill ngrok
ngrok http 8080
```

### Alexa Skill Issues

**Skill not responding**:
1. Check Lambda CloudWatch logs
2. Test Lambda function directly
3. Verify skill is enabled in Alexa app
4. Check interaction model is built

**"Done for the day" intent issues**:
1. Verify `GetDoneForDayIntent` is included in interaction model JSON
2. Test with specific phrases: "ask calendar bot am I done for the day"
3. Check that `/api/alexa/done-for-day` endpoint returns valid response
4. If response says "no meetings today" when you have meetings, check calendar sync

**Authentication errors in Lambda**:
1. Verify environment variables in Lambda
2. Test CalendarBot endpoint with curl
3. Check network connectivity from Lambda

### Lambda Debug Commands

```bash
# View Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/calendarbot"

# Stream logs in real-time
aws logs tail /aws/lambda/calendarbot-alexa-skill --follow
```

## Maintenance

### Regular Updates

1. **Update CalendarBot**: Pull latest changes and restart service
2. **Rotate Bearer Token**: Generate new token monthly
3. **Monitor Logs**: Check for errors or unusual activity
4. **Test Functionality**: Weekly voice test with Alexa for all intents:
   - "Alexa, ask Calendar Bot what's my next meeting"
   - "Alexa, ask Calendar Bot how long until my next meeting"
   - "Alexa, ask Calendar Bot am I done for the day"

### Backup Configuration

```bash
# Backup CalendarBot config
cp calendarbot_lite/config.yaml config.yaml.backup

# Export Lambda environment variables
aws lambda get-function-configuration \
  --function-name calendarbot-alexa-skill \
  --query 'Environment.Variables' > lambda-env-backup.json
```

## Cost Considerations

- **AWS Lambda**: Free tier includes 1M requests/month
- **Domain/DNS**: $10-15/year for domain registration
- **Dynamic DNS**: Free options available (DuckDNS, No-IP)
- **Let's Encrypt**: Free SSL certificates
- **Compute**: Runs on existing hardware

## Privacy Notes

- Calendar data never leaves your local network (except metadata for next meeting)
- Bearer token provides API security
- No user data stored in AWS Lambda
- Request logs can be disabled in both CalendarBot and Lambda
- Alexa processes voice locally when possible

## Next Steps

- Consider setting up monitoring/alerting
- Implement rate limiting for API endpoints
- Add support for additional calendar information
- Create backup CalendarBot instance for redundancy