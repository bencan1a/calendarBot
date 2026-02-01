"""Unit tests for ICS hash normalization functions.

These tests cover _normalize_ics_for_hashing and _compute_normalized_hash.
Tests verify that DTSTAMP lines are properly removed for stable hash computation
while real content changes are detected.
"""

from __future__ import annotations

import pytest

from calendarbot_lite.api import server

pytestmark = pytest.mark.unit


def test_normalize_removes_dtstamp_lines():
    """Verify DTSTAMP lines are removed during normalization."""
    # Test content with DTSTAMP mixed with other fields
    ics = "BEGIN:VEVENT\nDTSTAMP:20260201T002834Z\nSUMMARY:Meeting\nEND:VEVENT"

    normalized = server._normalize_ics_for_hashing(ics)

    # DTSTAMP should be removed
    assert 'DTSTAMP' not in normalized
    # Other fields should remain
    assert 'SUMMARY' in normalized
    assert 'BEGIN:VEVENT' in normalized
    assert 'END:VEVENT' in normalized


def test_normalize_removes_multiple_dtstamp_lines():
    """Verify multiple DTSTAMP lines are all removed."""
    ics = (
        "BEGIN:VCALENDAR\n"
        "DTSTAMP:20260201T000000Z\n"
        "BEGIN:VEVENT\n"
        "DTSTAMP:20260201T111111Z\n"
        "SUMMARY:Meeting 1\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "DTSTAMP:20260201T222222Z\n"
        "SUMMARY:Meeting 2\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )

    normalized = server._normalize_ics_for_hashing(ics)

    # All DTSTAMP lines should be removed
    assert 'DTSTAMP' not in normalized
    # Other content should remain
    assert 'SUMMARY:Meeting 1' in normalized
    assert 'SUMMARY:Meeting 2' in normalized
    assert normalized.count('BEGIN:VEVENT') == 2


def test_normalized_hash_stable_across_dtstamp_changes():
    """Hash should match when only DTSTAMP changes."""
    # Same event content, different DTSTAMP values
    ics1 = "DTSTAMP:20260201T000000Z\nSUMMARY:Test Event\n"
    ics2 = "DTSTAMP:20260201T999999Z\nSUMMARY:Test Event\n"

    hash1 = server._compute_normalized_hash(ics1)
    hash2 = server._compute_normalized_hash(ics2)

    # Hashes should match (DTSTAMP ignored)
    assert hash1 == hash2
    # Hash should be valid SHA-256 (64 hex chars)
    assert len(hash1) == 64
    # Verify it's a valid hex string
    assert all(c in '0123456789abcdef' for c in hash1)


def test_normalized_hash_detects_real_changes():
    """Hash should differ when event data changes."""
    ics1 = "DTSTAMP:20260201T000000Z\nSUMMARY:Old Meeting\n"
    ics2 = "DTSTAMP:20260201T000000Z\nSUMMARY:New Meeting\n"

    hash1 = server._compute_normalized_hash(ics1)
    hash2 = server._compute_normalized_hash(ics2)

    # Hashes should differ (real content changed)
    assert hash1 != hash2


def test_normalize_handles_empty_content():
    """Normalization handles empty content."""
    empty = ""
    normalized = server._normalize_ics_for_hashing(empty)
    assert normalized == ""

    hash_val = server._compute_normalized_hash(empty)
    assert len(hash_val) == 64  # Valid hash
    assert all(c in '0123456789abcdef' for c in hash_val)


def test_normalize_handles_no_dtstamp():
    """Normalization handles content without DTSTAMP."""
    ics = "BEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT"
    normalized = server._normalize_ics_for_hashing(ics)
    # Should return unchanged (no DTSTAMP to remove)
    assert normalized == ics


def test_normalize_preserves_line_endings():
    """Normalization preserves line endings."""
    ics = "LINE1\nDTSTAMP:12345\nLINE2\n"
    normalized = server._normalize_ics_for_hashing(ics)
    # Should preserve newlines
    assert normalized == "LINE1\nLINE2\n"


def test_normalize_handles_dtstamp_at_start():
    """Normalization handles DTSTAMP at the start of content."""
    ics = "DTSTAMP:20260201T000000Z\nBEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT"
    normalized = server._normalize_ics_for_hashing(ics)
    assert 'DTSTAMP' not in normalized
    assert normalized == "BEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT"


def test_normalize_handles_dtstamp_at_end():
    """Normalization handles DTSTAMP at the end of content."""
    ics = "BEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT\nDTSTAMP:20260201T000000Z"
    normalized = server._normalize_ics_for_hashing(ics)
    assert 'DTSTAMP' not in normalized
    assert normalized == "BEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT\n"


def test_normalize_handles_consecutive_dtstamp_lines():
    """Normalization handles consecutive DTSTAMP lines."""
    ics = "BEGIN:VEVENT\nDTSTAMP:1\nDTSTAMP:2\nDTSTAMP:3\nSUMMARY:Test\nEND:VEVENT"
    normalized = server._normalize_ics_for_hashing(ics)
    assert 'DTSTAMP' not in normalized
    assert normalized == "BEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT"


def test_normalize_does_not_affect_non_dtstamp_lines():
    """Normalization only removes DTSTAMP lines, not lines containing 'DTSTAMP' elsewhere."""
    # Line that starts with DTSTAMP should be removed
    # Line with DTSTAMP in description should be kept
    ics = (
        "BEGIN:VEVENT\n"
        "DTSTAMP:20260201T000000Z\n"
        "SUMMARY:Meeting about DTSTAMP field\n"
        "DESCRIPTION:We will discuss DTSTAMP handling\n"
        "END:VEVENT"
    )
    normalized = server._normalize_ics_for_hashing(ics)

    # DTSTAMP: line should be removed
    assert 'DTSTAMP:20260201T000000Z' not in normalized
    # But DTSTAMP in summary/description should remain
    assert 'DTSTAMP field' in normalized
    assert 'DTSTAMP handling' in normalized


def test_normalized_hash_different_for_different_event_fields():
    """Hash should differ when different event fields change."""
    base_ics = "DTSTAMP:20260201T000000Z\nSUMMARY:Test\nLOCATION:Room A\n"

    # Change location
    ics_location = "DTSTAMP:20260201T000000Z\nSUMMARY:Test\nLOCATION:Room B\n"

    # Change summary
    ics_summary = "DTSTAMP:20260201T000000Z\nSUMMARY:Different\nLOCATION:Room A\n"

    hash_base = server._compute_normalized_hash(base_ics)
    hash_location = server._compute_normalized_hash(ics_location)
    hash_summary = server._compute_normalized_hash(ics_summary)

    # All hashes should be different
    assert hash_base != hash_location
    assert hash_base != hash_summary
    assert hash_location != hash_summary


def test_normalized_hash_ignores_only_dtstamp_changes():
    """Hash should be stable when DTSTAMP changes but nothing else."""
    # Complex ICS with multiple fields
    ics_template = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:Test\n"
        "{dtstamp}"
        "BEGIN:VEVENT\n"
        "UID:123\n"
        "SUMMARY:Team Meeting\n"
        "LOCATION:Conference Room\n"
        "DTSTART:20260202T100000Z\n"
        "DTEND:20260202T110000Z\n"
        "{event_dtstamp}"
        "DESCRIPTION:Quarterly planning\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )

    ics1 = ics_template.format(
        dtstamp="DTSTAMP:20260201T000000Z\n",
        event_dtstamp="DTSTAMP:20260201T111111Z\n"
    )
    ics2 = ics_template.format(
        dtstamp="DTSTAMP:20260201T999999Z\n",
        event_dtstamp="DTSTAMP:20260201T888888Z\n"
    )

    hash1 = server._compute_normalized_hash(ics1)
    hash2 = server._compute_normalized_hash(ics2)

    # Hashes should match despite different DTSTAMP values
    assert hash1 == hash2


def test_normalized_hash_detects_subtle_changes():
    """Hash should detect even subtle content changes."""
    ics1 = "DTSTAMP:20260201T000000Z\nSUMMARY:Meeting at 2pm\n"
    ics2 = "DTSTAMP:20260201T000000Z\nSUMMARY:Meeting at 3pm\n"

    hash1 = server._compute_normalized_hash(ics1)
    hash2 = server._compute_normalized_hash(ics2)

    # Single character change should produce different hash
    assert hash1 != hash2


def test_normalize_handles_crlf_line_endings():
    """Normalization handles Windows-style CRLF line endings."""
    ics = "BEGIN:VEVENT\r\nDTSTAMP:20260201T000000Z\r\nSUMMARY:Test\r\nEND:VEVENT\r\n"
    normalized = server._normalize_ics_for_hashing(ics)

    # DTSTAMP line should be removed
    assert 'DTSTAMP' not in normalized
    # Other content should remain
    assert 'SUMMARY' in normalized


def test_normalized_hash_stable_across_whitespace_in_dtstamp():
    """Hash should ignore variations in DTSTAMP values (spaces, different timestamps)."""
    # These have different DTSTAMP values but same actual content
    ics1 = "SUMMARY:Test\nDTSTAMP:20260201T000000Z\nLOCATION:Room\n"
    ics2 = "SUMMARY:Test\nDTSTAMP:20260202T123456Z\nLOCATION:Room\n"

    hash1 = server._compute_normalized_hash(ics1)
    hash2 = server._compute_normalized_hash(ics2)

    # Hashes should match (only DTSTAMP differs)
    assert hash1 == hash2
