# CONPORT USAGE GUIDE

This document provides comprehensive guidance for using the Context Portal (ConPort) system in the CalendarBot project. It contains detailed initialization sequences, tool usage patterns, and best practices for maintaining project context.

## Table of Contents

- [Initialization Sequence](#initialization-sequence)
- [Core ConPort Operations](#core-conport-operations)
- [Status Prefixes](#status-prefixes)
- [Sync Routine](#sync-routine)
- [Dynamic Context Retrieval](#dynamic-context-retrieval)
- [Knowledge Graph Linking](#knowledge-graph-linking)
- [Tool Reference](#tool-reference)

## Initialization Sequence

### Initial Setup

At the beginning of every session, the agent must execute the initialization sequence to determine ConPort status and load relevant context:

1. Determine workspace ID (absolute path to current workspace)
2. Check for existence of context database
3. If database exists:
   - Load initial contexts (product context, active context, decisions, progress, etc.)
   - Set status to `[CONPORT_ACTIVE]`
4. If database doesn't exist:
   - Inform user and offer to initialize a new database
   - If user agrees, bootstrap from projectBrief.md if available
   - Set status appropriately

### Loading Existing Context

When a context database exists:

1. Load initial contexts:
   - Product context
   - Active context
   - Recent decisions (limit 5)
   - Recent progress (limit 5)
   - System patterns (limit 5)
   - Critical settings
   - Project glossary
   - Recent activity summary
2. Analyze loaded context
3. Set internal status to `[CONPORT_ACTIVE]`
4. Inform user of initialization status

## Core ConPort Operations

### Product Context

- **Purpose**: Stores overall project goals, features, architecture
- **When to Update**: When high-level project description, goals, features, or architecture changes significantly
- **Usage Pattern**:
  1. (Optional) Get current product context
  2. Prepare content (full overwrite) or patch_content (partial update)
  3. Confirm changes with user
  4. Update product context

### Active Context

- **Purpose**: Stores current task focus, immediate goals, session-specific context
- **When to Update**: When current focus changes, new questions arise, or session-specific context needs updating
- **Usage Pattern**:
  1. (Optional) Get current active context
  2. Prepare content (full overwrite) or patch_content (partial update)
  3. Confirm changes with user
  4. Update active context

### Decisions

- **Purpose**: Records significant architectural or implementation decisions
- **When to Log**: When a significant decision is made and confirmed by user
- **Usage Pattern**:
  1. Identify decision point
  2. Prepare summary, rationale, and optional tags
  3. Confirm with user
  4. Log decision

### Progress

- **Purpose**: Tracks task status and completion
- **When to Log**: When a task begins, changes status, or completes
- **Usage Pattern**:
  1. Identify task status change
  2. Prepare description, status, and optional links
  3. Log progress

### System Patterns

- **Purpose**: Documents architectural patterns used in the project
- **When to Log**: When new patterns are introduced or existing ones modified
- **Usage Pattern**:
  1. Identify pattern
  2. Prepare name, description, and optional tags
  3. Confirm with user
  4. Log system pattern

### Custom Data

- **Purpose**: Stores any other structured or unstructured project information
- **When to Log**: For information not covered by other categories (glossary terms, specs, notes)
- **Usage Pattern**:
  1. Identify information to store
  2. Determine appropriate category and key
  3. Prepare value (object or string)
  4. Log custom data

## Status Prefixes

- **Requirement**: Begin EVERY response with either `[CONPORT_ACTIVE]` or `[CONPORT_INACTIVE]`
- **Active**: ConPort database is available and being used
- **Inactive**: ConPort is not available or not being used for the session

## Sync Routine

The ConPort Sync routine synchronizes the database with information from the current chat session:

1. **Trigger**: User types `Sync ConPort` or `ConPort Sync`
2. **Acknowledgment**: Agent responds with `[CONPORT_SYNCING]`
3. **Process**:
   - Review chat history for new information, decisions, progress, context changes
   - Update ConPort with appropriate tools
   - Inform user when synchronization is complete
4. **Post-Sync**: Resume previous task or await new instructions

## Dynamic Context Retrieval

Guidelines for retrieving and assembling context from ConPort:

1. **Analyze Query**: Identify key entities, concepts, keywords
2. **Retrieval Strategy**:
   - Use targeted search for specific terms
   - Use specific item retrieval when item types/IDs are known
   - Use semantic search for conceptual queries
   - Fall back to broad context if targeted retrieval yields little
3. **Initial Retrieval**: Get small set (3-5) of most relevant items
4. **Contextual Expansion**: For promising items, fetch directly related items
5. **Synthesize and Filter**: Review, discard irrelevant items, summarize
6. **Assemble Context**: Construct clear, attributed, concise context

## Knowledge Graph Linking

Guidelines for identifying and creating links between ConPort items:

1. **Monitor Context**: Analyze discussion for mentions of ConPort items and relationships
2. **Identify Links**: Look for patterns indicating relationships between items
3. **Propose Links**: Clearly state items involved and perceived relationship
4. **Execute Linking**: Gather details and create link if user confirms
5. **Confirm Outcome**: Inform user of success or failure

## Tool Reference

### Context Management

- `get_product_context`: Retrieves overall project information
- `update_product_context`: Updates project-level context
- `get_active_context`: Retrieves current session context
- `update_active_context`: Updates session-specific context

### Decision Tracking

- `log_decision`: Records architectural or implementation decisions
- `get_decisions`: Retrieves past decisions
- `search_decisions_fts`: Searches decisions by keywords
- `delete_decision_by_id`: Removes a specific decision

### Progress Tracking

- `log_progress`: Records task status
- `get_progress`: Retrieves task progress
- `update_progress`: Updates existing progress entry
- `delete_progress_by_id`: Removes a progress entry

### System Patterns

- `log_system_pattern`: Records architectural patterns
- `get_system_patterns`: Retrieves defined patterns
- `delete_system_pattern_by_id`: Removes a specific pattern

### Custom Data

- `log_custom_data`: Stores miscellaneous project information
- `get_custom_data`: Retrieves custom data
- `delete_custom_data`: Removes specific custom data
- `search_custom_data_value_fts`: Searches custom data by keywords
- `search_project_glossary_fts`: Searches glossary terms

### Knowledge Graph

- `link_conport_items`: Creates relationships between items
- `get_linked_items`: Retrieves relationships for an item

### History and Activity

- `get_item_history`: Reviews past versions of contexts
- `get_recent_activity_summary`: Summarizes recent project activities

### Batch Operations

- `batch_log_items`: Logs multiple items of the same type

### Export/Import

- `export_conport_to_markdown`: Exports ConPort data to markdown
- `import_markdown_to_conport`: Imports data from markdown files