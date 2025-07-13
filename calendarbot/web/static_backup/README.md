# Legacy Layout Files Backup

This directory contains the old layout files that were migrated to the new layout system on 2025-07-12.

## Files

- `3x4.css` - Legacy CSS for 3x4 grid layout
- `3x4.js` - Legacy JavaScript for 3x4 grid layout
- `4x8.css` - Legacy CSS for 4x8 grid layout  
- `4x8.js` - Legacy JavaScript for 4x8 grid layout

## Migration

These files have been migrated to the new layout system at:
- `calendarbot/layouts/3x4/`
- `calendarbot/layouts/4x8/`

The new layout system includes:
- Layout metadata (`layout.json`)
- Dynamic resource loading via ResourceManager
- Layout-renderer separation architecture

## Safety

These files are kept as backup during the migration period. They can be safely removed once the new layout system is fully verified and deployed.

## New Architecture

The new layout system provides:
- Dynamic layout discovery
- Separation of layout from renderer concerns
- Extensible layout registry
- Improved resource management