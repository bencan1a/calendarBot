# Async Resource Management Patterns

**Document Version:** 1.0  
**Last Updated:** January 7, 2025  
**Target Audience:** Developers, System Architects, Performance Engineers

## Executive Summary

This document details the sophisticated asynchronous resource management patterns implemented throughout CalendarBot. The system uses advanced async/await patterns, event loop management, thread pool coordination, and context managers to ensure efficient resource utilization and prevent common async pitfalls.

## 1. Event Loop Management Patterns

### Primary Event Loop Detection

The system implements robust event loop detection to handle sync/async boundary crossing:

```python
def get_calendar_html(self, date_str: str) -> str:
    """Safe event loop detection and isolation pattern."""
    try:
        # Detect existing event loop
        loop = asyncio.get_running_loop()
        
        # Execute in isolated thread to avoid conflicts
        return self._execute_in_thread_pool(async_operation)
        
    except RuntimeError:
        # No running event loop - safe to use asyncio.run()
        return asyncio.run(async_operation())
```

### Event Loop Isolation Pattern

When running async code from sync contexts, the system creates isolated event loops:

```python
def run_async_in_thread() -> Any:
    """Isolated event loop execution pattern."""
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    
    try:
        return new_loop.run_until_complete(async_operation())
    finally:
        # Critical: Always clean up event loop
        new_loop.close()
        asyncio.set_event_loop(None)
```

## 2. Thread Pool Resource Management

### Context-Managed Thread Pools

All thread pool execution uses context managers for guaranteed cleanup:

```python
class WebServer:
    def execute_async_safely(self, async_func: Callable) -> Any:
        """Resource-managed async execution with timeout protection."""
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._run_in_isolated_loop, async_func)
            
            try:
                return future.result(timeout=5.0)
            except concurrent.futures.TimeoutError:
                logger.error("Async operation timed out")
                return None
            except Exception as e:
                logger.error(f"Async operation failed: {e}")
                return None
        # ThreadPoolExecutor automatically cleaned up via context manager
```

### Thread Pool Sizing Strategy

The system uses conservative thread pool sizing to prevent resource exhaustion:

```python
# Configuration in WebServer
MAX_WORKER_THREADS = min(32, (os.cpu_count() or 1) + 4)

# Usage pattern
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    # Single worker for sequential async execution
    # Prevents resource contention in HTTP handlers
    future = executor.submit(async_operation)
    result = future.result(timeout=timeout)
```

## 3. Database Connection Management

### Async Database Context Management

All database operations use async context managers for proper resource cleanup:

```python
class CacheManager:
    async def store_events(self, events: List[CachedEvent]) -> bool:
        """Async database resource management pattern."""
        
        async with aiosqlite.connect(str(self.database_path)) as db:
            # Connection automatically managed
            await db.execute("PRAGMA journal_mode=WAL")
            
            async with db.execute("BEGIN IMMEDIATE") as cursor:
                # Transaction automatically managed
                for event in events:
                    await cursor.execute(INSERT_QUERY, event.to_tuple())
                
                await db.commit()
                return True
        # Connection and transaction automatically closed
```

### Connection Pool Management

The system implements connection pooling for high-concurrency scenarios:

```python
class DatabaseConnectionPool:
    def __init__(self, database_path: Path, max_connections: int = 5):
        self._database_path = database_path
        self._connection_pool: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self._total_connections = 0
        self._max_connections = max_connections
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get connection from pool or create new one."""
        try:
            # Try to get existing connection (non-blocking)
            connection = self._connection_pool.get_nowait()
            return connection
        except asyncio.QueueEmpty:
            if self._total_connections < self._max_connections:
                # Create new connection
                connection = await aiosqlite.connect(str(self._database_path))
                self._total_connections += 1
                return connection
            else:
                # Wait for available connection
                return await self._connection_pool.get()
    
    async def return_connection(self, connection: aiosqlite.Connection) -> None:
        """Return connection to pool."""
        try:
            self._connection_pool.put_nowait(connection)
        except asyncio.QueueFull:
            # Pool full, close excess connection
            await connection.close()
            self._total_connections -= 1
```

## 4. HTTP Client Resource Management

### Async HTTP Session Management

HTTP clients use persistent sessions with proper lifecycle management:

```python
class ICSFetcher:
    def __init__(self):
        self._session: Optional[httpx.AsyncClient] = None
        self._session_lock = asyncio.Lock()
    
    async def get_session(self) -> httpx.AsyncClient:
        """Lazy session initialization with thread safety."""
        if self._session is None:
            async with self._session_lock:
                if self._session is None:  # Double-check pattern
                    self._session = httpx.AsyncClient(
                        timeout=httpx.Timeout(30.0),
                        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
                    )
        return self._session
    
    async def close(self) -> None:
        """Cleanup HTTP session resources."""
        if self._session:
            await self._session.aclose()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### Request Timeout and Resource Protection

All HTTP operations include comprehensive timeout and resource protection:

```python
async def fetch_ics(self, source: ICSSource) -> ICSResponse:
    """Resource-protected HTTP fetching with comprehensive timeouts."""
    
    session = await self.get_session()
    
    try:
        async with asyncio.timeout(source.timeout_seconds):
            response = await session.get(
                source.url,
                auth=source.auth,
                timeout=httpx.Timeout(
                    connect=5.0,      # Connection timeout
                    read=20.0,        # Read timeout
                    write=5.0,        # Write timeout
                    pool=1.0          # Pool acquisition timeout
                )
            )
            
            # Limit response size to prevent memory exhaustion
            if response.headers.get('content-length'):
                content_length = int(response.headers['content-length'])
                if content_length > 10 * 1024 * 1024:  # 10MB limit
                    raise ResourceError("Response too large")
            
            content = await response.aread()
            return ICSResponse(success=True, content=content)
            
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching from {source.url}")
        return ICSResponse(success=False, error_message="Request timeout")
    
    except Exception as e:
        logger.error(f"Error fetching from {source.url}: {e}")
        return ICSResponse(success=False, error_message=str(e))
```

## 5. Memory Management Patterns

### Async Generator Patterns for Large Datasets

The system uses async generators to process large datasets without memory exhaustion:

```python
class EventProcessor:
    async def process_events_streaming(self, source: ICSSource) -> AsyncGenerator[CachedEvent, None]:
        """Memory-efficient event processing using async generators."""
        
        async with self.get_ics_stream(source) as stream:
            parser = ICSParser()
            
            async for ics_chunk in stream:
                events = await parser.parse_chunk(ics_chunk)
                
                for event in events:
                    # Yield one event at a time to control memory usage
                    yield event
                
                # Optional: Yield control to event loop periodically
                await asyncio.sleep(0)  # Allow other coroutines to run
```

### Memory-Bounded Async Queues

For producer-consumer patterns, the system uses bounded queues to prevent memory overflow:

```python
class EventCache:
    def __init__(self, max_queue_size: int = 1000):
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._processing_active = True
    
    async def producer(self, sources: List[ICSSource]) -> None:
        """Producer coroutine with back-pressure handling."""
        for source in sources:
            async for event in self.fetch_events_streaming(source):
                try:
                    # This will block if queue is full (back-pressure)
                    await self._event_queue.put(event)
                except asyncio.CancelledError:
                    logger.info("Producer cancelled")
                    break
    
    async def consumer(self) -> None:
        """Consumer coroutine with resource management."""
        batch = []
        batch_size = 100
        
        while self._processing_active:
            try:
                # Wait for events with timeout to enable periodic flushing
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=5.0
                )
                
                batch.append(event)
                
                if len(batch) >= batch_size:
                    await self._flush_batch(batch)
                    batch.clear()
                
            except asyncio.TimeoutError:
                # Flush partial batch on timeout
                if batch:
                    await self._flush_batch(batch)
                    batch.clear()
```

## 6. Resource Cleanup Patterns

### Async Context Manager Implementation

All major components implement async context managers for guaranteed cleanup:

```python
class SourceManager:
    async def __aenter__(self):
        """Initialize async resources."""
        await self._initialize_sources()
        await self._start_health_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async resources."""
        await self._stop_health_monitoring()
        await self._cleanup_sources()
        
        # Cancel any pending tasks
        pending_tasks = [task for task in asyncio.all_tasks() 
                        if task.get_name().startswith('source_')]
        
        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            
            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not cancel within timeout")
```

### Signal-Based Cleanup

The system registers signal handlers for graceful shutdown:

```python
class CalendarBot:
    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._cleanup_tasks: List[asyncio.Task] = []
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Signal handler for graceful shutdown."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self) -> None:
        """Graceful shutdown with resource cleanup."""
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete with timeout
        if self._cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._cleanup_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Cleanup tasks did not complete within timeout")
        
        # Close async resources
        await self._source_manager.close()
        await self._cache_manager.close()
        await self._display_manager.close()
```

## 7. Error Recovery and Circuit Breaker Patterns

### Async Circuit Breaker Implementation

The system implements circuit breakers for resilient async operations:

```python
class AsyncCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        await self._check_state()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is not None:
                # Operation failed
                self._failure_count += 1
                self._last_failure_time = time.time()
                
                if self._failure_count >= self._failure_threshold:
                    self._state = "OPEN"
                    logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
            else:
                # Operation succeeded
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    self._failure_count = 0
                    logger.info("Circuit breaker closed - service recovered")
    
    async def _check_state(self) -> None:
        """Check and update circuit breaker state."""
        async with self._lock:
            if self._state == "OPEN":
                if (self._last_failure_time and 
                    time.time() - self._last_failure_time > self._recovery_timeout):
                    self._state = "HALF_OPEN"
                    logger.info("Circuit breaker half-open - testing service")
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")
```

## 8. Performance Monitoring and Resource Tracking

### Async Resource Monitoring

The system tracks async resource usage for performance optimization:

```python
class AsyncResourceMonitor:
    def __init__(self):
        self._active_tasks: Set[asyncio.Task] = set()
        self._task_metrics: Dict[str, Dict[str, Any]] = {}
        self._monitoring_active = True
    
    async def monitor_task(self, name: str, coro: Coroutine) -> Any:
        """Monitor async task execution with metrics collection."""
        task = asyncio.create_task(coro, name=name)
        self._active_tasks.add(task)
        
        start_time = time.time()
        memory_start = self._get_memory_usage()
        
        try:
            result = await task
            
            # Record successful execution metrics
            execution_time = time.time() - start_time
            memory_delta = self._get_memory_usage() - memory_start
            
            self._task_metrics[name] = {
                'execution_time': execution_time,
                'memory_delta': memory_delta,
                'status': 'success',
                'timestamp': time.time()
            }
            
            return result
            
        except Exception as e:
            # Record failure metrics
            self._task_metrics[name] = {
                'execution_time': time.time() - start_time,
                'status': 'failed',
                'error': str(e),
                'timestamp': time.time()
            }
            raise
        
        finally:
            self._active_tasks.discard(task)
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get current resource utilization summary."""
        return {
            'active_tasks': len(self._active_tasks),
            'task_names': [task.get_name() for task in self._active_tasks],
            'recent_metrics': dict(list(self._task_metrics.items())[-10:]),
            'memory_usage': self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
```

## 9. Best Practices and Guidelines

### Async Resource Management Checklist

1. **Event Loop Safety**
   - Always detect existing event loops before creating new ones
   - Use thread pools for sync/async boundary crossing
   - Properly close event loops in finally blocks

2. **Context Management**
   - Use async context managers for all resources
   - Implement `__aenter__` and `__aexit__` methods
   - Handle exceptions in context managers

3. **Timeout Protection**
   - Set timeouts on all async operations
   - Use `asyncio.wait_for()` for operation-level timeouts
   - Implement overall request timeouts

4. **Memory Management**
   - Use async generators for large datasets
   - Implement bounded queues for producer-consumer patterns
   - Monitor memory usage in long-running operations

5. **Error Handling**
   - Implement circuit breakers for external services
   - Use structured exception handling
   - Log resource-related errors with context

6. **Cleanup Patterns**
   - Register signal handlers for graceful shutdown
   - Cancel pending tasks during shutdown
   - Wait for task completion with timeouts

### Common Anti-Patterns to Avoid

❌ **Creating event loops in async contexts**
```python
# Don't do this
async def bad_pattern():
    loop = asyncio.new_event_loop()  # Will conflict with existing loop
    loop.run_until_complete(some_async_func())
```

✅ **Use proper async/sync bridging**
```python
# Do this instead
def good_pattern():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_isolated_loop, async_func)
        return future.result(timeout=5.0)
```

❌ **Not handling resource cleanup**
```python
# Don't do this
async def bad_cleanup():
    client = httpx.AsyncClient()
    return await client.get(url)  # Client never closed
```

✅ **Use context managers for cleanup**
```python
# Do this instead
async def good_cleanup():
    async with httpx.AsyncClient() as client:
        return await client.get(url)  # Client automatically closed
```

---

**Async Resource Management v1.0** - Comprehensive patterns for efficient async resource management in CalendarBot.