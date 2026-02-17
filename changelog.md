# Microsoft To-Do v1.0 API Migration

New in version __version__:

### Breaking Changes
* Migrated from Microsoft To-Do beta API to v1.0 API - database will be cleared on first sync after upgrade
* Renamed TaskFolder to TaskList throughout to match Microsoft API terminology

### Features & Improvements
* Modernized build system: replaced requirements.txt with pyproject.toml and adopted uv package manager
* Added robust JSON error handling to gracefully handle malformed API responses
* Improved authentication flow with better error messages and user notifications
* Enhanced logging with daily rotation and 7-day retention

### Technical
* Added type hints and docstrings throughout the codebase
* Added comprehensive test suite for handlers
* Updated dependencies: requests 2.32.5, msal 1.34.0

For more details:
https://github.com/__githubslug__/releases/tag/__version__
