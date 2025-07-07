"""Mock HTTP servers for testing network operations."""

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


class MockHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock server."""

    def do_GET(self):
        """Handle GET requests."""
        self.server.request_count += 1
        path = self.path

        # Check if we have a specific response for this path
        if path in self.server.responses:
            response = self.server.responses[path]

            # Handle timeout simulation
            if response.get("timeout"):
                time.sleep(response.get("timeout_duration", 30))
                return

            # Handle delay simulation
            if response.get("delay"):
                time.sleep(response["delay"])

            # Send response
            status_code = response.get("status_code", 200)
            self.send_response(status_code)

            headers = response.get("headers", {})
            for header, value in headers.items():
                self.send_header(header, value)
            self.end_headers()

            content = response.get("content", "")
            if isinstance(content, str):
                content = content.encode()
            self.wfile.write(content)

        else:
            # Default 404 response
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_HEAD(self):
        """Handle HEAD requests."""
        self.server.request_count += 1
        path = self.path

        if path in self.server.responses:
            response = self.server.responses[path]
            status_code = response.get("status_code", 200)
            self.send_response(status_code)

            headers = response.get("headers", {})
            for header, value in headers.items():
                self.send_header(header, value)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress logging to avoid cluttering test output."""
        pass


class MockICSServer:
    """Mock HTTP server specifically for ICS calendar testing."""

    def __init__(self, host: str = "localhost", port: int = 8999):
        self.host = host
        self.port = port
        self.responses: Dict[str, Dict[str, Any]] = {}
        self.request_count = 0
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def set_response(
        self,
        path: str,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        delay: Optional[float] = None,
    ):
        """Set response for a specific path."""
        response_headers = headers or {"Content-Type": "text/calendar"}

        self.responses[path] = {
            "content": content,
            "status_code": status_code,
            "headers": response_headers,
        }

        if delay:
            self.responses[path]["delay"] = delay

    def set_timeout_response(self, path: str, timeout_duration: float = 30):
        """Set a timeout response for a specific path."""
        self.responses[path] = {"timeout": True, "timeout_duration": timeout_duration}

    def set_auth_required_response(self, path: str, realm: str = "Calendar"):
        """Set an authentication required response."""
        self.responses[path] = {
            "content": "Authentication Required",
            "status_code": 401,
            "headers": {"Content-Type": "text/plain", "WWW-Authenticate": f'Basic realm="{realm}"'},
        }

    def set_not_modified_response(self, path: str, etag: str = "12345"):
        """Set a 304 Not Modified response."""
        self.responses[path] = {
            "content": "",
            "status_code": 304,
            "headers": {"ETag": f'"{etag}"', "Last-Modified": "Wed, 01 Jan 2025 12:00:00 GMT"},
        }

    def clear_responses(self):
        """Clear all configured responses."""
        self.responses.clear()
        self.request_count = 0

    def start(self):
        """Start the mock server."""
        if self.running:
            return

        self.server = HTTPServer((self.host, self.port), MockHTTPHandler)
        self.server.responses = self.responses
        self.server.request_count = 0

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.running = True

        # Give the server a moment to start
        time.sleep(0.1)

    def stop(self):
        """Stop the mock server."""
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False

            if self.thread:
                self.thread.join(timeout=1)

    def get_request_count(self) -> int:
        """Get the number of requests received."""
        return self.server.request_count if self.server else 0

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"


class MockWebServer:
    """Mock web server for testing web API endpoints."""

    def __init__(self, host: str = "localhost", port: int = 8998):
        self.host = host
        self.port = port
        self.api_responses: Dict[str, Callable] = {}
        self.request_log: List[Dict[str, Any]] = []
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def set_api_handler(self, endpoint: str, handler: Callable):
        """Set a custom handler for an API endpoint."""
        self.api_responses[endpoint] = handler

    def start(self):
        """Start the mock web server."""
        if self.running:
            return

        class WebHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                self._handle_request(handler_self, "GET")

            def do_POST(handler_self):
                self._handle_request(handler_self, "POST")

            def log_message(handler_self, format, *args):
                pass  # Suppress logging

        def _handle_request(handler_self, method):
            parsed_url = urlparse(handler_self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # Log the request
            request_info = {
                "method": method,
                "path": path,
                "query_params": query_params,
                "timestamp": time.time(),
            }

            if method == "POST":
                content_length = int(handler_self.headers.get("Content-Length", 0))
                request_info["body"] = handler_self.rfile.read(content_length).decode()

            self.request_log.append(request_info)

            # Check if we have a custom handler for this endpoint
            if path in self.api_responses:
                try:
                    response = self.api_responses[path](request_info)

                    handler_self.send_response(response.get("status_code", 200))

                    headers = response.get("headers", {"Content-Type": "application/json"})
                    for header, value in headers.items():
                        handler_self.send_header(header, value)
                    handler_self.end_headers()

                    content = response.get("content", "")
                    if isinstance(content, dict):
                        content = json.dumps(content)
                    handler_self.wfile.write(content.encode())

                except Exception as e:
                    handler_self.send_response(500)
                    handler_self.end_headers()
                    handler_self.wfile.write(f"Handler error: {e}".encode())
            else:
                # Default 404 response
                handler_self.send_response(404)
                handler_self.end_headers()
                handler_self.wfile.write(b"API endpoint not found")

        self.server = HTTPServer((self.host, self.port), WebHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.running = True

        # Give the server a moment to start
        time.sleep(0.1)

    def stop(self):
        """Stop the mock web server."""
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False

            if self.thread:
                self.thread.join(timeout=1)

    def clear_request_log(self):
        """Clear the request log."""
        self.request_log.clear()

    def get_requests(self) -> List[Dict[str, Any]]:
        """Get all logged requests."""
        return self.request_log.copy()

    def get_requests_for_endpoint(self, endpoint: str) -> List[Dict[str, Any]]:
        """Get requests for a specific endpoint."""
        return [req for req in self.request_log if req["path"] == endpoint]


class NetworkSimulator:
    """Utility for simulating various network conditions."""

    @staticmethod
    def create_slow_server(ics_content: str, delay: float = 2.0) -> MockICSServer:
        """Create a server that responds slowly."""
        server = MockICSServer()
        server.set_response("/slow.ics", ics_content, delay=delay)
        return server

    @staticmethod
    def create_unreliable_server(ics_content: str, failure_rate: float = 0.5) -> MockICSServer:
        """Create a server that randomly fails."""
        server = MockICSServer()

        def unreliable_handler(request_info):
            import random

            if random.random() < failure_rate:
                return {
                    "status_code": 500,
                    "content": "Server Error",
                    "headers": {"Content-Type": "text/plain"},
                }
            else:
                return {
                    "status_code": 200,
                    "content": ics_content,
                    "headers": {"Content-Type": "text/calendar"},
                }

        return server

    @staticmethod
    def create_auth_server(
        ics_content: str, username: str = "test", password: str = "pass"
    ) -> MockICSServer:
        """Create a server that requires authentication."""
        server = MockICSServer()

        def auth_handler(request_info):
            import base64

            auth_header = request_info.get("headers", {}).get("Authorization")
            if not auth_header:
                return {
                    "status_code": 401,
                    "content": "Authentication Required",
                    "headers": {
                        "Content-Type": "text/plain",
                        "WWW-Authenticate": 'Basic realm="Calendar"',
                    },
                }

            # Decode basic auth
            try:
                auth_type, credentials = auth_header.split(" ", 1)
                if auth_type.lower() == "basic":
                    decoded = base64.b64decode(credentials).decode()
                    provided_username, provided_password = decoded.split(":", 1)

                    if provided_username == username and provided_password == password:
                        return {
                            "status_code": 200,
                            "content": ics_content,
                            "headers": {"Content-Type": "text/calendar"},
                        }
            except Exception:
                pass

            return {
                "status_code": 401,
                "content": "Invalid credentials",
                "headers": {"Content-Type": "text/plain"},
            }

        return server


# Utility functions for common test scenarios
def create_test_calendar_server(ics_content: str, port: int = 8999) -> MockICSServer:
    """Create a basic test calendar server."""
    server = MockICSServer(port=port)
    server.set_response("/test.ics", ics_content)
    return server


def create_conditional_request_server(ics_content: str, etag: str = "12345") -> MockICSServer:
    """Create a server that supports conditional requests."""
    server = MockICSServer()

    # Set initial response with ETag
    server.set_response(
        "/conditional.ics",
        ics_content,
        headers={
            "Content-Type": "text/calendar",
            "ETag": f'"{etag}"',
            "Last-Modified": "Wed, 01 Jan 2025 12:00:00 GMT",
        },
    )

    # Set 304 response for the same path (will be used for conditional requests)
    server.set_not_modified_response("/conditional.ics", etag)

    return server


def create_api_test_server(port: int = 8998) -> MockWebServer:
    """Create a basic API test server."""
    server = MockWebServer(port=port)

    # Set up default handlers for common endpoints
    def navigation_handler(request_info):
        return {"status_code": 200, "content": {"success": True, "html": "<html>Test</html>"}}

    def status_handler(request_info):
        return {
            "status_code": 200,
            "content": {"running": True, "host": "127.0.0.1", "port": 8998, "theme": "standard"},
        }

    server.set_api_handler("/api/navigate", navigation_handler)
    server.set_api_handler("/api/status", status_handler)

    return server
