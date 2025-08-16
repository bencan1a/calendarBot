"""Cache key generation utilities and strategies for standardized caching.

Cache Strategy Implementation - Cache Key Generation component.
Provides consistent, collision-resistant cache key generation across all cache layers.
"""

import hashlib
import json
import logging
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class KeyStrategy(Enum):
    """Cache key generation strategies."""

    SIMPLE = "simple"  # Basic string concatenation
    HASH = "hash"  # SHA256 hash for complex objects
    HIERARCHICAL = "hierarchical"  # Nested key structure
    VERSIONED = "versioned"  # Include version/timestamp
    NORMALIZED = "normalized"  # URL/path normalization


@dataclass
class CacheKeyConfig:
    """Configuration for cache key generation."""

    strategy: KeyStrategy = KeyStrategy.SIMPLE
    max_length: int = 250  # Maximum key length before hashing
    include_version: bool = False  # Include version in key
    normalize_paths: bool = True  # Normalize file paths/URLs
    case_sensitive: bool = True  # Case sensitivity for keys
    hash_algorithm: str = "sha256"  # Hash algorithm for complex keys
    separator: str = ":"  # Key component separator
    prefix: str = ""  # Optional key prefix


class CacheKeyGenerator:
    """Generates standardized cache keys for different data types.

    Provides consistent, collision-resistant cache key generation
    with support for multiple strategies and configurations.
    """

    def __init__(self, config: Optional[CacheKeyConfig] = None):
        """Initialize cache key generator.

        Args:
            config: Optional configuration for key generation
        """
        self.config = config or CacheKeyConfig()
        self.logger = logger

    def generate_simple_key(self, *components: str) -> str:
        """Generate a simple concatenated cache key.

        Args:
            *components: String components to concatenate

        Returns:
            Generated cache key
        """
        # Filter out None/empty components
        valid_components = [str(c) for c in components if c is not None and str(c).strip()]

        if not valid_components:
            raise ValueError("At least one valid component required for key generation")

        # Apply case sensitivity
        if not self.config.case_sensitive:
            valid_components = [c.lower() for c in valid_components]

        # Join with separator
        key = self.config.separator.join(valid_components)

        # Add prefix if configured
        if self.config.prefix:
            key = f"{self.config.prefix}{self.config.separator}{key}"

        # Check length and hash if needed
        if len(key) > self.config.max_length:
            key = self._hash_key(key)

        return key

    def generate_object_key(self, obj: Any, *additional_components: str) -> str:
        """Generate cache key for complex objects.

        Args:
            obj: Object to generate key for
            *additional_components: Additional string components

        Returns:
            Generated cache key
        """
        try:
            # Convert object to deterministic string representation
            obj_str = self._serialize_object(obj)

            # Combine with additional components
            components = [obj_str, *additional_components]

            # Generate hash since objects are typically complex
            key_data = self.config.separator.join(str(c) for c in components if c)

            if self.config.prefix:
                key_data = f"{self.config.prefix}{self.config.separator}{key_data}"

            return self._hash_key(key_data)

        except Exception as e:
            self.logger.warning(f"Error generating object key: {e}")
            # Fallback to string representation
            fallback_key = str(hash(str(obj)))
            return self.generate_simple_key(fallback_key, *additional_components)

    def generate_url_key(
        self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None
    ) -> str:
        """Generate cache key for HTTP requests.

        Args:
            url: Request URL
            params: Optional query parameters
            headers: Optional relevant headers for caching

        Returns:
            Generated cache key for HTTP request
        """
        # Normalize URL
        normalized_url = self._normalize_url(url) if self.config.normalize_paths else url

        components = [normalized_url]

        # Add sorted parameters for consistency
        if params:
            param_str = self._serialize_params(params)
            components.append(f"params_{param_str}")

        # Add relevant headers
        if headers:
            # Only include cache-relevant headers
            cache_headers = {
                k.lower(): v
                for k, v in headers.items()
                if k.lower() in ["accept", "accept-encoding", "user-agent"]
            }
            if cache_headers:
                header_str = self._serialize_params(cache_headers)
                components.append(f"headers_{header_str}")

        return self.generate_simple_key(*components)

    def generate_file_key(
        self,
        file_path: str | Path,
        modification_time: Optional[datetime] = None,
        content_hash: Optional[str] = None,
    ) -> str:
        """Generate cache key for file-based data.

        Args:
            file_path: Path to the file
            modification_time: Optional file modification time
            content_hash: Optional content hash for versioning

        Returns:
            Generated cache key for file
        """
        # Normalize path
        path_str = str(file_path)
        if self.config.normalize_paths:
            path_str = self._normalize_path(path_str)

        components = [path_str]

        # Add modification time for versioning
        if modification_time:
            mod_str = modification_time.isoformat()
            components.append(f"mod_{mod_str}")

        # Add content hash if available
        if content_hash:
            components.append(f"hash_{content_hash}")

        return self.generate_simple_key(*components)

    def generate_event_key(
        self,
        source: str,
        event_id: Optional[str] = None,
        filters: Optional[dict] = None,
        time_range: Optional[tuple] = None,
    ) -> str:
        """Generate cache key for calendar event data.

        Args:
            source: Event source identifier
            event_id: Optional specific event ID
            filters: Optional event filters
            time_range: Optional time range tuple (start, end)

        Returns:
            Generated cache key for event data
        """
        components = [source]

        if event_id:
            components.append(f"event_{event_id}")

        if filters:
            filter_str = self._serialize_params(filters)
            components.append(f"filters_{filter_str}")

        if time_range:
            start_str = time_range[0].isoformat() if time_range[0] else "none"
            end_str = time_range[1].isoformat() if time_range[1] else "none"
            components.append(f"range_{start_str}_{end_str}")

        return self.generate_simple_key(*components)

    def generate_layout_key(
        self,
        layout_name: str,
        config: dict,
        theme: Optional[str] = None,
        viewport: Optional[tuple] = None,
    ) -> str:
        """Generate cache key for layout computation results.

        Args:
            layout_name: Name of the layout
            config: Layout configuration dictionary
            theme: Optional theme identifier
            viewport: Optional viewport dimensions (width, height)

        Returns:
            Generated cache key for layout
        """
        components = [layout_name]

        # Add configuration hash
        config_str = self._serialize_params(config)
        components.append(f"config_{config_str}")

        if theme:
            components.append(f"theme_{theme}")

        if viewport:
            components.append(f"viewport_{viewport[0]}x{viewport[1]}")

        return self.generate_simple_key(*components)

    def generate_versioned_key(self, base_key: str, version: str | int | datetime) -> str:
        """Generate versioned cache key.

        Args:
            base_key: Base cache key
            version: Version identifier (string, number, or datetime)

        Returns:
            Versioned cache key
        """
        version_str = version.isoformat() if isinstance(version, datetime) else str(version)

        return f"{base_key}{self.config.separator}v_{version_str}"

    def _serialize_object(self, obj: Any) -> str:
        """Serialize object to deterministic string.

        Args:
            obj: Object to serialize

        Returns:
            Deterministic string representation
        """
        try:
            # Handle common types specially for better keys
            if isinstance(obj, (dict, list)):
                return json.dumps(obj, sort_keys=True, default=str)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if hasattr(obj, "__dict__"):
                # For custom objects, use their dict representation
                return json.dumps(obj.__dict__, sort_keys=True, default=str)
            return str(obj)
        except Exception:
            # Fallback to string representation
            return str(obj)

    def _serialize_params(self, params: dict) -> str:
        """Serialize parameters to deterministic string.

        Args:
            params: Parameters dictionary

        Returns:
            Deterministic parameter string
        """
        try:
            # Sort keys for consistency
            sorted_params = {k: v for k, v in sorted(params.items()) if v is not None}
            return json.dumps(sorted_params, sort_keys=True, default=str)
        except Exception:
            # Fallback to simple string representation
            return str(sorted(params.items()))

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent cache keys.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        try:
            # Parse and normalize URL components
            parsed = urllib.parse.urlparse(url)

            # Normalize scheme and netloc to lowercase
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()

            # Remove default ports
            if netloc.endswith(":80") and scheme == "http":
                netloc = netloc[:-3]
            elif netloc.endswith(":443") and scheme == "https":
                netloc = netloc[:-4]

            # Normalize path (remove trailing slash, decode, etc.)
            path = urllib.parse.unquote(parsed.path)
            if path.endswith("/") and len(path) > 1:
                path = path[:-1]

            # Sort query parameters
            query_params = urllib.parse.parse_qs(parsed.query)
            sorted_query = urllib.parse.urlencode(sorted(query_params.items()), doseq=True)

            # Reconstruct normalized URL
            return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))

        except Exception as e:
            self.logger.warning(f"Error normalizing URL {url}: {e}")
            return url

    def _normalize_path(self, path: str) -> str:
        """Normalize file path for consistent cache keys.

        Args:
            path: File path to normalize

        Returns:
            Normalized path
        """
        try:
            # Convert to Path for normalization
            p = Path(path)

            # Resolve relative paths and normalize
            normalized = str(p.resolve()) if p.is_absolute() else str(p)

            # Convert to forward slashes for consistency across platforms
            normalized = normalized.replace("\\", "/")

            # Remove case sensitivity if configured
            if not self.config.case_sensitive:
                normalized = normalized.lower()

            return normalized

        except Exception as e:
            self.logger.warning(f"Error normalizing path {path}: {e}")
            return path

    def _hash_key(self, key_data: str) -> str:
        """Generate hash for key data.

        Args:
            key_data: Data to hash

        Returns:
            Hashed key
        """
        try:
            # Use configured hash algorithm
            if self.config.hash_algorithm == "md5":
                hash_obj = hashlib.md5(usedforsecurity=False)  # Used for cache keys, not security
            elif self.config.hash_algorithm == "sha1":
                hash_obj = hashlib.sha1(usedforsecurity=False)  # Used for cache keys, not security
            else:  # Default to sha256
                hash_obj = hashlib.sha256()

            hash_obj.update(key_data.encode("utf-8"))
            hash_value = hash_obj.hexdigest()

            # Include algorithm prefix for clarity
            prefix = self.config.prefix or self.config.hash_algorithm[:3]
            return f"{prefix}_{hash_value}"

        except Exception as e:
            self.logger.warning(f"Error hashing key data: {e}")
            # Fallback to simple hash
            return f"fallback_{abs(hash(key_data))}"


# Predefined key generators for common use cases
DEFAULT_GENERATOR = CacheKeyGenerator()

HTTP_GENERATOR = CacheKeyGenerator(
    CacheKeyConfig(strategy=KeyStrategy.HASH, normalize_paths=True, max_length=200, prefix="http")
)

FILE_GENERATOR = CacheKeyGenerator(
    CacheKeyConfig(
        strategy=KeyStrategy.VERSIONED, normalize_paths=True, include_version=True, prefix="file"
    )
)

EVENT_GENERATOR = CacheKeyGenerator(
    CacheKeyConfig(
        strategy=KeyStrategy.HIERARCHICAL, max_length=180, include_version=False, prefix="event"
    )
)

LAYOUT_GENERATOR = CacheKeyGenerator(
    CacheKeyConfig(strategy=KeyStrategy.HASH, max_length=150, prefix="layout")
)


# Convenience functions for common key generation patterns
def generate_http_cache_key(
    url: str, params: Optional[dict] = None, headers: Optional[dict] = None
) -> str:
    """Generate cache key for HTTP requests."""
    return HTTP_GENERATOR.generate_url_key(url, params, headers)


def generate_file_cache_key(
    file_path: str | Path, modification_time: Optional[datetime] = None
) -> str:
    """Generate cache key for file-based data."""
    return FILE_GENERATOR.generate_file_key(file_path, modification_time)


def generate_event_cache_key(
    source: str, event_id: Optional[str] = None, filters: Optional[dict] = None
) -> str:
    """Generate cache key for event data."""
    return EVENT_GENERATOR.generate_event_key(source, event_id, filters)


def generate_layout_cache_key(layout_name: str, config: dict, theme: Optional[str] = None) -> str:
    """Generate cache key for layout computation."""
    return LAYOUT_GENERATOR.generate_layout_key(layout_name, config, theme)


def create_custom_generator(
    strategy: KeyStrategy = KeyStrategy.SIMPLE, max_length: int = 250, prefix: str = ""
) -> CacheKeyGenerator:
    """Create custom cache key generator.

    Args:
        strategy: Key generation strategy
        max_length: Maximum key length before hashing
        prefix: Optional key prefix

    Returns:
        Configured cache key generator
    """
    config = CacheKeyConfig(strategy=strategy, max_length=max_length, prefix=prefix)
    return CacheKeyGenerator(config)
