"""Utility functions for calendarbot_lite test runner.

Remember to activate the venv before running: `. venv/bin/activate`
"""

import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.request import urlopen
import http.server
import socketserver

logger = logging.getLogger(__name__)


def find_free_port() -> int:
    """Find an available TCP port on localhost.
    
    Returns:
        Available port number
        
    Raises:
        OSError: If no free port can be found
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('localhost', 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        return port


def start_simple_http_server(path: Path, port: int) -> subprocess.Popen:
    """Start a simple HTTP server serving files from the given path.
    
    Args:
        path: Directory to serve files from
        port: Port to bind the server to
        
    Returns:
        Subprocess handle for the HTTP server
        
    Raises:
        FileNotFoundError: If path doesn't exist
        OSError: If server fails to start
    """
    if not path.exists():
        raise FileNotFoundError(f"Path {path} does not exist")
    
    # Use Python's built-in HTTP server module
    cmd = [
        "python", "-m", "http.server", str(port),
        "--bind", "127.0.0.1",
        "--directory", str(path)
    ]
    
    logger.debug("Starting HTTP server: %s", " ".join(cmd))
    
    # Start the server with output redirected to avoid noise
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(path)
    )
    
    # Give the server a moment to start
    time.sleep(0.5)
    
    # Check if the process started successfully
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise OSError(
            f"HTTP server failed to start. Exit code: {process.returncode}. "
            f"Stderr: {stderr.decode()}"
        )
    
    return process


def start_calendarbot_lite(port: int, env_overrides: Dict[str, str]) -> subprocess.Popen:
    """Start calendarbot_lite server as a subprocess.
    
    Args:
        port: Port for the calendarbot_lite server
        env_overrides: Environment variables to set for the process
        
    Returns:
        Subprocess handle for calendarbot_lite server
        
    Raises:
        OSError: If server fails to start
    """
    env = os.environ.copy()
    env.update(env_overrides)
    
    cmd = ["python", "-m", "calendarbot_lite", "--port", str(port)]
    
    logger.debug("Starting calendarbot_lite: %s", " ".join(cmd))
    logger.debug("Environment overrides: %s", env_overrides)
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    
    return process


def wait_for_whats_next(port: int, timeout: float = 30.0, retry_interval: float = 1.0) -> Dict[str, Any]:
    """Wait for whats-next endpoint to be ready and return response.
    
    Args:
        port: Port of the calendarbot_lite server
        timeout: Maximum time to wait in seconds
        retry_interval: Time between retry attempts in seconds
        
    Returns:
        JSON response from whats-next endpoint
        
    Raises:
        TimeoutError: If endpoint doesn't become ready within timeout
        Exception: If endpoint returns error or invalid JSON
    """
    url = f"http://127.0.0.1:{port}/api/whats-next"
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            with urlopen(url, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    logger.debug("Successfully got whats-next response: %s keys", list(data.keys()))
                    return data
                else:
                    last_error = f"HTTP {response.status}: {response.reason}"
                    
        except Exception as e:
            last_error = str(e)
            logger.debug("Waiting for whats-next endpoint (attempt failed: %s)", last_error)
        
        time.sleep(retry_interval)
    
    raise TimeoutError(
        f"whats-next endpoint not ready after {timeout}s. Last error: {last_error}"
    )


def compare_expected_actual(expected: Dict[str, Any], actual: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Compare expected vs actual test results.
    
    Args:
        expected: Expected test result structure
        actual: Actual API response from whats-next
        
    Returns:
        Tuple of (pass_bool, diff_structure)
    """
    diff_struct = {
        "expected": expected,
        "actual": actual,
        "differences": [],
        "missing_fields": [],
        "extra_fields": [],
    }
    
    # Support two schemas: legacy 'events' array and current 'meeting' object.
    if "meeting" in expected or "meeting" in actual:
        expected_meeting = expected.get("meeting", {})
        actual_meeting = actual.get("meeting", None)

        # Handle case where both expected and actual are None
        if expected_meeting is None and actual_meeting is None:
            # Both null, this is valid (e.g., no meetings)
            pass
        elif actual_meeting is None:
            diff_struct["differences"].append(
                f"Meeting missing: expected meeting {expected_meeting}, got {actual_meeting}"
            )
        else:
            # Compare simple scalar fields
            for field in ["meeting_id", "subject", "description", "location"]:
                if field in expected_meeting:
                    expected_val = expected_meeting.get(field)
                    actual_val = actual_meeting.get(field)

                    # Special handling for meeting_id: allow pattern matching with wildcards
                    if field == "meeting_id" and expected_val and "*" in expected_val:
                        # Convert glob pattern to regex
                        import re
                        pattern = expected_val.replace("*", ".*")
                        if not re.fullmatch(pattern, actual_val or ""):
                            diff_struct["differences"].append(
                                f"Meeting field '{field}' mismatch: expected pattern {expected_val!r}, got {actual_val!r}"
                            )
                    elif expected_val != actual_val:
                        diff_struct["differences"].append(
                            f"Meeting field '{field}' mismatch: expected {expected_val!r}, got {actual_val!r}"
                        )
            # Compare attendees (list)
            if "attendees" in expected_meeting:
                if expected_meeting.get("attendees", []) != actual_meeting.get("attendees", []):
                    diff_struct["differences"].append(
                        f"Meeting attendees mismatch: expected {expected_meeting.get('attendees')}, got {actual_meeting.get('attendees')}"
                    )
            # Compare start_iso (datetime) and duration_seconds (numeric)
            if "start_iso" in expected_meeting:
                try:
                    expected_dt = normalize_datetime_to_utc(expected_meeting["start_iso"])
                    actual_dt = normalize_datetime_to_utc(actual_meeting.get("start_iso"))
                    if abs((expected_dt - actual_dt).total_seconds()) > 60:
                        diff_struct["differences"].append(
                            f"Meeting start_iso mismatch: expected {expected_meeting['start_iso']}, got {actual_meeting.get('start_iso')}"
                        )
                except Exception as e:
                    diff_struct["differences"].append(f"Failed to compare meeting start_iso: {e}")
            if "duration_seconds" in expected_meeting:
                try:
                    exp_dur = int(expected_meeting["duration_seconds"])
                    act_dur = int(actual_meeting.get("duration_seconds", -1))
                    if exp_dur != act_dur:
                        diff_struct["differences"].append(
                            f"Meeting duration_seconds mismatch: expected {exp_dur}, got {act_dur}"
                        )
                except Exception as e:
                    diff_struct["differences"].append(f"Failed to compare meeting duration_seconds: {e}")
        
        # Top-level key checks
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        diff_struct["missing_fields"] = list(expected_keys - actual_keys)
        diff_struct["extra_fields"] = list(actual_keys - expected_keys)
        
        has_differences = len(diff_struct["differences"]) > 0 or len(diff_struct["missing_fields"]) > 0
        return (not has_differences), diff_struct

    # Fallback to legacy 'events' array comparison
    expected_events = expected.get("events", [])
    actual_events = actual.get("events", [])
    
    if len(expected_events) != len(actual_events):
        diff_struct["differences"].append(
            f"Event count mismatch: expected {len(expected_events)}, got {len(actual_events)}"
        )
    
    # Compare individual events
    for i, expected_event in enumerate(expected_events):
        if i >= len(actual_events):
            diff_struct["differences"].append(f"Missing event at index {i}: {expected_event}")
            continue
            
        actual_event = actual_events[i]
        
        # Compare key fields
        for field in ["start_datetime", "end_datetime", "summary", "uid"]:
            if field in expected_event:
                expected_val = expected_event[field]
                actual_val = actual_event.get(field)
                
                if field.endswith("_datetime"):
                    # Normalize datetime comparison
                    if not _datetime_matches(expected_val, actual_val):
                        diff_struct["differences"].append(
                            f"Event {i} {field} mismatch: expected {expected_val}, got {actual_val}"
                        )
                else:
                    if expected_val != actual_val:
                        diff_struct["differences"].append(
                            f"Event {i} {field} mismatch: expected {expected_val}, got {actual_val}"
                        )
    
    # Check for missing/extra fields in top-level response
    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())
    
    diff_struct["missing_fields"] = list(expected_keys - actual_keys)
    diff_struct["extra_fields"] = list(actual_keys - expected_keys)
    
    # Determine if test passes
    has_differences = (
        len(diff_struct["differences"]) > 0 or
        len(diff_struct["missing_fields"]) > 0
    )
    
    pass_bool = not has_differences
    
    return pass_bool, diff_struct


def _datetime_matches(expected: str, actual: Optional[str]) -> bool:
    """Compare datetime strings with normalization.
    
    Args:
        expected: Expected datetime string
        actual: Actual datetime string (may be None)
        
    Returns:
        True if datetimes match when normalized
    """
    if actual is None:
        return False
    
    try:
        # Normalize both to UTC for comparison
        expected_dt = normalize_datetime_to_utc(expected)
        actual_dt = normalize_datetime_to_utc(actual)
        
        # Allow small time differences (up to 1 minute) to account for processing delays
        diff_seconds = abs((expected_dt - actual_dt).total_seconds())
        return diff_seconds <= 60.0
        
    except Exception as e:
        logger.warning("Failed to parse datetimes for comparison: %s", e)
        return False


def normalize_datetime_to_utc(iso_str: str) -> datetime:
    """Normalize ISO 8601 datetime string to UTC datetime object.
    
    Args:
        iso_str: ISO 8601 datetime string (with or without timezone)
        
    Returns:
        UTC datetime object
        
    Raises:
        ValueError: If datetime string cannot be parsed
    """
    try:
        # Parse the datetime - handle both with and without timezone info
        if iso_str.endswith('Z'):
            dt = datetime.fromisoformat(iso_str[:-1]).replace(tzinfo=timezone.utc)
        elif '+' in iso_str[-6:] or '-' in iso_str[-6:]:
            # Has timezone offset
            dt = datetime.fromisoformat(iso_str)
        else:
            # Assume UTC if no timezone specified
            dt = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        
        # Convert to UTC
        return dt.astimezone(timezone.utc)
        
    except Exception as e:
        raise ValueError(f"Cannot parse datetime '{iso_str}': {e}") from e


def cleanup_processes(*processes: subprocess.Popen) -> None:
    """Gracefully terminate subprocess handles.
    
    Args:
        *processes: Variable number of subprocess.Popen objects to clean up
    """
    for process in processes:
        if process.poll() is None:  # Process is still running
            try:
                # Try graceful termination first
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    process.kill()
                    process.wait(timeout=2.0)
                logger.debug("Cleaned up process PID %s", process.pid)
            except Exception as e:
                logger.warning("Failed to clean up process PID %s: %s", process.pid, e)