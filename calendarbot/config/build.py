"""
CalendarBot Production Build Configuration

Handles debug asset exclusion and production optimizations for static file serving.
Provides environment-based configuration to exclude debug JavaScript assets in production
while preserving them for development workflow.

Key Features:
- Environment-based asset exclusion (CALENDARBOT_ENV)
- Pattern-based filtering for debug assets
- Integration with StaticFileCache
- 45MB JavaScript heap reduction target
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional, Union

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv

    # Load from .env file in project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logging.getLogger(__name__).debug(f"Loaded environment variables from {env_file}")
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass
except Exception as e:
    # Log error but don't fail module loading
    logging.getLogger(__name__).warning(f"Failed to load .env file: {e}")

logger = logging.getLogger(__name__)

# Production exclusion patterns for debug assets
# These patterns target debug-heavy JavaScript files that should not be served in production
PRODUCTION_EXCLUDES = [
    # Debug JavaScript patterns
    r"debug-.*\.js$",
    r"development-.*\.js$",
    r"test-.*\.js$",
    r"mock-.*\.js$",
    # Specific debug-heavy files identified during optimization analysis
    # These files contain extensive console.log statements and debug infrastructure
    r"settings-panel\.js$",  # 1287 lines, 38+ console.log statements
    r"settings-api\.js$",  # 525 lines, console.error/warn for API debugging
    r"gesture-handler\.js$",  # 549 lines, console.log/warn/error for gestures
    # Additional debug patterns
    r".*\.debug\.js$",
    r".*\.dev\.js$",
    r".*-debug\.js$",
    r".*-dev\.js$",
    r"console-.*\.js$",
    r"debugger-.*\.js$",
]

# Source maps and other development artifacts
DEVELOPMENT_ARTIFACTS = [
    r".*\.map$",
    r".*\.map\.js$",
    r".*-sourcemap\.js$",
]

# Test and mock files
TEST_PATTERNS = [
    r".*\.test\.js$",
    r".*\.spec\.js$",
    r".*\.mock\.js$",
    r"__tests__/.*\.js$",
    r"tests?/.*\.js$",
]


def is_production_mode() -> bool:
    """
    Determine if application is running in production mode.

    Checks CALENDARBOT_ENV environment variable:
    - 'production' or 'prod' → production mode
    - 'development', 'dev', or 'debug' → development mode
    - Default to production mode for safety

    Returns:
        bool: True if in production mode, False for development
    """
    # Check explicit environment setting
    env = os.getenv("CALENDARBOT_ENV", "").lower()
    if env in ("production", "prod"):
        return True
    if env in ("development", "dev", "debug"):  # noqa: SIM103
        return False

    # Default to production mode for security and performance
    # In production, debug assets should be excluded by default
    return True


def is_debug_asset(file_path: Union[str, Path]) -> bool:
    """
    Check if a file path matches debug asset patterns.

    Args:
        file_path: Path to the static asset file

    Returns:
        bool: True if file matches debug patterns and should be excluded in production
    """
    if isinstance(file_path, Path):
        file_path = str(file_path)

    # Extract filename for pattern matching
    filename = Path(file_path).name

    # Check against all exclusion patterns
    all_patterns = PRODUCTION_EXCLUDES + DEVELOPMENT_ARTIFACTS + TEST_PATTERNS

    for pattern in all_patterns:
        try:
            if re.search(pattern, filename, re.IGNORECASE):
                logger.debug(f"Debug asset detected: {filename} matches pattern {pattern}")
                return True
        except re.error as e:  # noqa: PERF203
            logger.warning(f"Invalid regex pattern {pattern}: {e}")
            continue

    return False


def should_exclude_asset(file_path: Union[str, Path]) -> bool:
    """
    Determine if an asset should be excluded from serving.

    Combines production mode detection with debug asset identification.

    Args:
        file_path: Path to the static asset file

    Returns:
        bool: True if asset should be excluded from serving
    """
    # Always serve assets in development mode
    if not is_production_mode():
        return False

    # In production mode, exclude debug assets
    return is_debug_asset(file_path)


def get_excluded_patterns() -> list[str]:
    """
    Get list of exclusion patterns for the current environment.

    Returns:
        List[str]: Regex patterns for assets to exclude
    """
    if not is_production_mode():
        return []

    return PRODUCTION_EXCLUDES + DEVELOPMENT_ARTIFACTS + TEST_PATTERNS


def filter_asset_paths(asset_paths: list[Union[str, Path]]) -> list[Union[str, Path]]:
    """
    Filter a list of asset paths, excluding debug assets in production.

    Args:
        asset_paths: List of asset file paths

    Returns:
        List: Filtered asset paths with debug assets removed in production
    """
    if not is_production_mode():
        return asset_paths

    filtered_paths = []
    excluded_count = 0

    for asset_path in asset_paths:
        if should_exclude_asset(asset_path):
            excluded_count += 1
            logger.debug(f"Excluding debug asset: {asset_path}")
        else:
            filtered_paths.append(asset_path)

    if excluded_count > 0:
        logger.info(f"Production mode: excluded {excluded_count} debug assets")

    return filtered_paths


def get_asset_exclusion_info() -> dict:
    """
    Get detailed information about asset exclusion configuration.

    Returns:
        dict: Configuration details including mode, patterns, and metrics
    """
    production_mode = is_production_mode()

    return {
        "production_mode": production_mode,
        "environment": {
            "CALENDARBOT_ENV": os.getenv("CALENDARBOT_ENV"),
        },
        "exclusion_patterns": {
            "production_excludes": len(PRODUCTION_EXCLUDES),
            "development_artifacts": len(DEVELOPMENT_ARTIFACTS),
            "test_patterns": len(TEST_PATTERNS),
            "total_patterns": len(get_excluded_patterns()),
        },
        "target_files": [
            "settings-panel.js (1287 lines)",
            "settings-api.js (525 lines)",
            "gesture-handler.js (549 lines)",
        ],
        "estimated_savings": {
            "javascript_heap_mb": 45,
            "transfer_size_kb": 120,
            "total_lines_excluded": 2361,
        },
    }


def validate_asset_path(file_path: Union[str, Path]) -> bool:
    """
    Validate that an asset path is safe and should be processed.

    Args:
        file_path: Path to validate

    Returns:
        bool: True if path is valid and safe to process
    """
    if not file_path:
        return False

    try:
        # Convert to Path object for validation
        path_obj = Path(file_path)
        path_str = str(file_path)

        # Check for path traversal attempts
        if ".." in str(path_obj):
            logger.warning(f"Path traversal detected in asset path: {file_path}")
            return False

        # Ensure path is relative and safe (check both Unix and Windows patterns)
        if path_obj.is_absolute() or (len(path_str) >= 3 and path_str[1:3] == ":\\"):
            logger.warning(f"Absolute path not allowed for assets: {file_path}")
            return False

        return True

    except (ValueError, OSError) as e:
        logger.warning(f"Invalid asset path {file_path}: {e}")
        return False


class ProductionAssetFilter:
    """
    Production asset filter for static file serving integration.

    Provides a reusable filter class for integration with StaticFileCache
    and other static file serving components.
    """

    def __init__(self):
        self.production_mode = is_production_mode()
        self.exclusion_patterns = get_excluded_patterns()
        self._excluded_cache: set[str] = set()

        logger.info(f"ProductionAssetFilter initialized - Production mode: {self.production_mode}")
        if self.production_mode:
            logger.info(f"Asset exclusion active with {len(self.exclusion_patterns)} patterns")

    def should_serve_asset(self, file_path: Union[str, Path]) -> bool:
        """
        Determine if an asset should be served to clients.

        Args:
            file_path: Path to the asset file

        Returns:
            bool: True if asset should be served, False if excluded
        """
        if not validate_asset_path(file_path):
            return False

        # Always serve assets in development mode
        if not self.production_mode:
            return True

        # Cache exclusion results for performance
        path_str = str(file_path)
        if path_str in self._excluded_cache:
            return False

        # In production mode, exclude debug assets
        excluded = is_debug_asset(file_path)
        if excluded:
            self._excluded_cache.add(path_str)

        return not excluded

    def get_serving_decision(self, file_path: Union[str, Path]) -> dict:
        """
        Get detailed information about serving decision for an asset.

        Args:
            file_path: Path to the asset file

        Returns:
            dict: Decision details including reasoning
        """
        should_serve = self.should_serve_asset(file_path)
        is_debug = is_debug_asset(file_path)

        return {
            "file_path": str(file_path),
            "should_serve": should_serve,
            "is_debug_asset": is_debug,
            "production_mode": self.production_mode,
            "excluded_reason": None
            if should_serve
            else ("debug_asset_in_production" if is_debug else "invalid_path"),
        }

    def clear_cache(self) -> None:
        """Clear the exclusion cache."""
        self._excluded_cache.clear()
        logger.debug("ProductionAssetFilter cache cleared")


# Global filter instance for convenient access
_global_filter: Optional[ProductionAssetFilter] = None


def get_production_filter() -> ProductionAssetFilter:
    """
    Get the global production asset filter instance.

    Returns:
        ProductionAssetFilter: Singleton filter instance
    """
    global _global_filter  # noqa: PLW0603
    if _global_filter is None:
        _global_filter = ProductionAssetFilter()
    return _global_filter
