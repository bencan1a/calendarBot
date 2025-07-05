"""Validation runner for coordinating component testing in test mode."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from config.settings import settings
from .results import ValidationResults, ValidationStatus
from .logging_setup import get_validation_logger, log_validation_start, log_validation_result


class ValidationRunner:
    """Coordinates validation testing of Calendar Bot components."""
    
    def __init__(self, 
                 test_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None,
                 components: Optional[List[str]] = None,
                 use_cache: bool = True,
                 output_format: str = "console"):
        """Initialize validation runner.
        
        Args:
            test_date: Date to test (default: today)
            end_date: End date for range testing (default: same as test_date)
            components: List of components to test (default: all)
            use_cache: Whether to use cached data when available
            output_format: Output format ('console' or 'json')
        """
        self.test_date = test_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_date = end_date or self.test_date
        self.components = components or ['auth', 'api', 'cache', 'display']
        self.use_cache = use_cache
        self.output_format = output_format
        self.settings = settings
        
        # Initialize results tracking
        self.results = ValidationResults()
        
        # Get logger
        self.logger = get_validation_logger('validation')
        
        # Component instances (to be initialized during run)
        self.auth_manager = None
        self.graph_client = None
        self.cache_manager = None
        self.display_manager = None
        
        self.logger.info(f"ValidationRunner initialized for {self.test_date.date()}")
        if self.end_date != self.test_date:
            self.logger.info(f"Date range: {self.test_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Components to test: {', '.join(self.components)}")
    
    async def run_validation(self) -> ValidationResults:
        """Run complete validation suite.
        
        Returns:
            ValidationResults with all test outcomes
        """
        try:
            self.logger.info("Starting Calendar Bot validation")
            
            # Initialize components
            await self._initialize_components()
            
            # Run validations for each requested component
            if 'auth' in self.components:
                await self._validate_authentication()
            
            if 'api' in self.components:
                await self._validate_api_connectivity()
            
            if 'cache' in self.components:
                await self._validate_cache_operations()
            
            if 'display' in self.components:
                await self._validate_display_functionality()
            
            # Finalize results
            self.results.finalize()
            self.logger.info("Validation completed")
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"Validation runner error: {e}")
            self.results.add_failure('system', 'validation_runner', f"Runner error: {str(e)}")
            self.results.finalize()
            return self.results
        finally:
            await self._cleanup_components()
    
    async def _initialize_components(self) -> None:
        """Initialize Calendar Bot components for testing."""
        try:
            log_validation_start(self.logger, "component_initialization")
            start_time = time.time()
            
            # Import components
            from calendarbot.auth import AuthManager
            from calendarbot.api import GraphClient
            from calendarbot.cache import CacheManager
            from calendarbot.display import DisplayManager
            
            # Initialize components
            self.auth_manager = AuthManager(self.settings)
            self.cache_manager = CacheManager(self.settings)
            self.display_manager = DisplayManager(self.settings)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.results.add_success(
                'system', 
                'component_initialization', 
                'Components initialized successfully',
                {'auth': bool(self.auth_manager), 'cache': bool(self.cache_manager), 'display': bool(self.display_manager)},
                duration_ms
            )
            
            log_validation_result(self.logger, "component_initialization", True, 
                                "Components initialized", duration_ms)
            
        except Exception as e:
            self.results.add_failure('system', 'component_initialization', f"Failed to initialize components: {str(e)}")
            log_validation_result(self.logger, "component_initialization", False, str(e))
            raise
    
    async def _cleanup_components(self) -> None:
        """Clean up component resources."""
        try:
            if self.cache_manager:
                await self.cache_manager.cleanup_old_events()
            self.logger.debug("Component cleanup completed")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def _validate_authentication(self) -> None:
        """Validate authentication functionality."""
        self.logger.info("Validating authentication component")
        
        # Test token store accessibility
        await self._test_token_store()
        
        # Test authentication state
        await self._test_auth_state()
        
        # Test token validation (if authenticated)
        if self.auth_manager.is_authenticated():
            await self._test_token_validation()
    
    async def _test_token_store(self) -> None:
        """Test token storage functionality."""
        test_name = "token_store_access"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            # Test token store file accessibility
            token_file_exists = self.auth_manager.token_store.token_file.exists()
            has_tokens = self.auth_manager.token_store.has_tokens()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.results.add_success(
                'auth',
                test_name,
                'Token store accessible',
                {
                    'token_file_exists': token_file_exists,
                    'has_stored_tokens': has_tokens,
                    'token_file_path': str(self.auth_manager.token_store.token_file)
                },
                duration_ms
            )
            
            log_validation_result(self.logger, test_name, True, 
                                f"Token store OK (exists: {token_file_exists}, has_tokens: {has_tokens})", 
                                duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('auth', test_name, f"Token store error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_auth_state(self) -> None:
        """Test current authentication state."""
        test_name = "auth_state_check"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            is_authenticated = self.auth_manager.is_authenticated()
            token_info = self.auth_manager.get_token_info()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if is_authenticated:
                self.results.add_success(
                    'auth',
                    test_name,
                    'Authentication state valid',
                    {
                        'authenticated': is_authenticated,
                        'token_info': token_info or {}
                    },
                    duration_ms
                )
                log_validation_result(self.logger, test_name, True, "Authenticated", duration_ms)
            else:
                self.results.add_warning(
                    'auth',
                    test_name,
                    'Not currently authenticated',
                    {'authenticated': is_authenticated},
                    duration_ms
                )
                log_validation_result(self.logger, test_name, True, "Not authenticated (expected in some scenarios)", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('auth', test_name, f"Auth state check error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_token_validation(self) -> None:
        """Test token validation if authenticated."""
        test_name = "token_validation"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            access_token = await self.auth_manager.get_valid_access_token()
            duration_ms = int((time.time() - start_time) * 1000)
            
            if access_token:
                self.results.add_success(
                    'auth',
                    test_name,
                    'Valid access token retrieved',
                    {
                        'has_access_token': True,
                        'token_length': len(access_token)
                    },
                    duration_ms
                )
                log_validation_result(self.logger, test_name, True, "Valid access token", duration_ms)
            else:
                self.results.add_failure(
                    'auth',
                    test_name,
                    'Failed to retrieve valid access token',
                    duration_ms=duration_ms
                )
                log_validation_result(self.logger, test_name, False, "No valid access token", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('auth', test_name, f"Token validation error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _validate_api_connectivity(self) -> None:
        """Validate API connectivity functionality."""
        self.logger.info("Validating API connectivity")
        
        # Test Graph API client initialization
        await self._test_graph_client_init()
        
        # Test API connectivity (if authenticated)
        if self.auth_manager and self.auth_manager.is_authenticated():
            await self._test_api_connection()
            await self._test_api_calendar_access()
        else:
            self.results.add_skipped('api', 'connection_test', 'Skipped - not authenticated')
            self.results.add_skipped('api', 'calendar_access', 'Skipped - not authenticated')
    
    async def _test_graph_client_init(self) -> None:
        """Test Graph API client initialization."""
        test_name = "graph_client_init"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            from calendarbot.api import GraphClient
            
            # Test client creation
            async with GraphClient(self.auth_manager, self.settings) as client:
                self.graph_client = client
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                self.results.add_success(
                    'api',
                    test_name,
                    'Graph client initialized successfully',
                    {
                        'client_initialized': True,
                        'base_url': 'https://graph.microsoft.com/v1.0'
                    },
                    duration_ms
                )
                
                log_validation_result(self.logger, test_name, True, "Graph client initialized", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('api', test_name, f"Graph client init error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_api_connection(self) -> None:
        """Test API connection."""
        test_name = "api_connection"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            from calendarbot.api import GraphClient
            
            async with GraphClient(self.auth_manager, self.settings) as client:
                connection_ok = await client.test_connection()
                duration_ms = int((time.time() - start_time) * 1000)
                
                if connection_ok:
                    self.results.add_success(
                        'api',
                        test_name,
                        'API connection successful',
                        {'connection_test': True},
                        duration_ms
                    )
                    log_validation_result(self.logger, test_name, True, "API connection OK", duration_ms)
                else:
                    self.results.add_failure(
                        'api',
                        test_name,
                        'API connection test failed',
                        duration_ms=duration_ms
                    )
                    log_validation_result(self.logger, test_name, False, "Connection test failed", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('api', test_name, f"API connection error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_api_calendar_access(self) -> None:
        """Test calendar data access."""
        test_name = "calendar_access"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            from calendarbot.api import GraphClient
            
            async with GraphClient(self.auth_manager, self.settings) as client:
                # Try to fetch events for test date (full day range)
                end_date = self.test_date + timedelta(days=1)
                events = await client.get_calendar_events(self.test_date, end_date)
                duration_ms = int((time.time() - start_time) * 1000)
                
                self.results.add_success(
                    'api',
                    test_name,
                    f'Calendar access successful - {len(events)} events retrieved',
                    {
                        'events_count': len(events),
                        'test_date': self.test_date.date().isoformat()
                    },
                    duration_ms
                )
                
                log_validation_result(self.logger, test_name, True, f"{len(events)} events retrieved", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('api', test_name, f"Calendar access error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _validate_cache_operations(self) -> None:
        """Validate cache functionality."""
        self.logger.info("Validating cache operations")
        
        # Test cache initialization
        await self._test_cache_init()
        
        # Test cache operations
        await self._test_cache_operations()
        
        # Test cache status
        await self._test_cache_status()
    
    async def _test_cache_init(self) -> None:
        """Test cache initialization."""
        test_name = "cache_initialization"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            init_success = await self.cache_manager.initialize()
            duration_ms = int((time.time() - start_time) * 1000)
            
            if init_success:
                self.results.add_success(
                    'cache',
                    test_name,
                    'Cache initialized successfully',
                    {
                        'initialized': init_success,
                        'database_path': str(self.settings.database_file)
                    },
                    duration_ms
                )
                log_validation_result(self.logger, test_name, True, "Cache initialized", duration_ms)
            else:
                self.results.add_failure(
                    'cache',
                    test_name,
                    'Cache initialization failed',
                    duration_ms=duration_ms
                )
                log_validation_result(self.logger, test_name, False, "Cache init failed", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('cache', test_name, f"Cache init error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_cache_operations(self) -> None:
        """Test basic cache operations."""
        test_name = "cache_operations"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            # Test getting cached events
            cached_events = await self.cache_manager.get_todays_cached_events()
            
            # Test cache summary
            cache_summary = await self.cache_manager.get_cache_summary()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.results.add_success(
                'cache',
                test_name,
                f'Cache operations successful - {len(cached_events)} cached events',
                {
                    'cached_events_count': len(cached_events),
                    'cache_summary': cache_summary
                },
                duration_ms
            )
            
            log_validation_result(self.logger, test_name, True, f"{len(cached_events)} cached events", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('cache', test_name, f"Cache operations error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_cache_status(self) -> None:
        """Test cache status reporting."""
        test_name = "cache_status"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            cache_status = await self.cache_manager.get_cache_status()
            is_fresh = await self.cache_manager.is_cache_fresh()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.results.add_success(
                'cache',
                test_name,
                f'Cache status check successful - fresh: {is_fresh}',
                {
                    'is_fresh': is_fresh,
                    'cache_status': cache_status.__dict__ if hasattr(cache_status, '__dict__') else str(cache_status)
                },
                duration_ms
            )
            
            log_validation_result(self.logger, test_name, True, f"Cache fresh: {is_fresh}", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('cache', test_name, f"Cache status error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _validate_display_functionality(self) -> None:
        """Validate display functionality."""
        self.logger.info("Validating display functionality")
        
        # Test display initialization
        await self._test_display_init()
        
        # Test display rendering (with mock data)
        await self._test_display_rendering()
    
    async def _test_display_init(self) -> None:
        """Test display manager initialization."""
        test_name = "display_initialization"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            # Test display manager properties
            display_type = self.display_manager.settings.display_type
            display_enabled = self.display_manager.settings.display_enabled
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.results.add_success(
                'display',
                test_name,
                'Display manager initialized',
                {
                    'display_type': display_type,
                    'display_enabled': display_enabled
                },
                duration_ms
            )
            
            log_validation_result(self.logger, test_name, True, f"Display type: {display_type}", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('display', test_name, f"Display init error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    async def _test_display_rendering(self) -> None:
        """Test display rendering with mock data."""
        test_name = "display_rendering"
        log_validation_start(self.logger, test_name)
        start_time = time.time()
        
        try:
            # Create mock status info
            status_info = {
                'last_update': datetime.now(),
                'is_cached': False,
                'connection_status': 'Online',
                'total_events': 0,
                'consecutive_failures': 0
            }
            
            # Test display with empty events (validation mode)
            display_success = await self.display_manager.display_events([], status_info)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if display_success:
                self.results.add_success(
                    'display',
                    test_name,
                    'Display rendering successful',
                    {
                        'render_success': display_success,
                        'status_info': status_info
                    },
                    duration_ms
                )
                log_validation_result(self.logger, test_name, True, "Display rendering OK", duration_ms)
            else:
                self.results.add_failure(
                    'display',
                    test_name,
                    'Display rendering failed',
                    duration_ms=duration_ms
                )
                log_validation_result(self.logger, test_name, False, "Display rendering failed", duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure('display', test_name, f"Display rendering error: {str(e)}", duration_ms=duration_ms)
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)
    
    def get_results(self) -> ValidationResults:
        """Get validation results.
        
        Returns:
            ValidationResults instance
        """
        return self.results
    
    def print_results(self, verbose: bool = False) -> None:
        """Print validation results in requested format.
        
        Args:
            verbose: Whether to show verbose output
        """
        if self.output_format == "json":
            self.results.print_json_report()
        else:
            self.results.print_console_report(verbose)