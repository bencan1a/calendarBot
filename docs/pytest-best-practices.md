# Pytest Best Practices for CalendarBot

**Version:** 1.0
**Last Updated:** 2025-11-06
**Based on:** Phases 1-3 test quality improvement findings

---

## Core Principles

### 1. Tests Must Fail When Implementation Breaks

**The Golden Rule:** If you comment out the implementation, the test MUST fail.

```python
# ✅ GOOD: Test fails if deduplication breaks
def test_deduplicate_removes_duplicate():
    events = [
        create_event(id="dup"),
        create_event(id="dup"),
        create_event(id="unique"),
    ]
    result = deduplicate(events)
    assert len(result) == 2  # Fails if dedup doesn't work
    assert [e.id for e in result].count("dup") == 1
```

```python
# ❌ BAD: Test passes even if deduplication is broken
def test_deduplicate():
    result = deduplicate([])  # Empty input, nothing to test
    assert isinstance(result, list)  # Always passes
```

### 2. Unconditional Assertions Always

**Never use `if` statements in test bodies.** All assertions must execute.

```python
# ❌ BAD: Assertion might not run
def test_ssml_generation():
    response = generate_response()
    if response.ssml:  # Test passes if ssml is None!
        assert response.ssml.startswith("<speak>")
```

```python
# ✅ GOOD: Assertion always runs
def test_ssml_generation():
    response = generate_response()
    assert response.ssml is not None, "SSML must be generated"
    assert response.ssml.startswith("<speak>")
    assert response.ssml.endswith("</speak>")
```

### 3. Test ONE Specific Outcome

**Don't accept multiple outcomes as success.**

```python
# ❌ BAD: Accepts multiple outcomes
def test_health_check():
    result = check_health()
    assert result in [200, 204, 304]  # Which is correct?
```

```python
# ✅ GOOD: Tests specific outcome
def test_health_check_success():
    result = check_health()
    assert result == 200  # One specific expected result
```

---

## Critical Anti-Patterns to Avoid

### Anti-Pattern #1: Accepting Multiple Exit Codes

```python
# ❌ NEVER accept multiple outcomes as success
assert exit_code in [0, 1, 2]

# ✅ Test ONE specific exit code
assert exit_code == 0, "Installation should succeed with exit code 0"
```

### Anti-Pattern #2: Testing String Constants Instead of Behavior

```python
# ❌ Checking string presence doesn't verify functionality
def test_config_file():
    run_installer()
    config = read_file("config.txt")
    assert "timezone=UTC" in config  # String exists, but is it used?

# ✅ Verify actual behavior
def test_timezone_configuration():
    run_installer()
    app = load_config()
    assert app.get_timezone() == "UTC"  # Tests actual behavior
```

### Anti-Pattern #3: Setting Config Without Verification

```python
# ❌ Sets config but doesn't verify it took effect
def test_set_config():
    set_config("max_events", 50)
    # No assertion - did it actually apply?

# ✅ Verify config was applied
def test_set_config():
    set_config("max_events", 50)
    assert get_config("max_events") == 50
    # Bonus: verify it affects behavior
    result = get_events()
    assert len(result) <= 50
```

### Anti-Pattern #4: Over-Mocking (Mocking Business Logic)

```python
# ❌ Mocks the thing being tested
def test_deduplication():
    with patch('myapp.deduplicate') as mock_dedup:
        mock_dedup.return_value = [event1, event2]  # Mocked!
        result = deduplicate([event1, event1, event2])
        assert len(result) == 2  # Test proves nothing

# ✅ Only mock external dependencies
def test_deduplication():
    # No mocking - test the real function
    result = deduplicate([event1, event1, event2])
    assert len(result) == 2
    assert result == [event1, event2]
```

**What to Mock:**
- ✅ HTTP requests (network I/O)
- ✅ File system operations
- ✅ Database calls
- ✅ Time/date (for deterministic tests)
- ✅ Random number generation

**What NOT to Mock:**
- ❌ Business logic
- ❌ Data transformations
- ❌ Pure functions
- ❌ The function you're testing

### Anti-Pattern #5: Creating Data Never Used

```python
# ❌ Creates event but never verifies it
def test_add_event():
    event = create_event("Meeting")
    add_to_calendar(event)
    # No assertion - event was created but not verified

# ✅ Verify data was actually used
def test_add_event():
    event = create_event("Meeting")
    add_to_calendar(event)

    calendar = get_calendar()
    assert len(calendar) == 1
    assert calendar[0].subject == "Meeting"
```

### Anti-Pattern #6: Conditional Assertions

**Already covered in Core Principles, but worth repeating:**

```python
# ❌ NEVER
if condition:
    assert something

# ✅ ALWAYS
assert something, "Clear failure message"
```

### Anti-Pattern #7: Testing Test Infrastructure

```python
# ❌ Tests helper function, not actual feature
def test_correlation_id():
    id = generate_correlation_id()
    assert len(id) > 0  # Just tests generation

# ✅ Tests actual propagation
def test_correlation_id_propagation():
    correlation_id = "test-123"
    set_correlation_id(correlation_id)

    with patch('httpx.Client.get') as mock_get:
        client = InstrumentedHTTPClient()
        client.get("https://api.example.com")

        # Verify ID is in actual HTTP headers
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['headers']['X-Request-ID'] == correlation_id
```

### Anti-Pattern #8: Testing --help Instead of Functionality

```python
# ❌ Tests --help flag, not actual feature
def test_installer():
    result = run("installer.sh --help")
    assert result.exit_code == 0

# ✅ Tests actual installation
def test_installer():
    result = run("installer.sh --install")
    assert result.exit_code == 0
    assert file_exists("/etc/myapp/config.conf")
    assert service_is_running("myapp")
```

### Anti-Pattern #9: Performance Claims Without Measurement

```python
# ❌ Claims efficiency but doesn't measure
def test_memory_efficient_parsing():
    result = parse_large_file()
    assert result.success  # No memory measurement!

# ✅ Actually measures performance
def test_memory_efficient_parsing():
    import tracemalloc

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    result = parse_large_file(events=10000)

    snapshot_after = tracemalloc.take_snapshot()
    memory_mb = sum(s.size for s in snapshot_after.statistics('lineno')) / 1024 / 1024

    assert result.success
    assert memory_mb < 50, f"Used {memory_mb:.1f}MB - too much!"
```

### Anti-Pattern #10: Missing State Verification

```python
# ❌ Calls function but doesn't verify state changed
def test_record_error():
    tracker.record_error(url)
    # No verification!

# ✅ Verifies state actually changed
def test_record_error():
    tracker.record_error(url)

    health = tracker.get_health(url)
    assert health.error_count == 1
    assert health.last_error_time is not None
    assert health.status == HealthStatus.DEGRADED
```

---

## Modern Pytest Best Practices

### 1. Let Pytest's Assertion Rewriting Do Its Job

**Modern pytest doesn't need custom error messages for simple assertions.**

```python
# ❌ Unnecessary custom message (pytest shows this automatically)
assert len(events) == 5, "Should have 5 events"

# ✅ Pytest's automatic output is excellent
assert len(events) == 5

# Pytest shows:
# AssertionError: assert 3 == 5
#  +  where 3 = len([<Event 'Meeting'>, <Event 'Standup'>, <Event 'Review'>])
```

**When custom messages ADD value:**

```python
# ✅ Explains business rule
assert user.can_delete(post), \
    "Authors should be able to delete their own posts per policy #42"

# ✅ Documents known quirk
assert len(result.events) == 1, \
    "Parser currently keeps TRANSPARENT events (maps to 'tentative'). " \
    "If this fails, parser behavior changed - update test."

# ✅ Clarifies complex condition
assert is_business_hours(event_time), \
    f"Event at {event_time} should be within business hours (9 AM - 5 PM)"
```

### 2. Comprehensive Test Docstrings

**Good docstrings explain WHAT is tested and WHAT is NOT tested.**

```python
def test_alexa_launch_intent_no_meetings():
    """Test launch intent switches to morning summary when no meetings today.

    ARCHITECTURAL LIMITATION: Mocks call_calendarbot_api() because current
    architecture uses urllib.request without dependency injection.

    WHAT THIS VERIFIES:
    ✅ Switching logic detects "no meetings today" condition
    ✅ Handler makes exactly 2 API calls in correct sequence
    ✅ Query parameters are correctly constructed

    WHAT THIS DOES NOT VERIFY (requires integration test):
    ❌ Actual HTTP requests work (network I/O)
    ❌ urllib.request.urlopen() behavior
    ❌ Bearer token authentication

    TODO: Refactor to support dependency injection for better testing.
    """
```

### 3. Verify Causes, Not Just Effects

```python
# ❌ Tests effect (fallback used) but not cause (why?)
def test_fallback_logic():
    parsed_events = []  # Simulates "all sources failed"
    result = apply_fallback(parsed_events)
    assert result.used_fallback is True  # Effect only

# ✅ Tests cause (threshold detection)
def test_fallback_triggers_when_below_threshold():
    num_sources = 5
    threshold = 3
    num_sources_processed = 2  # Below threshold
    parsed_events = []

    result = apply_fallback(
        events=parsed_events,
        sources_processed=num_sources_processed,
        threshold=threshold
    )

    assert result.used_fallback is True, \
        f"Fallback should trigger when {num_sources_processed} < {threshold}"
    assert result.reason == "sources_below_threshold"
```

### 4. Complete Loop Verification

```python
# ❌ Only checks first and last
def test_events_sorted():
    events = sort_events([event3, event1, event2])
    assert events[0] == event1
    assert events[-1] == event3
    # Doesn't verify event2 is in correct position!

# ✅ Verifies entire sequence
def test_events_sorted():
    events = sort_events([event3, event1, event2])

    # Verify complete order
    assert events == [event1, event2, event3]

    # Verify ascending order property
    for i in range(len(events) - 1):
        assert events[i].start <= events[i + 1].start
```

### 5. Test Data Validation

**Verify test data contains what you claim to filter.**

```python
# ❌ Doesn't verify input contains cancelled events
def test_filter_cancelled():
    result = parse_ics(CALENDAR_ICS)
    for event in result.events:
        assert event.status != "CANCELLED"
    # But was there ever a cancelled event to filter?

# ✅ Verifies test data is correct
def test_filter_cancelled():
    # Verify input contains what we claim
    assert "STATUS:CANCELLED" in CALENDAR_ICS, \
        "Test data must contain cancelled events"

    result = parse_ics(CALENDAR_ICS)

    # Verify filtering happened
    assert len(result.events) < total_events_in_calendar
    for event in result.events:
        assert event.status != "CANCELLED"
    assert result.filtered_count > 0
```

---

## Testing Patterns by Category

### HTTP/Network Tests

**Mock at the HTTP client level, not business logic level.**

```python
@pytest.mark.asyncio
async def test_fetch_calendar_with_retry():
    """Test HTTP fetcher retries on failure."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Simulate failure then success
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.text = AsyncMock(return_value="ICS_DATA")

        mock_get.side_effect = [
            mock_response_fail,
            mock_response_success
        ]

        result = await fetch_calendar(url)

        assert result.success is True
        assert mock_get.call_count == 2  # Verify retry happened
```

### Security Tests

**Test actual security properties, not just that checks exist.**

```python
def test_ssrf_protection():
    """Test SSRF protection blocks non-HTTP schemes and internal IPs."""
    # Test actual blocking behavior
    assert validate_url("ftp://example.com") is False
    assert validate_url("file:///etc/passwd") is False
    assert validate_url("http://localhost/admin") is False
    assert validate_url("http://192.168.1.1/api") is False

    # Test allowed URLs
    assert validate_url("https://example.com/calendar.ics") is True
```

### Database/State Tests

**Verify state changes after operations.**

```python
def test_user_registration():
    """Test user registration creates account and sends email."""
    # Setup
    email = "test@example.com"

    # Execute
    result = register_user(email=email, password="secret")

    # Verify state changes
    assert result.success is True

    # Database state
    user = db.get_user(email=email)
    assert user is not None
    assert user.email == email
    assert user.is_verified is False

    # Email sent
    assert len(mock_email.sent) == 1
    assert mock_email.sent[0].to == email
```

### Async Tests

**Use pytest-asyncio properly.**

```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test system handles concurrent requests correctly."""
    # Launch multiple concurrent requests
    tasks = [
        fetch_calendar(url1),
        fetch_calendar(url2),
        fetch_calendar(url3)
    ]

    results = await asyncio.gather(*tasks)

    # Verify all succeeded
    assert all(r.success for r in results)
    assert len(results) == 3
```

---

## Test Organization

### File Structure

```
tests/
├── lite/
│   ├── unit/               # Fast, isolated unit tests
│   ├── integration/        # Integration tests (multiple components)
│   ├── e2e/               # End-to-end tests
│   ├── performance/       # Performance benchmarks
│   └── smoke/             # Smoke tests (critical path)
```

### Test Naming Convention

```python
# Pattern: test_[function]_when_[condition]_then_[expected]

def test_parse_ics_when_valid_then_returns_events():
    """Clear from name what's being tested."""
    pass

def test_parse_ics_when_empty_then_returns_error():
    """Each test covers one scenario."""
    pass
```

### Test Class Organization

```python
class TestEventParser:
    """Group related tests by component."""

    def test_parse_valid_event(self):
        """Happy path."""
        pass

    def test_parse_missing_required_field(self):
        """Error case."""
        pass

    def test_parse_malformed_datetime(self):
        """Edge case."""
        pass
```

---

## Quick Reference: Test Quality Checklist

### Before Committing Tests, Verify:

- [ ] **Unconditional assertions** - No `if` statements in test body
- [ ] **Would fail if broken** - Comment out implementation, test fails
- [ ] **Tests ONE outcome** - Not accepting multiple results as success
- [ ] **Mocks externals only** - Business logic runs for real
- [ ] **Verifies state changes** - Not just that function completed
- [ ] **Complete verification** - Loops check all items, not just first/last
- [ ] **Clear docstring** - Explains what IS and ISN'T tested
- [ ] **Good test data** - Inputs contain what you claim to filter/transform
- [ ] **Appropriate scope** - Unit tests are fast, integration tests are thorough
- [ ] **Follows naming convention** - `test_X_when_Y_then_Z`

---

## Common Mistakes and Fixes

### Mistake: Testing Multiple Things in One Test

```python
# ❌ Tests too many things
def test_user_workflow():
    user = create_user()
    user.login()
    user.update_profile()
    user.logout()
    # If this fails, which part broke?

# ✅ Separate tests
def test_user_creation():
    user = create_user()
    assert user.id is not None

def test_user_login():
    user = create_user()
    result = user.login()
    assert result.success is True

def test_user_profile_update():
    user = create_user()
    user.login()
    result = user.update_profile(name="New Name")
    assert result.success is True
    assert user.name == "New Name"
```

### Mistake: Brittle Tests (Over-Specified)

```python
# ❌ Breaks if implementation details change
def test_generate_summary():
    summary = generate_summary(events)
    assert summary == "You have 3 meetings: Meeting at 10:00, Standup at 11:00, Review at 15:00"
    # Breaks if we change punctuation or format

# ✅ Tests essential properties
def test_generate_summary():
    summary = generate_summary(events)
    assert "3 meetings" in summary
    assert all(e.subject in summary for e in events)
    assert len(summary) > 0
```

### Mistake: Flaky Tests (Non-Deterministic)

```python
# ❌ Uses actual time (flaky)
def test_upcoming_events():
    now = datetime.now()  # Changes every second!
    events = get_upcoming_events(now)
    assert len(events) > 0  # Might fail at different times

# ✅ Uses fixed time
def test_upcoming_events():
    fixed_time = datetime(2025, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    events = get_upcoming_events(fixed_time)
    assert len(events) == 2  # Deterministic
```

---

## Summary: The Three Questions

**Every test must answer YES to all three:**

1. **Does this test verify actual behavior?** (Not string constants, not --help output)
2. **Will this test fail if the implementation breaks?** (Comment out code, test fails)
3. **Are all assertions unconditional?** (No `if` statements that might skip checks)

If YES to all three: **Good test** ✅
If NO to any: **Fix before committing** ❌

---

**Last Updated:** 2025-11-06
**Based On:** CalendarBot Phases 1-3 test quality improvements
**References:**
- [/tmp/test-validation-guide.md](file:///tmp/test-validation-guide.md)
- [/tmp/phase2-reality-vs-expectations.md](file:///tmp/phase2-reality-vs-expectations.md)
- [/tmp/phase3-completion-report.md](file:///tmp/phase3-completion-report.md)
