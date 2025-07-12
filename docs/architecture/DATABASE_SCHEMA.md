# Database Schema Documentation

## Overview

CalendarBot uses **SQLite** with **aiosqlite** for asynchronous database operations. The database implements a sophisticated caching architecture with WAL mode, comprehensive indexing, TTL management, and event deduplication strategies.

## Database Configuration

### SQLite Pragma Settings

The database is configured with optimal settings for performance and reliability:

```sql
-- WAL mode for better concurrent access and reduced SD card wear
PRAGMA journal_mode=WAL;

-- Normal synchronous mode for better performance
PRAGMA synchronous=NORMAL;

-- Enable foreign key constraints
PRAGMA foreign_keys=ON;
```

### Key Benefits

- **WAL Mode**: Write-Ahead Logging reduces database locks and provides better concurrent access
- **Reduced SD Card Wear**: WAL mode minimizes write operations on embedded systems
- **Performance Optimization**: NORMAL synchronous mode balances safety with speed
- **Data Integrity**: Foreign key constraints ensure referential integrity

## Table Schema

### cached_events Table

Primary table for storing calendar event data with comprehensive metadata.

```sql
CREATE TABLE cached_events (
    -- Primary identification
    id TEXT PRIMARY KEY,                    -- Unique cache ID (cached_{graph_id})
    graph_id TEXT UNIQUE NOT NULL,         -- Original Microsoft Graph/source ID
    
    -- Event content
    subject TEXT NOT NULL,                  -- Event title/summary
    body_preview TEXT,                      -- Event description excerpt
    
    -- Temporal data (ISO 8601 strings for SQLite compatibility)
    start_datetime TEXT NOT NULL,          -- Event start time
    end_datetime TEXT NOT NULL,            -- Event end time
    start_timezone TEXT NOT NULL,          -- Start timezone identifier
    end_timezone TEXT NOT NULL,            -- End timezone identifier
    is_all_day INTEGER NOT NULL DEFAULT 0, -- All-day event flag (boolean as int)
    
    -- Status and visibility
    show_as TEXT NOT NULL DEFAULT 'busy',  -- Availability status
    is_cancelled INTEGER NOT NULL DEFAULT 0,    -- Cancellation status
    is_organizer INTEGER NOT NULL DEFAULT 0,    -- Current user organizer status
    
    -- Location information
    location_display_name TEXT,            -- Human-readable location
    location_address TEXT,                 -- Structured address data
    
    -- Meeting details
    is_online_meeting INTEGER NOT NULL DEFAULT 0,  -- Virtual meeting flag
    online_meeting_url TEXT,               -- Meeting join URL
    web_link TEXT,                        -- Calendar web link (Graph API only)
    
    -- Recurrence information
    is_recurring INTEGER NOT NULL DEFAULT 0,       -- Recurring event flag
    series_master_id TEXT,                 -- Parent event ID for recurrences
    
    -- Cache metadata
    cached_at TEXT NOT NULL,               -- Cache timestamp (ISO 8601)
    last_modified TEXT,                    -- Source last modified timestamp
    
    -- System timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Field Details

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | TEXT | Primary cache identifier | Primary Key, Format: `cached_{graph_id}` |
| `graph_id` | TEXT | Source system event ID | Unique, Not Null |
| `subject` | TEXT | Event title | Not Null |
| `body_preview` | TEXT | Event description excerpt | Optional |
| `start_datetime` | TEXT | Event start (ISO 8601) | Not Null |
| `end_datetime` | TEXT | Event end (ISO 8601) | Not Null |
| `start_timezone` | TEXT | Start timezone identifier | Not Null |
| `end_timezone` | TEXT | End timezone identifier | Not Null |
| `is_all_day` | INTEGER | All-day event flag | Boolean as INTEGER |
| `show_as` | TEXT | Availability status | Default: 'busy' |
| `is_cancelled` | INTEGER | Cancellation status | Boolean as INTEGER |
| `is_organizer` | INTEGER | User is organizer | Boolean as INTEGER |
| `location_display_name` | TEXT | Location name | Optional |
| `location_address` | TEXT | Location address | Optional |
| `is_online_meeting` | INTEGER | Virtual meeting flag | Boolean as INTEGER |
| `online_meeting_url` | TEXT | Meeting join URL | Optional |
| `web_link` | TEXT | Calendar web link | Optional (Graph API only) |
| `is_recurring` | INTEGER | Recurring event flag | Boolean as INTEGER |
| `series_master_id` | TEXT | Parent event ID | Optional |
| `cached_at` | TEXT | Cache timestamp | Not Null, ISO 8601 |
| `last_modified` | TEXT | Source modification time | Optional, ISO 8601 |

### cache_metadata Table

Stores cache management metadata and operational statistics.

```sql
CREATE TABLE cache_metadata (
    key TEXT PRIMARY KEY,                   -- Metadata key identifier
    value TEXT NOT NULL,                    -- Metadata value (JSON/string)
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP  -- Last update timestamp
);
```

#### Metadata Keys

| Key | Type | Description |
|-----|------|-------------|
| `last_update` | ISO 8601 String | Last cache operation timestamp |
| `last_successful_fetch` | ISO 8601 String | Last successful API fetch |
| `consecutive_failures` | Integer String | Count of consecutive fetch failures |
| `last_error` | String | Last error message |
| `last_error_time` | ISO 8601 String | Last error timestamp |

## Indexing Strategy

### Primary Indexes

```sql
-- Date range query optimization (most common query pattern)
CREATE INDEX idx_events_datetime 
ON cached_events(start_datetime, end_datetime);

-- Graph ID lookup optimization (for deduplication)
CREATE INDEX idx_events_graph_id 
ON cached_events(graph_id);
```

### Index Performance Benefits

1. **Date Range Queries**: Primary use case for calendar display
2. **Event Deduplication**: Fast lookups during INSERT OR REPLACE operations
3. **Query Optimization**: Composite index on datetime fields optimizes range queries

### Query Performance

```sql
-- Optimized query using datetime index
SELECT * FROM cached_events 
WHERE start_datetime <= ? AND end_datetime >= ? 
AND is_cancelled = 0 
ORDER BY start_datetime ASC;
```

## Database Triggers

### Automatic Timestamp Updates

```sql
CREATE TRIGGER update_events_timestamp
AFTER UPDATE ON cached_events
BEGIN
    UPDATE cached_events SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
```

**Purpose**: Automatically maintains `updated_at` timestamps for event modifications.

## TTL Management

### Cache Expiration Strategy

TTL (Time-To-Live) is implemented through the `CacheMetadata` model:

```python
class CacheMetadata(BaseModel):
    cache_ttl_seconds: int = 3600  # 1 hour default
    last_successful_fetch: Optional[str] = None
    
    def is_cache_expired(self) -> bool:
        """Check if cache has expired based on TTL."""
        if not self.last_successful_fetch_dt:
            return True
        
        now = datetime.now()
        expiry_time = self.last_successful_fetch_dt + timedelta(seconds=self.cache_ttl_seconds)
        return now > expiry_time
```

### Cleanup Operations

#### Old Event Cleanup

```sql
-- Remove events older than specified days
DELETE FROM cached_events 
WHERE end_datetime < ?;
```

**Default**: Events older than 7 days are automatically cleaned up.

#### Cache Clearing

```python
async def clear_cache(self) -> bool:
    """Clear all cached events and reset metadata."""
    # Clear all events
    await self.cleanup_old_events(days_old=0)
    
    # Reset metadata
    await self.db.update_cache_metadata(
        last_update=None,
        last_successful_fetch=None,
        consecutive_failures=0,
        last_error=None,
        last_error_time=None,
    )
```

## Event Deduplication

### UPSERT Strategy

```sql
INSERT OR REPLACE INTO cached_events (
    id, graph_id, subject, body_preview,
    start_datetime, end_datetime, start_timezone, end_timezone,
    is_all_day, show_as, is_cancelled, is_organizer,
    location_display_name, location_address,
    is_online_meeting, online_meeting_url, web_link,
    is_recurring, series_master_id, cached_at, last_modified
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```

### Deduplication Logic

1. **Primary Key**: Uses `id` field (format: `cached_{graph_id}`)
2. **Unique Constraint**: `graph_id` ensures source event uniqueness
3. **Conflict Resolution**: `INSERT OR REPLACE` updates existing events
4. **Metadata Preservation**: Maintains cache timestamps during updates

## Data Models

### Pydantic Integration

The database uses Pydantic models for data validation and serialization:

```python
class CachedEvent(BaseModel):
    """Cached calendar event model for local storage."""
    
    # Primary identification
    id: str
    graph_id: str
    
    # Event details with validation
    subject: str
    body_preview: Optional[str] = None
    
    # Temporal data (ISO strings for SQLite)
    start_datetime: str
    end_datetime: str
    start_timezone: str
    end_timezone: str
    is_all_day: bool = False
    
    # Computed properties for datetime conversion
    @property
    def start_dt(self) -> datetime:
        """Get start datetime as datetime object."""
        return datetime.fromisoformat(self.start_datetime.replace("Z", "+00:00"))
    
    @property
    def end_dt(self) -> datetime:
        """Get end datetime as datetime object."""
        return datetime.fromisoformat(self.end_datetime.replace("Z", "+00:00"))
```

### Type Safety Benefits

1. **Runtime Validation**: Pydantic validates data integrity
2. **Type Conversion**: Automatic conversion between SQLite and Python types
3. **Boolean Handling**: Seamless INTEGER ↔ bool conversion
4. **DateTime Processing**: ISO string ↔ datetime object conversion

## Async Operations

### aiosqlite Implementation

All database operations use `aiosqlite` for non-blocking I/O:

```python
async def store_events(self, events: List[CachedEvent]) -> bool:
    """Store calendar events asynchronously."""
    async with aiosqlite.connect(str(self.database_path)) as db:
        await db.executemany(
            "INSERT OR REPLACE INTO cached_events (...) VALUES (...)",
            [(event.field1, event.field2, ...) for event in events]
        )
        await db.commit()
        return True
```

### Connection Management

- **Connection Pooling**: Automatic connection management per operation
- **Transaction Safety**: Explicit commits for data integrity
- **Error Handling**: Comprehensive exception handling with rollback support

## Performance Characteristics

### Query Optimization

| Operation | Optimization | Performance Impact |
|-----------|--------------|-------------------|
| Date Range Queries | Composite index on datetime fields | O(log n) lookup + range scan |
| Event Deduplication | Unique index on graph_id | O(log n) conflict detection |
| Metadata Updates | Single-row operations | O(1) updates |
| Bulk Inserts | Batch executemany() | Minimized transaction overhead |

### Memory Management

- **Streaming Results**: Row-by-row processing for large result sets
- **Batch Operations**: Bulk inserts/updates for efficiency
- **Connection Scope**: Per-operation connections minimize memory footprint

## Monitoring and Diagnostics

### Database Information Query

```python
async def get_database_info(self) -> Dict[str, Any]:
    """Get comprehensive database statistics."""
    return {
        "file_size_bytes": self.database_path.stat().st_size,
        "events_by_date": [...],  # Event distribution
        "user_version": 0,        # Schema version
        "journal_mode": "wal"     # WAL mode confirmation
    }
```

### Health Checks

- **File Size Monitoring**: Track database growth
- **Event Distribution**: Analyze temporal data distribution
- **Journal Mode Verification**: Confirm WAL mode operation
- **Index Usage**: Monitor query performance

## Migration Strategy

### Schema Versioning

```sql
-- Check current schema version
PRAGMA user_version;

-- Update schema version (for migrations)
PRAGMA user_version = 1;
```

### Future Considerations

1. **Backward Compatibility**: Maintain compatibility with existing data
2. **Migration Scripts**: Automated schema updates
3. **Data Preservation**: Safe migration of existing cached events
4. **Index Optimization**: Performance tuning based on usage patterns

## Security Considerations

### Data Protection

- **Local Storage**: All data stored locally, no cloud exposure
- **File Permissions**: Restricted database file access
- **Input Validation**: Pydantic model validation prevents injection
- **Transaction Safety**: Atomic operations prevent corruption

### Privacy Compliance

- **Data Retention**: Automatic cleanup of old events
- **Local Processing**: No external data transmission
- **User Control**: Complete local data management

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Database Lock | Connection timeouts | Check WAL mode, reduce concurrent operations |
| Large Database Size | Slow queries | Run cleanup operations, optimize indexes |
| Memory Usage | High memory consumption | Use streaming queries, batch operations |
| Corruption | Data integrity errors | Database recovery, restore from backup |

### Diagnostic Queries

```sql
-- Check database size and page count
PRAGMA page_count;
PRAGMA page_size;

-- Verify indexes are being used
EXPLAIN QUERY PLAN SELECT * FROM cached_events 
WHERE start_datetime <= ? AND end_datetime >= ?;

-- Check table statistics
SELECT COUNT(*) as total_events, 
       MIN(start_datetime) as earliest_event,
       MAX(end_datetime) as latest_event
FROM cached_events;
```

## Best Practices

### Development Guidelines

1. **Always use async/await**: Leverage aiosqlite's async capabilities
2. **Batch operations**: Use executemany() for bulk operations
3. **Transaction boundaries**: Explicit commits for critical operations
4. **Error handling**: Comprehensive exception handling
5. **Index awareness**: Design queries to use existing indexes

### Performance Optimization

1. **Query optimization**: Use EXPLAIN QUERY PLAN for analysis
2. **Index maintenance**: Monitor index usage and effectiveness
3. **Regular cleanup**: Implement automated old data removal
4. **Memory monitoring**: Track memory usage during bulk operations

### Data Integrity

1. **Validation**: Use Pydantic models for all data operations
2. **Constraint enforcement**: Rely on database constraints
3. **Atomic operations**: Group related changes in transactions
4. **Backup strategy**: Regular database backups for recovery