"""HTTP client for downloading ICS calendar files."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from .models import ICSSource, ICSResponse
from .exceptions import ICSFetchError, ICSNetworkError, ICSTimeoutError, ICSAuthError

logger = logging.getLogger(__name__)


class ICSFetcher:
    """Async HTTP client for downloading ICS calendar files."""
    
    def __init__(self, settings):
        """Initialize ICS fetcher.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client: Optional[httpx.AsyncClient] = None
        
        logger.debug("ICS fetcher initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_client()
    
    async def _ensure_client(self):
        """Ensure HTTP client exists."""
        if self.client is None or self.client.is_closed:
            timeout = httpx.Timeout(
                connect=10.0,
                read=self.settings.request_timeout,
                write=10.0,
                pool=30.0
            )
            
            self.client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                verify=True,  # SSL verification
                headers={
                    'User-Agent': f'{self.settings.app_name}/1.0.0 ICS-Client',
                    'Accept': 'text/calendar, text/plain, */*',
                    'Accept-Charset': 'utf-8',
                    'Cache-Control': 'no-cache'
                }
            )
    
    async def _close_client(self):
        """Close HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
    
    async def fetch_ics(self, source: ICSSource, 
                       conditional_headers: Optional[Dict[str, str]] = None) -> ICSResponse:
        """Download ICS content from source.
        
        Args:
            source: ICS source configuration
            conditional_headers: Optional headers for conditional requests (If-Modified-Since, If-None-Match)
            
        Returns:
            ICS response with content or error information
        """
        await self._ensure_client()
        
        try:
            logger.info(f"Fetching ICS from {source.url}")
            
            # Prepare headers
            headers = {}
            
            # Add authentication headers
            auth_headers = source.auth.get_headers()
            headers.update(auth_headers)
            
            # Add custom headers
            headers.update(source.custom_headers)
            
            # Add conditional request headers
            if conditional_headers:
                headers.update(conditional_headers)
            
            # Make request with retry logic
            response = await self._make_request_with_retry(
                source.url, 
                headers, 
                source.timeout,
                source.validate_ssl
            )
            
            return self._create_response(response)
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching ICS from {source.url}: {e}")
            return ICSResponse(
                success=False,
                error_message=f"Request timeout after {source.timeout}s",
                status_code=None
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching ICS from {source.url}: {e.response.status_code}")
            
            if e.response.status_code == 401:
                error_msg = "Authentication failed - check credentials"
                raise ICSAuthError(error_msg, e.response.status_code)
            elif e.response.status_code == 403:
                error_msg = "Access forbidden - insufficient permissions"
                raise ICSAuthError(error_msg, e.response.status_code)
            else:
                return ICSResponse(
                    success=False,
                    status_code=e.response.status_code,
                    error_message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                    headers=dict(e.response.headers)
                )
        
        except httpx.NetworkError as e:
            logger.error(f"Network error fetching ICS from {source.url}: {e}")
            raise ICSNetworkError(f"Network error: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error fetching ICS from {source.url}: {e}")
            raise ICSFetchError(f"Unexpected error: {e}")
    
    async def _make_request_with_retry(self, url: str, headers: Dict[str, str], 
                                     timeout: int, verify_ssl: bool) -> httpx.Response:
        """Make HTTP request with retry logic.
        
        Args:
            url: URL to fetch
            headers: Request headers
            timeout: Request timeout
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            HTTP response
        """
        last_exception = None
        
        for attempt in range(self.settings.max_retries + 1):
            try:
                # Update client SSL verification if needed
                if not verify_ssl and self.client:
                    self.client._verify = False
                
                response = await self.client.get(
                    url,
                    headers=headers,
                    timeout=timeout
                )
                
                # Raise for HTTP error status codes (4xx, 5xx)
                response.raise_for_status()
                
                logger.debug(f"Successfully fetched ICS from {url} (attempt {attempt + 1})")
                return response
                
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                
                if attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff_factor ** attempt
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.settings.max_retries + 1}), "
                                 f"retrying in {backoff_time:.1f}s: {e}")
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    raise e
            
            except httpx.HTTPStatusError as e:
                # Don't retry HTTP errors (auth errors, not found, etc.)
                raise e
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise ICSFetchError("Maximum retries exceeded")
    
    def _create_response(self, http_response: httpx.Response) -> ICSResponse:
        """Create ICS response from HTTP response.
        
        Args:
            http_response: HTTP response object
            
        Returns:
            ICS response object
        """
        headers = dict(http_response.headers)
        
        # Handle 304 Not Modified
        if http_response.status_code == 304:
            logger.debug("ICS content not modified (304)")
            return ICSResponse(
                success=True,
                status_code=304,
                headers=headers,
                etag=headers.get('etag'),
                last_modified=headers.get('last-modified'),
                cache_control=headers.get('cache-control')
            )
        
        # Get content
        content = http_response.text
        content_type = headers.get('content-type', '').lower()
        
        # Validate content type
        if content_type and not any(ct in content_type for ct in ['text/calendar', 'text/plain']):
            logger.warning(f"Unexpected content type: {content_type}")
        
        # Basic content validation
        if not content or not content.strip():
            logger.error("Empty ICS content received")
            return ICSResponse(
                success=False,
                status_code=http_response.status_code,
                error_message="Empty content received",
                headers=headers
            )
        
        # Check for basic ICS markers
        if 'BEGIN:VCALENDAR' not in content:
            logger.warning("Content does not appear to be valid ICS format")
        
        logger.info(f"Successfully fetched ICS content ({len(content)} bytes)")
        
        return ICSResponse(
            success=True,
            content=content,
            status_code=http_response.status_code,
            headers=headers,
            etag=headers.get('etag'),
            last_modified=headers.get('last-modified'),
            cache_control=headers.get('cache-control')
        )
    
    async def test_connection(self, source: ICSSource) -> bool:
        """Test connection to ICS source.
        
        Args:
            source: ICS source to test
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing connection to {source.url}")
            
            # Make a HEAD request first for efficiency
            await self._ensure_client()
            
            headers = source.auth.get_headers()
            headers.update(source.custom_headers)
            
            response = await self.client.head(
                source.url,
                headers=headers,
                timeout=source.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Connection test successful for {source.url}")
                return True
            elif response.status_code == 405:  # Method not allowed, try GET
                logger.debug("HEAD not supported, testing with GET")
                response = await self.fetch_ics(source)
                return response.success
            else:
                logger.warning(f"Connection test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed for {source.url}: {e}")
            return False
    
    def get_conditional_headers(self, etag: Optional[str] = None, 
                              last_modified: Optional[str] = None) -> Dict[str, str]:
        """Get conditional request headers for caching.
        
        Args:
            etag: ETag value from previous response
            last_modified: Last-Modified value from previous response
            
        Returns:
            Dictionary of conditional headers
        """
        headers = {}
        
        if etag:
            headers['If-None-Match'] = etag
        
        if last_modified:
            headers['If-Modified-Since'] = last_modified
        
        return headers