# Morning Summary API Documentation

This document provides comprehensive examples for using both the general-purpose and Alexa-specific morning summary API endpoints.

## Endpoints Overview

| Endpoint | Method | Authentication | Purpose |
|----------|---------|---------------|---------|
| `/api/morning-summary` | POST | None | General-purpose API returning structured data |
| `/api/alexa/morning-summary` | POST | Bearer Token | Alexa-specific API with speech text and SSML |

---

## General API Endpoint: `/api/morning-summary`

### Basic Usage

```bash
# Simple request with defaults
curl -X POST "http://localhost:8080/api/morning-summary"
```

### With Query Parameters

```bash
# Full parameter example
curl -X POST "http://localhost:8080/api/morning-summary?date=2025-10-29&timezone=America/Los_Angeles&detail_level=detailed&max_events=30"
```

### Individual Parameter Examples

```bash
# Specific date (ISO format)
curl -X POST "http://localhost:8080/api/morning-summary?date=2025-10-29"

# Different timezone
curl -X POST "http://localhost:8080/api/morning-summary?timezone=Europe/London"

# Detail levels: brief, normal, detailed
curl -X POST "http://localhost:8080/api/morning-summary?detail_level=brief"

# Limit number of events processed
curl -X POST "http://localhost:8080/api/morning-summary?max_events=20"
```

### Expected Response Format

```json
{
  "summary": {
    "timeframe_start": "2025-10-29T06:00:00-07:00",
    "timeframe_end": "2025-10-29T12:00:00-07:00",
    "analysis_time": "2025-10-28T23:45:00-07:00",
    "total_meetings_equivalent": 2.5,
    "early_start_flag": true,
    "density": "moderate",
    "back_to_back_count": 1,
    "meeting_insights": [
      {
        "meeting_id": "meeting-123",
        "subject": "Team Standup",
        "start_time": "2025-10-29T09:00:00-07:00",
        "end_time": "2025-10-29T09:30:00-07:00",
        "time_until_minutes": 420,
        "preparation_needed": false,
        "is_online": true,
        "attendees_count": 5,
        "short_note": "Quick sync meeting"
      }
    ],
    "free_blocks": [
      {
        "start_time": "2025-10-29T10:00:00-07:00",
        "end_time": "2025-10-29T11:00:00-07:00",
        "duration_minutes": 60,
        "recommended_action": "Deep work time",
        "is_significant": true
      }
    ],
    "wake_up_recommendation_time": "2025-10-29T07:30:00-07:00",
    "metadata": {
      "preview_for": "tomorrow_morning",
      "generation_context": {
        "delivery_time": "evening",
        "reference_day": "2025-10-29"
      },
      "events_in": 10,
      "events_considered": 8,
      "truncated": false,
      "generation_ms": 36,
      "cache_key": "cache_key_here"
    }
  }
}
```

---

## Alexa API Endpoint: `/api/alexa/morning-summary`

### Authentication Required

All Alexa endpoints require bearer token authentication. Replace `YOUR_BEARER_TOKEN` with your actual token.

```bash
# Basic authenticated request
curl -X POST "http://localhost:8080/api/alexa/morning-summary" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

### With Query Parameters

```bash
# Full parameter example for Alexa
curl -X POST "http://localhost:8080/api/alexa/morning-summary?date=2025-10-29&timezone=America/Los_Angeles&detail_level=normal&prefer_ssml=true&max_events=50" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

### SSML Preference Examples

```bash
# Request with SSML for enhanced Alexa speech
curl -X POST "http://localhost:8080/api/alexa/morning-summary?prefer_ssml=true" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"

# Request without SSML (plain text only)
curl -X POST "http://localhost:8080/api/alexa/morning-summary?prefer_ssml=false" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

### Expected Alexa Response Format

```json
{
  "speech_text": "Tomorrow morning looks busy with 3 meetings between 6 AM and noon. Your day starts early at 7:30 AM with the team standup. You'll have a 45-minute break from 10 to 10:45 for deep work.",
  "summary": {
    "preview_for": "tomorrow_morning",
    "total_meetings_equivalent": 2.5,
    "early_start_flag": true,
    "density": "moderate",
    "back_to_back_count": 1,
    "timeframe_start": "2025-10-29T06:00:00-07:00",
    "timeframe_end": "2025-10-29T12:00:00-07:00",
    "wake_up_recommendation": "2025-10-29T06:00:00-07:00"
  },
  "ssml": "<speak>Tomorrow morning looks <emphasis level='moderate'>busy</emphasis> with 3 meetings between 6 AM and noon...</speak>"
}
```

---

## Production Examples

### Using with HTTPS

```bash
# General API via HTTPS
curl -X POST "https://your-domain.com/api/morning-summary?timezone=America/New_York"

# Alexa API via HTTPS
curl -X POST "https://your-domain.com/api/alexa/morning-summary" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

### Error Handling Examples

```bash
# Invalid timezone example
curl -X POST "http://localhost:8080/api/morning-summary?timezone=Invalid/Timezone"
# Expected: 500 error with descriptive message

# Missing bearer token for Alexa endpoint
curl -X POST "http://localhost:8080/api/alexa/morning-summary"
# Expected: 401 Unauthorized

# Invalid bearer token for Alexa endpoint
curl -X POST "http://localhost:8080/api/alexa/morning-summary" \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 Unauthorized
```

---

## Response Differences

| Field | General API | Alexa API | Notes |
|-------|-------------|-----------|-------|
| `speech_text` | ❌ | ✅ | Natural language summary for voice |
| `ssml` | ❌ | ✅ (optional) | Enhanced speech markup |
| `meeting_insights` | ✅ (full details) | ❌ | Complete meeting information |
| `free_blocks` | ✅ (full details) | ❌ | Detailed free time analysis |
| `metadata` | ✅ (complete) | ❌ | Full generation metadata |
| Authentication | ❌ | ✅ | Bearer token required |

## Common Use Cases

### For UI Applications
Use the general API endpoint (`/api/morning-summary`) to get structured data for web/mobile interfaces:

```bash
curl -X POST "http://localhost:8080/api/morning-summary?detail_level=detailed" \
  | jq '.summary.meeting_insights'
```

### For Voice Assistants
Use the Alexa API endpoint (`/api/alexa/morning-summary`) to get speech-ready responses:

```bash
curl -X POST "http://localhost:8080/api/alexa/morning-summary?prefer_ssml=true" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  | jq '.speech_text'
```

### For Analytics/Monitoring
Extract metadata from the general API:

```bash
curl -X POST "http://localhost:8080/api/morning-summary" \
  | jq '.summary.metadata'