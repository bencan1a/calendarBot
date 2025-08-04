# E-Paper Rendering Optimizations

## Overview

This document describes the performance optimizations implemented in the e-paper rendering pipeline to improve efficiency on resource-constrained devices like the Raspberry Pi Zero 2W. These optimizations focus on reducing memory usage and CPU load while maintaining visual consistency with the web renderer.

## Optimization Techniques

### 1. Font Caching with LRU Eviction

**Problem:** Font loading is an expensive operation that consumes both CPU time and memory. The original implementation loaded fonts on demand but didn't cache them, leading to repeated loading of the same fonts.

**Solution:** Implemented a Least Recently Used (LRU) font cache that:
- Stores loaded fonts in an OrderedDict for quick access
- Limits the cache size to prevent memory bloat (configurable via `MAX_FONT_CACHE_SIZE`)
- Evicts the least recently used fonts when the cache reaches capacity
- Prioritizes frequently used fonts by moving them to the end of the OrderedDict on access

**Benefits:**
- Reduces CPU usage by avoiding repeated font loading
- Improves rendering speed for text-heavy displays
- Maintains a bounded memory footprint

**Implementation:**
```python
def _get_font(self, font_key: str) -> Union[FreeTypeFont, BuiltinFont]:
    """Get a font from cache or load it if not cached."""
    # Check if font is already in cache
    if font_key in self._font_cache:
        # Move to end of OrderedDict to mark as recently used
        font = self._font_cache.pop(font_key)
        self._font_cache[font_key] = font
        return font
        
    # Load the font
    # ...
        
    # Add to cache with LRU eviction
    if len(self._font_cache) >= MAX_FONT_CACHE_SIZE:
        # Remove least recently used font (first item in OrderedDict)
        self._font_cache.popitem(last=False)
        
    # Add new font to cache
    self._font_cache[font_key] = font
    return font
```

### 2. Text Measurement Caching

**Problem:** Text measurement operations (calculating bounding boxes) are computationally expensive and often repeated for the same text strings.

**Solution:** Implemented a text measurement cache that:
- Stores text bounding box measurements in an OrderedDict
- Uses a composite key of (text, font_key, font_id) to ensure uniqueness
- Limits the cache size to prevent memory bloat (configurable via `MAX_TEXT_MEASURE_CACHE_SIZE`)
- Evicts least recently used measurements when the cache reaches capacity

**Benefits:**
- Reduces CPU usage by avoiding repeated text measurements
- Improves rendering speed for text-heavy displays
- Particularly beneficial for static or repeated text elements

**Implementation:**
```python
def _get_text_bbox(self, draw: ImageDraw.ImageDraw, text: str, font_key: str) -> Tuple[int, int, int, int]:
    """Get text bounding box with caching to avoid repeated calculations."""
    # Create cache key from text and font
    font = self._get_font(font_key)
    cache_key = (text, font_key, id(font))
    
    # Check if measurement is in cache
    if cache_key in self._text_measure_cache:
        # Move to end of OrderedDict to mark as recently used
        bbox = self._text_measure_cache.pop(cache_key)
        self._text_measure_cache[cache_key] = bbox
        return bbox
        
    # Calculate text bbox
    bbox = draw.textbbox((0, 0), text, font=font)
    
    # Add to cache with LRU eviction
    if len(self._text_measure_cache) >= MAX_TEXT_MEASURE_CACHE_SIZE:
        # Remove least recently used measurement
        self._text_measure_cache.popitem(last=False)
        
    # Add new measurement to cache
    self._text_measure_cache[cache_key] = bbox
    return bbox
```

### 3. Image Buffer Pooling

**Problem:** Creating and destroying PIL Image objects is memory-intensive and triggers frequent garbage collection, which can cause rendering stutters.

**Solution:** Implemented an image buffer pool that:
- Reuses image buffers of the same size and mode
- Maintains a pool of buffers for each (mode, width, height) combination
- Limits the pool size to prevent memory bloat (configurable via `BUFFER_POOL_SIZE`)
- Automatically clears recycled buffers to prevent image artifacts

**Benefits:**
- Reduces memory allocation and deallocation overhead
- Minimizes garbage collection pauses
- Improves rendering consistency and reduces stutters

**Implementation:**
```python
def _get_image_buffer(self, mode: str, width: int, height: int) -> Image.Image:
    """Get an image buffer from the pool or create a new one."""
    buffer_key = (mode, width, height)
    
    # Check if we have a buffer of this size in the pool
    if buffer_key in self._image_buffer_pool and self._image_buffer_pool[buffer_key]:
        # Reuse an existing buffer
        image = self._image_buffer_pool[buffer_key].pop()
        # Clear the buffer by filling with background color
        image.paste(self._colors["background"], (0, 0, width, height))
        return image
        
    # Create a new buffer
    return Image.new(mode, (width, height), self._colors["background"])

def _recycle_image_buffer(self, image: Image.Image) -> None:
    """Recycle an image buffer back to the pool."""
    buffer_key = (image.mode, image.width, image.height)
    
    # Initialize pool for this buffer size if needed
    if buffer_key not in self._image_buffer_pool:
        self._image_buffer_pool[buffer_key] = []
        
    # Only keep up to BUFFER_POOL_SIZE buffers of each size
    if len(self._image_buffer_pool[buffer_key]) < BUFFER_POOL_SIZE:
        self._image_buffer_pool[buffer_key].append(image)
```

### 4. Performance Monitoring

**Problem:** Identifying performance bottlenecks in the rendering pipeline was difficult without precise timing information.

**Solution:** Implemented a lightweight performance monitoring utility that:
- Tracks operation timing with millisecond precision
- Adds minimal overhead to the rendering process
- Provides both individual operation timings and summary statistics
- Integrates with the logging system for easy analysis

**Benefits:**
- Enables data-driven optimization decisions
- Helps identify rendering bottlenecks
- Provides quantifiable metrics for performance improvements

**Implementation:**
```python
# In PerformanceMetrics class
def start_operation(self, operation_name: str) -> None:
    """Start timing an operation."""
    self._operation_timers[operation_name] = time.time() * 1000  # Store in milliseconds

def end_operation(self, operation_name: str) -> float:
    """End timing an operation and record the result."""
    if operation_name not in self._operation_timers:
        raise KeyError(f"Operation '{operation_name}' was not started")
        
    end_time = time.time() * 1000
    start_time = self._operation_timers.pop(operation_name)
    duration = end_time - start_time
    
    # Store the result
    self._operation_results[operation_name] = duration
    return duration
```

### 5. Resource Management Improvements

**Problem:** Resource leaks could occur when exceptions were thrown during rendering, leading to memory leaks and degraded performance over time.

**Solution:** Implemented proper resource cleanup in error conditions:
- Added try/except/finally blocks to ensure resources are released
- Recycled image buffers in error conditions
- Ensured performance monitoring operations are properly closed
- Added defensive checks before accessing resources

**Benefits:**
- Prevents memory leaks during error conditions
- Improves long-term stability
- Maintains consistent performance over extended operation

**Implementation:**
```python
try:
    # Rendering code
    # ...
except Exception as e:
    # Clean up resources in case of error
    if 'image' in locals():
        self._recycle_image_buffer(image)
    
    logger.exception("Error rendering image")
    self.performance.end_operation("render_operation")
    return self._render_error_image(f"Error: {e}")
```

### 6. Lazy Font Loading

**Problem:** The original implementation loaded all fonts during initialization, consuming memory even for fonts that might never be used.

**Solution:** Implemented lazy font loading that:
- Loads fonts only when they are first requested
- Leverages the font cache for subsequent accesses
- Reduces initial memory footprint

**Benefits:**
- Reduces initial memory usage
- Improves startup time
- Only loads resources that are actually needed

**Implementation:**
```python
def _load_fonts(self) -> dict[str, Union[FreeTypeFont, BuiltinFont]]:
    """Load fonts optimized for e-Paper display."""
    # This is now a lazy-loading function that returns an empty dict
    # Actual fonts will be loaded on first use via _get_font()
    return {}
```

## Performance Impact

The combined optimizations provide significant performance improvements:

1. **Memory Usage**: Reduced peak memory usage by limiting font caching and reusing image buffers
2. **CPU Load**: Decreased CPU utilization through caching of expensive operations
3. **Rendering Speed**: Improved rendering times, especially for repeated content
4. **Stability**: Enhanced long-term stability through proper resource management

## Benchmarking

A benchmark script is provided in `scripts/benchmark_eink_renderer.py` to measure the performance impact of these optimizations. The script measures:

- Rendering time for the main view
- Rendering time for error screens
- Rendering time for authentication prompts

## Future Optimization Opportunities

1. **Partial Updates**: Further optimize the partial update mechanism to minimize e-paper refresh time
2. **Pre-rendering**: Pre-render static elements for frequently used screens
3. **Bitmap Caching**: Cache rendered bitmaps for static UI elements
4. **Asynchronous Rendering**: Move rendering to a background thread to improve UI responsiveness

## Conclusion

These optimizations significantly improve the performance of the e-paper rendering pipeline on resource-constrained devices like the Raspberry Pi Zero 2W. By reducing memory usage and CPU load, the renderer can provide a responsive and visually consistent experience while minimizing resource consumption.