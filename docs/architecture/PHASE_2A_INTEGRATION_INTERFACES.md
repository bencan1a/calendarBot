# Phase 2A: Integration Points and Interfaces

## Overview

This document defines the detailed integration points and interfaces between Phase 2A optimization components (ConnectionManager and RequestPipeline) and the existing CalendarBot WebServer infrastructure, ensuring seamless integration and backward compatibility.

## 1. WebServer Class Integration

### 1.1 Enhanced WebServer Constructor

```python
class WebServer:
    def __init__(
        self,
        settings: Any,
        display_manager: Any,
        cache_manager: Any,
        navigation_state: Optional[Any] = None,
        layout_registry: Optional[LayoutRegistry] = None,
        resource_manager: Optional[ResourceManager] = None,
    ) -> None:
        """Enhanced WebServer initialization with Phase 2A components."""
        
        # Existing initialization (unchanged)
        self.settings = settings
        self.display_manager = display_manager
        self.cache_manager = cache_manager
        self.navigation_state = navigation_state
        self.layout_registry = layout_registry or LayoutRegistry()
        self.resource_manager = resource_manager or ResourceManager(
            self.layout_registry, settings=self.settings
        )
        self.settings_service = SettingsService(settings)
        
        # Phase 2A optimization components
        self.connection_manager: Optional[ConnectionManager] = None
        self.request_pipeline: Optional[RequestPipeline] = None
        self._optimization_enabled = False
        
        # Initialize optimization components if enabled
        self._initialize_optimization_components()
        
        # Existing server configuration (unchanged)
        self.host = settings.web_host
        self.port = settings.web_port
        self.layout = settings.web_layout
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[Thread] = None
        self.running = False
        
        # Enhanced static file cache and asset cache (existing)
        self.static_cache = StaticFileCache()
        self.asset_cache = StaticAssetCache(static_dirs, layouts_dir)
        self.asset_cache.build_cache()
```

### 1.2 Optimization Component Initialization

```python
def _initialize_optimization_components(self) -> None:
    """Initialize Phase 2A optimization components based on configuration."""
    try:
        from ..optimization.connection_manager import ConnectionManager, ConnectionConfig
        from ..optimization.request_pipeline import RequestPipeline, PipelineConfig
        
        # Load optimization configuration
        connection_config = ConnectionConfig.from_environment()
        pipeline_config = PipelineConfig.from_environment()
        
        # Initialize components if enabled
        if connection_config.enable_connection_pooling:
            self.connection_manager = ConnectionManager(connection_config)
            logger.info("ConnectionManager initialized successfully")
            
        if pipeline_config.enable_request_pipeline:
            self.request_pipeline = RequestPipeline(pipeline_config)
            logger.info("RequestPipeline initialized successfully")
            
        self._optimization_enabled = (
            self.connection_manager is not None or 
            self.request_pipeline is not None
        )
        
    except ImportError as e:
        logger.warning(f"Phase 2A optimization components not available: {e}")
        self._optimization_enabled = False
    except Exception as e:
        logger.error(f"Failed to initialize optimization components: {e}")
        self._optimization_enabled = False
```

### 1.3 Enhanced Server Lifecycle Methods

```python
async def start(self) -> None:
    """Enhanced server startup with optimization component initialization."""
    if self.running:
        logger.warning("Web server already running")
        return

    try:
        # Start optimization components first
        if self._optimization_enabled:
            await self._start_optimization_components()
        
        # Existing startup logic (unchanged)
        if self.settings.auto_kill_existing:
            cleanup_success = auto_cleanup_before_start(self.host, self.port, force=True)
            if not cleanup_success:
                logger.warning(f"Port {self.port} may still be in use")

        # Create enhanced request handler
        def handler(*args: Any, **kwargs: Any) -> WebRequestHandler:
            return EnhancedWebRequestHandler(*args, web_server=self, **kwargs)

        self.server = HTTPServer((self.host, self.port), handler)
        self.server.timeout = 1.0
        self.server_thread = Thread(target=self._serve_with_cleanup, daemon=False)
        self.server_thread.start()
        self.running = True
        
        logger.info(f"Web server started on http://{self.host}:{self.port}")
        if self._optimization_enabled:
            logger.info("Phase 2A optimizations active")

    except Exception:
        logger.exception("Failed to start web server")
        raise

async def _start_optimization_components(self) -> None:
    """Start optimization components asynchronously."""
    if self.connection_manager:
        await self.connection_manager.startup()
        logger.debug("ConnectionManager started")
        
    if self.request_pipeline:
        await self.request_pipeline.startup()
        logger.debug("RequestPipeline started")

async def stop(self) -> None:
    """Enhanced server shutdown with optimization component cleanup."""
    if not self.running:
        logger.debug("Web server already stopped")
        return

    logger.info("Starting web server shutdown...")
    self.running = False

    try:
        # Stop optimization components first
        if self._optimization_enabled:
            await self._stop_optimization_components()
        
        # Existing shutdown logic (enhanced for better reliability)
        if self.server:
            logger.debug("Shutting down HTTP server...")
            try:
                self.server.server_close()
                logger.debug("Server socket closed")
            except Exception as e:
                logger.warning(f"Error closing server socket: {e}")

            # Enhanced shutdown with proper async handling
            import threading
            shutdown_complete = threading.Event()
            shutdown_error = None

            def shutdown_server() -> None:
                nonlocal shutdown_error
                try:
                    if self.server:
                        self.server.shutdown()
                    shutdown_complete.set()
                except Exception as e:
                    shutdown_error = e
                    shutdown_complete.set()

            shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
            shutdown_thread.start()

            if shutdown_complete.wait(timeout=10.0):
                if shutdown_error:
                    logger.warning(f"Server shutdown error: {shutdown_error}")
                else:
                    logger.debug("Server shutdown completed")
            else:
                logger.warning("Server shutdown timed out")

        # Clean up server thread
        if self.server_thread and self.server_thread.is_alive():
            logger.debug("Waiting for server thread...")
            self.server_thread.join(timeout=10)
            if self.server_thread.is_alive():
                logger.warning("Server thread did not terminate, marking as daemon")
                self.server_thread.daemon = True

        self.server = None
        logger.info("Web server shutdown completed")

    except Exception:
        logger.exception("Error during web server shutdown")
        # Emergency cleanup
        try:
            if self.server:
                self.server.server_close()
        except Exception:
            pass
        self.server = None
    finally:
        self.running = False

async def _stop_optimization_components(self) -> None:
    """Stop optimization components gracefully."""
    if self.request_pipeline:
        await self.request_pipeline.shutdown()
        logger.debug("RequestPipeline stopped")
        
    if self.connection_manager:
        await self.connection_manager.shutdown()
        logger.debug("ConnectionManager stopped")
```

## 2. WebRequestHandler Integration

### 2.1 Enhanced WebRequestHandler Class

```python
class EnhancedWebRequestHandler(WebRequestHandler):
    """Enhanced WebRequestHandler with Phase 2A optimization integration."""
    
    def __init__(self, *args: Any, web_server: Optional["WebServer"] = None, **kwargs: Any) -> None:
        """Initialize enhanced request handler."""
        super().__init__(*args, web_server=web_server, **kwargs)
        
        # Phase 2A optimization access
        self.connection_manager = web_server.connection_manager if web_server else None
        self.request_pipeline = web_server.request_pipeline if web_server else None
        self._optimization_enabled = (
            self.connection_manager is not None or 
            self.request_pipeline is not None
        )

    def _handle_api_request(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Enhanced API request handling with optimization pipeline."""
        try:
            logger.debug(f"API request: path='{path}', method={self.command}")

            if not self.web_server:
                self._send_json_response(500, {"error": "Web server not available"})
                return

            # Route through optimization pipeline if available
            if self._optimization_enabled and self.request_pipeline:
                self._handle_api_request_optimized(path, params)
            else:
                self._handle_api_request_legacy(path, params)

        except Exception as e:
            logger.exception("Error handling API request")
            self._send_json_response(500, {"error": str(e)})

    def _handle_api_request_optimized(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Handle API request through optimization pipeline."""
        try:
            # Classify request for pipeline processing
            request_type = self._classify_api_request(path)
            request_params = self._normalize_request_params(params)
            
            # Create handler function for legacy compatibility
            def legacy_handler():
                return self._execute_legacy_api_handler(path, request_params)
            
            # Process through pipeline
            if asyncio.iscoroutinefunction(legacy_handler):
                # Async handler
                result = asyncio.run(
                    self.request_pipeline.process_request(
                        request_type=request_type,
                        request_params=request_params,
                        handler_func=legacy_handler
                    )
                )
            else:
                # Sync handler with async pipeline integration
                result = self._run_pipeline_sync(
                    request_type, request_params, legacy_handler
                )
            
            # Send response
            if isinstance(result, dict):
                self._send_json_response(200, result)
            else:
                self._send_json_response(200, {"data": result})
                
        except Exception as e:
            logger.warning(f"Optimization pipeline failed for {path}: {e}")
            # Fallback to legacy handling
            self._handle_api_request_legacy(path, params)

    def _handle_api_request_legacy(
        self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
    ) -> None:
        """Original API request handling (preserved for fallback)."""
        # This is the existing _handle_api_request implementation
        # from the original WebRequestHandler class
        
        if path == "/api/navigate":
            logger.debug("Routing to navigation API")
            self._handle_navigation_api(params)
        elif path == "/api/layout":
            logger.debug("Routing to layout API")
            self._handle_layout_api(params)
        elif path == "/api/theme":
            logger.debug("Routing to theme API (redirect to layout)")
            self._handle_layout_api(params)
        elif path == "/api/refresh":
            logger.debug("Routing to refresh API")
            self._handle_refresh_api(params)
        elif path == "/api/whats-next/data":
            logger.debug("Routing to whats-next data API")
            self._handle_whats_next_data_api(params)
        elif path == "/api/status":
            logger.debug("Routing to status API")
            self._handle_status_api()
        elif path.startswith("/api/settings"):
            logger.debug("Routing to settings API")
            self._handle_settings_api(path, params)
        elif path.startswith("/api/events"):
            logger.debug("Routing events API to settings handler")
            self._handle_settings_api(path, params)
        elif path.startswith("/api/database"):
            logger.debug("Routing to database API")
            self._handle_database_api(path, params)
        else:
            logger.warning(f"No route found for API path: {path}")
            self._send_json_response(404, {"error": "API endpoint not found"})
```

### 2.2 Request Classification and Processing

```python
def _classify_api_request(self, path: str) -> str:
    """Classify API request for pipeline processing."""
    
    # High-value cacheable requests
    if path == "/api/whats-next/data":
        return "whats_next_data"
    elif path == "/api/status":
        return "status_data"
    elif path.startswith("/api/settings") and self.command == "GET":
        return "settings_get"
    elif path.startswith("/api/database/query"):
        return "database_query"
    
    # Batchable requests
    elif path.startswith("/api/events"):
        return "events_api"
    elif path.startswith("/api/database"):
        return "database_api"
    
    # Non-cacheable requests
    elif path == "/api/navigate":
        return "navigation"
    elif path == "/api/layout":
        return "layout_change"
    elif path == "/api/refresh":
        return "data_refresh"
    elif path.startswith("/api/settings") and self.command in ["POST", "PUT"]:
        return "settings_update"
    
    # Default classification
    else:
        return "generic_api"

def _normalize_request_params(
    self, params: Union[dict[str, list[str]], dict[str, Any]]
) -> dict[str, Any]:
    """Normalize request parameters for consistent processing."""
    
    if not params:
        return {}
    
    normalized = {}
    
    for key, value in params.items():
        if isinstance(value, list) and len(value) == 1:
            # Convert single-item lists to scalar values
            normalized[key] = value[0]
        elif isinstance(value, list) and len(value) == 0:
            # Skip empty lists
            continue
        else:
            # Keep as-is for multi-value or non-list parameters
            normalized[key] = value
    
    return normalized

def _run_pipeline_sync(
    self, request_type: str, request_params: dict[str, Any], handler_func: Callable
) -> Any:
    """Run optimization pipeline in sync context."""
    
    try:
        # Try to get running event loop
        loop = asyncio.get_running_loop()
        
        # If in event loop, run in thread pool
        def run_in_new_loop():
            import asyncio
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(
                    self.request_pipeline.process_request(
                        request_type=request_type,
                        request_params=request_params,
                        handler_func=handler_func
                    )
                )
            finally:
                new_loop.close()
        
        # Use existing thread pool utility
        return run_in_thread_pool(run_in_new_loop, timeout=10.0)
        
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        return asyncio.run(
            self.request_pipeline.process_request(
                request_type=request_type,
                request_params=request_params,
                handler_func=handler_func
            )
        )

def _execute_legacy_api_handler(
    self, path: str, params: dict[str, Any]
) -> Any:
    """Execute legacy API handler and return result."""
    
    # Create a response capture mechanism
    response_data = {}
    
    # Override _send_json_response to capture response
    original_send = self._send_json_response
    def capture_response(status_code: int, data: dict[str, Any]) -> None:
        response_data['status_code'] = status_code
        response_data['data'] = data
    
    self._send_json_response = capture_response
    
    try:
        # Execute legacy handler
        self._handle_api_request_legacy(path, params)
        
        # Return captured response data
        return response_data.get('data', {})
        
    finally:
        # Restore original response method
        self._send_json_response = original_send
```

## 3. Database Integration Interface

### 3.1 Enhanced Database Operations

```python
class EnhancedDatabaseOperations:
    """Enhanced database operations with connection pooling."""
    
    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.connection_manager = connection_manager
        self._fallback_available = True
    
    async def execute_query(
        self, query: str, params: tuple = (), fetch_results: bool = True
    ) -> Union[List[Dict[str, Any]], int]:
        """Execute database query with connection pooling."""
        
        if self.connection_manager:
            try:
                return await self.connection_manager.execute_db_query(
                    query, params, fetch_results
                )
            except Exception as e:
                logger.warning(f"Connection pool query failed: {e}")
                if self._fallback_available:
                    return await self._execute_query_fallback(query, params, fetch_results)
                raise
        else:
            return await self._execute_query_fallback(query, params, fetch_results)
    
    async def _execute_query_fallback(
        self, query: str, params: tuple = (), fetch_results: bool = True
    ) -> Union[List[Dict[str, Any]], int]:
        """Fallback to original database query method."""
        
        # This would use the existing database connection pattern
        # from the original WebRequestHandler._execute_safe_query method
        
        if not hasattr(self, '_db_path'):
            # Get database path from cache manager or settings
            from ..cache.manager import CacheManager
            cache_manager = CacheManager()  # This would need proper initialization
            self._db_path = cache_manager.db.database_path
        
        try:
            import sqlite3
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch_results:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    return cursor.rowcount
                    
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {e}")
            raise
```

### 3.2 Database Handler Integration

```python
def _handle_database_api_enhanced(
    self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
) -> None:
    """Enhanced database API with connection pooling."""
    
    try:
        # Initialize enhanced database operations
        db_ops = EnhancedDatabaseOperations(self.connection_manager)
        
        if path == "/api/database/query":
            self._handle_database_query_enhanced(params, db_ops)
        elif path == "/api/database/schema":
            self._handle_database_schema_enhanced(db_ops)
        elif path == "/api/database/tables":
            self._handle_database_tables_enhanced(db_ops)
        elif path == "/api/database/info":
            self._handle_database_info_enhanced(db_ops)
        else:
            self._send_json_response(404, {"error": "Database API endpoint not found"})
            
    except Exception as e:
        logger.exception("Error handling database API request")
        self._send_json_response(500, {"error": str(e)})

async def _handle_database_query_enhanced(
    self, params: dict[str, Any], db_ops: EnhancedDatabaseOperations
) -> None:
    """Handle database query with connection pooling."""
    
    query = params.get("query", "").strip()
    if not query:
        self._send_json_response(400, {"error": "Query parameter required"})
        return
    
    # Security validation (same as original)
    if not self._is_safe_query(query):
        self.security_logger.log_input_validation_failure(
            input_type="sql_query",
            validation_error="Unsafe SQL query attempted",
            details={
                "source_ip": self.client_address[0] if self.client_address else "unknown",
                "query": query[:100],
                "endpoint": "/api/database/query",
            },
        )
        self._send_json_response(403, {
            "error": "Query not allowed",
            "message": "Only SELECT and schema queries are permitted"
        })
        return
    
    try:
        # Execute through enhanced database operations
        results = await db_ops.execute_query(query, fetch_results=True)
        
        self._send_json_response(200, {
            "success": True,
            "data": {
                "rows": results,
                "count": len(results),
                "query": query
            }
        })
        
    except Exception as e:
        logger.exception("Enhanced database query failed")
        self._send_json_response(500, {"error": f"Query execution failed: {e!s}"})
```

## 4. Settings Service Integration

### 4.1 Enhanced Settings Operations

```python
class EnhancedSettingsOperations:
    """Enhanced settings operations with caching integration."""
    
    def __init__(
        self, 
        settings_service: SettingsService,
        request_pipeline: Optional[RequestPipeline] = None
    ):
        self.settings_service = settings_service
        self.request_pipeline = request_pipeline
    
    async def get_settings_cached(self) -> dict[str, Any]:
        """Get settings with caching support."""
        
        if self.request_pipeline:
            try:
                # Use pipeline for caching
                result = await self.request_pipeline.process_request(
                    request_type="settings_get",
                    request_params={},
                    handler_func=self._get_settings_direct
                )
                return result
            except Exception as e:
                logger.warning(f"Settings cache failed: {e}")
                return await self._get_settings_direct()
        else:
            return await self._get_settings_direct()
    
    async def _get_settings_direct(self) -> dict[str, Any]:
        """Direct settings retrieval (no caching)."""
        try:
            settings = self.settings_service.get_settings()
            return {"success": True, "data": settings.to_api_dict()}
        except Exception as e:
            logger.error(f"Settings retrieval failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_settings_with_invalidation(
        self, settings_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update settings and invalidate relevant caches."""
        
        try:
            # Update settings
            from ..settings.models import SettingsData
            settings = SettingsData(**settings_data)
            updated_settings = self.settings_service.update_settings(settings)
            
            # Invalidate caches if pipeline available
            if self.request_pipeline:
                await self.request_pipeline.invalidate_cache("settings_*")
                await self.request_pipeline.invalidate_cache("whats_next_*")
                logger.debug("Settings-related caches invalidated")
            
            return {
                "success": True,
                "message": "Settings updated successfully",
                "data": updated_settings.to_api_dict()
            }
            
        except Exception as e:
            logger.error(f"Settings update failed: {e}")
            return {"success": False, "error": str(e)}
```

### 4.2 Settings Handler Integration

```python
def _handle_settings_api_enhanced(
    self, path: str, params: Union[dict[str, list[str]], dict[str, Any]]
) -> None:
    """Enhanced settings API with caching integration."""
    
    try:
        if not self.web_server or not self.web_server.settings_service:
            self._send_json_response(503, {
                "error": "Settings service not available",
                "message": "Settings functionality is currently unavailable"
            })
            return
        
        # Initialize enhanced settings operations
        settings_ops = EnhancedSettingsOperations(
            self.web_server.settings_service,
            self.request_pipeline
        )
        
        method = self.command
        
        # Enhanced routing with caching support
        if path == "/api/settings" and method == "GET":
            result = asyncio.run(settings_ops.get_settings_cached())
            self._send_json_response(200, result)
            
        elif path == "/api/settings" and method == "PUT":
            if not params:
                self._send_json_response(400, {"error": "Invalid request data"})
                return
            
            result = asyncio.run(
                settings_ops.update_settings_with_invalidation(params)
            )
            status_code = 200 if result.get("success") else 500
            self._send_json_response(status_code, result)
            
        else:
            # Fallback to original settings handler for other endpoints
            super()._handle_settings_api(path, params)
            
    except Exception as e:
        logger.exception("Error handling enhanced settings API")
        self._send_json_response(500, {"error": str(e)})
```

## 5. Static File Serving Integration

### 5.1 Enhanced Static File Handling

```python
def _serve_static_file_enhanced(self, path: str) -> None:
    """Enhanced static file serving with improved caching."""
    
    try:
        # Remove /static/ prefix
        file_path = path[8:]
        
        # Production asset filtering (unchanged)
        if should_exclude_asset(file_path):
            logger.warning(f"ASSET_EXCLUSION: Blocking {file_path}")
            self._send_404()
            return
        
        # Use enhanced static asset cache with connection manager support
        full_path = None
        
        if (
            self.web_server
            and hasattr(self.web_server, "asset_cache")
            and self.web_server.asset_cache.is_cache_built()
        ):
            # Enhanced asset resolution with connection manager metrics
            layout_name = self._extract_layout_from_path(file_path)
            full_path = self.web_server.asset_cache.resolve_asset_path(file_path, layout_name)
            
            # Record cache performance metrics if connection manager available
            if self.connection_manager and hasattr(self.connection_manager, 'record_metric'):
                cache_hit = full_path is not None
                self.connection_manager.record_metric('static_cache_hit', cache_hit)
        
        if not full_path:
            # Fallback to original static file resolution
            full_path = self._resolve_static_file_legacy(file_path)
        
        if full_path and full_path.exists() and full_path.is_file():
            # Enhanced file serving with connection manager
            self._serve_static_file_content(full_path)
        else:
            logger.warning(f"Static file not found: {file_path}")
            self._send_404()
            
    except Exception as e:
        logger.exception(f"Error serving static file {path}")
        self._send_500(str(e))

def _serve_static_file_content(self, file_path: Path) -> None:
    """Serve static file content with enhanced caching."""
    
    try:
        # Generate ETag for caching
        etag = self._generate_etag(file_path)
        
        # Check if client has cached version
        client_etag = self.headers.get('If-None-Match')
        if client_etag and client_etag.strip('"') == etag:
            self.send_response(304)  # Not Modified
            self.send_header("ETag", f'"{etag}"')
            self.end_headers()
            return
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "text/plain"
        
        # Read file content
        with file_path.open("rb") as f:
            content = f.read()
        
        # Send enhanced response with caching headers
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("ETag", f'"{etag}"')
        self.send_header("Cache-Control", "public, max-age=3600, must-revalidate")
        self.end_headers()
        self.wfile.write(content)
        
        # Record metrics if available
        if self.connection_manager and hasattr(self.connection_manager, 'record_metric'):
            self.connection_manager.record_metric('static_file_served', len(content))
            
    except Exception as e:
        logger.error(f"Error serving file content: {e}")
        self._send_500(str(e))
```

## 6. Error Handling and Fallback Integration

### 6.1 Graceful Degradation Strategy

```python
class OptimizationFallbackHandler:
    """Handle graceful degradation when optimization components fail."""
    
    def __init__(self, web_server: "WebServer"):
        self.web_server = web_server
        self.fallback_active = False
        self.failure_count = 0
        self.last_failure_time = None
    
    def handle_optimization_failure(
        self, component: str, error: Exception, context: dict[str, Any]
    ) -> None:
        """Handle optimization component failure."""
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"Optimization component '{component}' failed: {error}. "
            f"Failure count: {self.failure_count}"
        )
        
        # Activate fallback mode if too many failures
        if self.failure_count >= 3 and not self.fallback_active:
            self.activate_fallback_mode()
    
    def activate_fallback_mode(self) -> None:
        """Activate fallback mode, disabling optimizations."""
        
        self.fallback_active = True
        logger.warning("Activating optimization fallback mode")
        
        # Disable optimization components
        if self.web_server.connection_manager:
            try:
                asyncio.run(self.web_server.connection_manager.disable())
            except Exception as e:
                logger.error(f"Error disabling connection manager: {e}")
        
        if self.web_server.request_pipeline:
            try:
                asyncio.run(self.web_server.request_pipeline.disable())
            except Exception as e:
                logger.error(f"Error disabling request pipeline: {e}")
        
        # Update server state
        self.web_server._optimization_enabled = False
        
        logger.info("Fallback mode activated - using legacy request handling")
    
    def check_recovery_possibility(self) -> bool:
        """Check if optimization components can be re-enabled."""
        
        if not self.fallback_active:
            return True
        
        # Allow recovery after 5 minutes of fallback mode
        if self.last_failure_time:
            time_since_failure = datetime.now() - self.last_failure_time
            if time_since_failure.total_seconds() > 300:  # 5 minutes
                return True
        
        return False
    
    async def attempt_recovery(self) -> bool:
        """Attempt to recover optimization components."""
        
        if not self.check_recovery_possibility():
            return False
        
        logger.info("Attempting optimization component recovery...")
        
        try:
            # Re-initialize components
            self.web_server._initialize_optimization_components()
            
            if self.web_server._optimization_enabled:
                await self.web_server._start_optimization_components()
                
                # Reset failure tracking
                self.fallback_active = False
                self.failure_count = 0
                self.last_failure_time = None
                
                logger.info("Optimization component recovery successful")
                return True
            else:
                logger.warning("Optimization component recovery failed")
                return False
                
        except Exception as e:
            logger.error(f"Optimization recovery failed: {e}")
            return False
```

## 7. Configuration Integration Interface

### 7.1 Unified Configuration Management

```python
@dataclass
class Phase2AConfiguration:
    """Unified configuration for Phase 2A optimization components."""
    
    # Feature flags
    enable_connection_pooling: bool = True
    enable_request_pipeline: bool = True
    enable_request_batching: bool = True
    enable_response_caching: bool = True
    
    # Connection pool settings
    http_pool_size: int = 100
    http_connections_per_host: int = 30
    db_pool_size: int = 10
    
    # Request pipeline settings
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000
    batch_size: int = 10
    batch_timeout_ms: int = 50
    
    # Performance settings
    enable_metrics: bool = True
    enable_health_monitoring: bool = True
    fallback_threshold: int = 3
    
    @classmethod
    def from_settings(cls, settings: Any) -> 'Phase2AConfiguration':
        """Create configuration from WebServer settings."""
        
        return cls(
            enable_connection_pooling=getattr(
                settings, 'enable_connection_pooling', 
                os.getenv('ENABLE_CONNECTION_POOLING', 'true').lower() == 'true'
            ),
            enable_request_pipeline=getattr(
                settings, 'enable_request_pipeline',
                os.getenv('ENABLE_REQUEST_PIPELINE', 'true').lower() == 'true'
            ),
            http_pool_size=getattr(
                settings, 'http_pool_size',
                int(os.getenv('HTTP_POOL_SIZE', '100'))
            ),
            cache_ttl_seconds=getattr(
                settings, 'cache_ttl_seconds',
                int(os.getenv('CACHE_TTL_SECONDS', '300'))
            ),
            # ... other configuration mappings
        )
```

## 8. Monitoring Integration Interface

### 8.1 Performance Metrics Integration

```python
class Phase2AMetricsCollector:
    """Collect and report Phase 2A optimization metrics."""
    
    def __init__(self, web_server: "WebServer"):
        self.web_server = web_server
        self.metrics = {
            'connection_pool': {},
            'request_pipeline': {},
            'optimization_status': {}
        }
    
    def collect_all_metrics(self) -> dict[str, Any]:
        """Collect comprehensive optimization metrics."""
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'optimization_enabled': self.web_server._optimization_enabled,
        }
        
        # Connection manager metrics
        if self.web_server.connection_manager:
            metrics['connection_manager'] = (
                self.web_server.connection_manager.get_metrics()
            )
        
        # Request pipeline metrics
        if self.web_server.request_pipeline:
            metrics['request_pipeline'] = (
                self.web_server.request_pipeline.get_metrics()
            )
        
        # Server metrics
        metrics['server_status'] = {
            'running': self.web_server.running,
            'host': self.web_server.host,
            'port': self.web_server.port,
            'current_layout': self.web_server.get_current_layout(),
        }
        
        return metrics
    
    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance improvement summary."""
        
        summary = {
            'phase_2a_active': self.web_server._optimization_enabled,
            'components': {
                'connection_manager': self.web_server.connection_manager is not None,
                'request_pipeline': self.web_server.request_pipeline is not None,
            }
        }
        
        # Add component-specific summaries
        if self.web_server.connection_manager:
            cm_stats = self.web_server.connection_manager.get_stats()
            summary['connection_pool_stats'] = cm_stats
        
        if self.web_server.request_pipeline:
            rp_stats = self.web_server.request_pipeline.get_stats()
            summary['request_pipeline_stats'] = rp_stats
        
        return summary
```

## 9. Testing Integration Interface

### 9.1 Test Compatibility Layer

```python
class Phase2ATestCompatibility:
    """Ensure Phase 2A components are compatible with existing tests."""
    
    @staticmethod
    def create_test_web_server(**kwargs) -> "WebServer":
        """Create WebServer instance for testing with optimization disabled."""
        
        # Disable optimizations for testing by default
        test_settings = type('TestSettings', (), {
            'web_host': 'localhost',
            'web_port': 0,  # Use random port for testing
            'web_layout': '4x8',
            'auto_kill_existing': False,
            'enable_connection_pooling': kwargs.get('enable_optimizations', False),
            'enable_request_pipeline': kwargs.get('enable_optimizations', False),
        })()
        
        # Create mock dependencies
        display_manager = kwargs.get('display_manager', MockDisplayManager())
        cache_manager = kwargs.get('cache_manager', MockCacheManager())
        
        return WebServer(
            settings=test_settings,
            display_manager=display_manager,
            cache_manager=cache_manager
        )
    
    @staticmethod
    def create_optimized_test_server(**kwargs) -> "WebServer":
        """Create WebServer with optimizations enabled for integration testing."""
        
        return Phase2ATestCompatibility.create_test_web_server(
            enable_optimizations=True,
            **kwargs
        )
```

## Summary

This integration specification provides:

1. **Seamless Integration**: Phase 2A components integrate without breaking existing functionality
2. **Backward Compatibility**: All existing APIs and behaviors are preserved
3. **Graceful Degradation**: System falls back to legacy behavior on optimization failures
4. **Configuration Flexibility**: Optimizations can be enabled/disabled via environment variables and settings
5. **Test Compatibility**: Existing tests continue to work with optimizations disabled by default
6. **Monitoring Integration**: Comprehensive metrics collection for performance validation
7. **Error Handling**: Robust error handling with automatic fallback mechanisms

The integration maintains the existing WebServer architecture while adding Phase 2A optimizations as an enhancement layer, ensuring zero breaking changes to current functionality.