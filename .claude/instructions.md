# Alfred Microsoft ToDo Workflow - Project Instructions

## Project Overview

This is an Alfred workflow for Microsoft ToDo, built with Python 3. It provides a comprehensive interface for managing Microsoft ToDo tasks directly from Alfred, including natural language date parsing, task creation, searching, and task management.

**Original Author**: Ian Paterson
**Current Maintainer**: Johan de Beurs
**License**: MIT
**Repository**: johandebeurs/alfred-mstodo-workflow

## Technology Stack

### Core Technologies
- **Python**: 3.11+ (must be available in $PATH)
- **Alfred**: Version 5 with Powerpack license required
- **Microsoft ToDo API**: Via MSAL authentication

### Key Dependencies
- `alfred-pyworkflow>=2.1.0,<3.0.0` - Alfred workflow framework
- `msal>=1.34.0,<2.0.0` - Microsoft authentication library
- `parsedatetime>=2.6,<3.0.0` - Natural language date parsing
- `peewee>=3.19.0,<4.0.0` - ORM for local database
- `requests>=2.32.5,<3.0.0` - HTTP library
- `python-dateutil>=2.9.0,<3.0.0` - Date utilities

### Development Dependencies
- `pytest>=9.0.2,<10.0.0` - Testing framework
- `invoke>=2.2.0,<3.0.0` - Task execution
- `pylint>=4.0.4,<5.0.0` - Linting
- `watchfiles>=1.1.1,<2.0.0` - File watching for auto-rebuild
- `pytest-cov>=7.0.0,<8.0.0` - Test coverage
- `pytest-mock>=3.15.1,<4.0.0` - Test mocking

## Project Structure

```
alfred-mstodo-workflow/
├── src/                          # Main source code
│   ├── alfred_mstodo_workflow.py # Entry point
│   ├── mstodo/                   # Core application code
│   │   ├── __init__.py          # Package metadata & version
│   │   ├── auth.py              # Microsoft authentication
│   │   ├── config.py            # Configuration management
│   │   ├── icons.py             # Icon handling
│   │   ├── sync.py              # Data synchronization
│   │   ├── util.py              # Utility functions
│   │   ├── api/                 # API layer
│   │   │   ├── base.py
│   │   │   ├── tasks.py
│   │   │   ├── task_lists.py
│   │   │   └── user.py
│   │   ├── handlers/            # Command handlers
│   │   │   ├── about.py
│   │   │   ├── completed.py
│   │   │   ├── due.py
│   │   │   ├── login.py
│   │   │   ├── logout.py
│   │   │   ├── new_task.py
│   │   │   ├── preferences.py
│   │   │   ├── route.py         # Command routing
│   │   │   ├── search.py
│   │   │   ├── task.py
│   │   │   ├── task_list.py
│   │   │   ├── upcoming.py
│   │   │   └── welcome.py
│   │   └── models/              # Data models
│   │       ├── base.py
│   │       ├── fields.py
│   │       ├── hashtag.py
│   │       ├── preferences.py
│   │       ├── task.py
│   │       ├── task_parser.py   # Natural language parsing
│   │       ├── task_list.py
│   │       └── user.py
│   ├── workflow/                # Alfred workflow library, copied from lib/ for build and distribution
│   ├── bin/                     # Binary scripts
│   ├── icons/                   # Workflow icons
│   ├── info.plist              # Alfred workflow configuration
│   └── version                 # Version number file
├── build/                       # Build scripts
│   ├── paths.py
│   ├── subtasks.py
│   └── tasks.py
├── lib/                        # Third-party libraries (installed via uv)
├── dist/                       # Distribution files
├── tests/                      # Unit tests
│   ├── conftest.py             # Test fixtures
│   ├── builders.py             # Test data builders
│   └── mstodo/
│       ├── handlers/           # Handler tests
│       ├── models/             # Model tests
│       ├── test_sync.py
│       └── test_task_lifecycle.py
├── screenshots/                # Documentation screenshots
├── .vscode/                    # VSCode settings and launch configs
├── pyproject.toml             # Project configuration & dependencies
├── uv.lock                    # Dependency lock file
├── .pylintrc                  # Pylint configuration
├── changelog.md               # Version changelog
└── README.md                  # Project documentation
```

## Key Features

1. **Natural Language Task Entry**: Uses parsedatetime for parsing dates like "tomorrow", "next Tuesday", "in 3 days"
2. **Recurrence Support**: Handle recurring tasks with various intervals (daily, weekly, monthly, etc.)
3. **Multiple Lists**: Support for custom lists beyond default "Tasks"
4. **Reminders**: Set reminders with flexible date/time parsing
5. **Search & Browse**: Search tasks by keyword, list, or hashtag
6. **Task Management**: Complete, delete, and view tasks
7. **Sync**: Stays in sync with Microsoft ToDo
8. **Update Notifications**: Automatic update checking with experimental/beta support
9. **Secure Authentication**: OAuth-based authentication via MSAL

## Command Structure

- `td` - Main entry point / welcome screen
- `td-search` / `tds` - Search tasks
- `td-upcoming` / `tdu` - View upcoming tasks
- `td-due` / `tdd` - View due/overdue tasks
- `td-pref` / `tdp` - Preferences
- `td-about` / `tda` - About screen
- `td [task text]` - Create new task

Commands can be abbreviated to first letter (e.g., `tds` for search).

## Development Workflow

### Initial Setup
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install production dependencies to ./lib (required for Alfred workflow)
uv pip install --target=./lib --requirements pyproject.toml

# Install development dependencies
uv pip install --target=./lib --requirements pyproject.toml --all-extras

# Initial build
uv run invoke -r build build --initial

# Install symlinked workflow in Alfred (opens Alfred)
open mstodo-symlinked.alfredworkflow
```

### Development Process
```bash
# Run tests
uv run invoke -r build test

# Manual build
uv run invoke -r build build

# Auto-rebuild on file changes
uv run invoke -r build monitor
```

### VSCode Integration
The project includes VSCode settings and launch configurations for:
- Debugging with adjusted Python path
- Running tests
- Linting integration

## Code Style & Conventions

### Python Style
- Follow PEP 8 guidelines
- Pylint configuration in `.pylintrc`
- Use type hints where appropriate
- Maximum line length: see `.pylintrc`

### Testing
- All new features should include unit tests
- Run `uv run invoke -r build test` before committing
- Use pytest for testing
- Aim for high test coverage

### Version Management
- Version stored in `pyproject.toml` (development source of truth)
- Version embedded in `info.plist` at build time (runtime source)
- Format: semantic versioning (e.g., "0.2.2" or "0.3.0-a" for alpha)
- `changelog.md` should contain only the changes for the current version
- Experimental updates supported for beta testing

## Important Considerations

### Security
- Never store Microsoft ToDo passwords
- Use OAuth/MSAL for authentication only
- Clear all caches/data on logout
- Credentials stored securely by macOS Keychain

### Language Support
- Primary support: US English
- Limited support: UK English, Dutch, German, Portuguese, Russian, Spanish
- Date parsing coverage varies by language

### Limitations
- No offline mode (requires API connection)
- Changes made offline are not saved
- Tasks must be synced to appear

### Authentication Flow
- Login via Microsoft portal
- Authorization for workflow to access account
- Logout clears all local data and preferences

## Build System

The build system (`build/tasks.py`) handles:
- Packaging the workflow
- Copying dependencies to correct locations
- Creating both regular and symlinked versions
- File watching for auto-rebuild
- Version management

## Database
Uses Peewee ORM with local SQLite database for:
- Cached task data
- User preferences
- List information
- Sync state management

## API Integration
- Base API wrapper in `mstodo/api/base.py`
- Task operations in `mstodo/api/tasks.py`
- List operations in `mstodo/api/task_lists.py`
- User operations in `mstodo/api/user.py`

## Handler Pattern
Each command has a dedicated handler in `mstodo/handlers/`:
- Receives user input from Alfred
- Processes commands and displays output in Alfred
- Adds a `--commit` to execute the command via the API/models
- Relaunches Alfred if required and returns results in proper format

## Common Tasks

### Adding a New Command
1. Create handler in `src/mstodo/handlers/`
2. Register route in `handlers/route.py`
3. Add icon if needed in `src/icons/`
4. Update welcome screen if it's a top-level command
5. Add tests in `tests/`
6. Update README.md with documentation

### Modifying Natural Language Parsing
- Edit `src/mstodo/models/task_parser.py`
- Leverages parsedatetime library
- Test various input formats
- Update documentation with examples

### Updating Dependencies
```bash
# Update pyproject.toml dependencies
# Then reinstall to ./lib
uv pip install --target=./lib --requirements pyproject.toml
uv run invoke -r build build
```

### Debugging
- Alfred debugger (Alfred Preferences > Workflows > Debug) will determine log level. Ask the user to open the debug panel if logs are not detailed enough
- Logs written to workflow directory
- All cli commands that rely on virtual environment content must be run via uv, i.e., `uv run <command>`

## Deployment

The workflow is distributed as:
- `mstodo.alfredworkflow` - Packaged workflow file
- `mstodo-symlinked.alfredworkflow` - Symlinked version for development

Users download from GitHub releases and double-click to install.

## Contributing Guidelines

1. Clone repository
2. Set up development environment
3. Make changes with tests
4. Run full test suite
5. Ensure linting passes
6. Submit pull request with clear description
7. Include screenshots for UI changes

## Support & Feedback

- GitHub Issues: https://github.com/johandebeurs/alfred-mstodo-workflow/issues
- Documentation: README.md
- Original project: alfred-wunderlist by idpaterson

## Notes for AI Assistants

- This is a defensive security project (task management) - modifications are permitted
- When making changes, always run tests before suggesting completion
- Respect the existing code structure and patterns
- Use the handler pattern for new commands
- Follow the natural language parsing patterns already established
- Consider sync implications when modifying data models
- Test with actual Alfred when possible
- Remember that this runs in Alfred's Python environment, not a standard shell
