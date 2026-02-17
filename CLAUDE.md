# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Alfred workflow for Microsoft ToDo, built with Python 3.11+. Provides task management directly from Alfred with natural language date parsing (via parsedatetime), task creation, searching, and sync with Microsoft ToDo API.

## Development Commands

```bash
# Run tests
uv run invoke -r build test

# Run single test
uv run pytest tests/mstodo/models/test_task_parser.py -v

# Build workflow
uv run invoke -r build build

# Initial build (creates symlinked workflow for development)
uv run invoke -r build build --initial

# Auto-rebuild on file changes
uv run invoke -r build monitor

# Install production dependencies to ./lib
uv pip install --target=./lib --python 3.11 .

# Install dev dependencies
uv pip install --python 3.11 -e ".[dev]"
```

## Architecture

### Entry Point
- `src/alfred_mstodo_workflow.py` - Main entry point called by Alfred

### Core Package (`src/mstodo/`)

**Handlers** (`handlers/`): Each Alfred command has a dedicated handler
- `route.py` - Routes commands to appropriate handlers
- `welcome.py`, `search.py`, `due.py`, `upcoming.py`, `new_task.py`, etc.

**Models** (`models/`): Data models using Peewee ORM with SQLite
- `task.py`, `task_list.py` - Core domain models
- `task_parser.py` - Natural language parsing for dates/recurrence
- `preferences.py` - User preferences storage

**API** (`api/`): Microsoft Graph API integration
- `base.py` - Base API wrapper with authentication
- `tasks.py`, `task_lists.py`, `user.py` - Endpoint implementations

**Other**:
- `auth.py` - MSAL-based Microsoft authentication
- `sync.py` - Data synchronization with Microsoft ToDo
- `config.py` - Configuration management

### Build System (`build/`)
- `tasks.py` - Invoke tasks for building/testing
- Packages workflow to `mstodo.alfredworkflow`
- Creates symlinked version for development

### Dependencies
Production dependencies installed to `./lib/` directory (bundled with workflow).

## Key Patterns

### Handler Pattern
Handlers receive user input from Alfred, process it, interact with API/models, and return Alfred-formatted results. To add a new command:
1. Create handler in `src/mstodo/handlers/`
2. Register route in `handlers/route.py`
3. Add icon in `src/icons/` if needed

### Natural Language Parsing
`task_parser.py` uses parsedatetime for flexible date input like "tomorrow", "next Tuesday", "in 3 days". Test changes thoroughly with various input formats.

## Version Management
- Source of truth: `pyproject.toml`
- Runtime version embedded in `info.plist` at build time
- Update `changelog.md` with changes
