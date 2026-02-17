# encoding: utf-8
"""
Shared pytest fixtures for the Alfred MS ToDo Workflow test suite.

This module provides common fixtures for mocking the workflow instance,
authentication, sync operations, notifications, and test data.
"""

import pytest
import sys
import importlib
from unittest.mock import MagicMock, Mock, PropertyMock
from datetime import datetime, timezone, date, time, timedelta


# List of modules that need to be cleared before each test
# These modules have module-level code that calls wf_wrapper() or other functions
MODULES_TO_CLEAR = [
    # Auth module runs wf_wrapper() at import and has atexit handlers
    'mstodo.auth',
    # Icons module runs wf_wrapper() and Preferences.current_prefs() at import
    'mstodo.icons',
    # Sync module needs fresh import for proper mocking
    'mstodo.sync',
    # Task parser imports Preferences and needs fresh import
    'mstodo.models.task_parser',
    # Handler modules that call wf_wrapper() at import
    'mstodo.handlers.about',
    'mstodo.handlers.completed',
    'mstodo.handlers.due',
    'mstodo.handlers.login',
    'mstodo.handlers.logout',
    'mstodo.handlers.new_task',
    'mstodo.handlers.preferences',
    'mstodo.handlers.route',
    'mstodo.handlers.search',
    'mstodo.handlers.task',
    'mstodo.handlers.task_list',
    'mstodo.handlers.upcoming',
    'mstodo.handlers.welcome',
]


def _reset_util_module():
    """Reset the _workflow singleton in mstodo.util if it's imported."""
    if 'mstodo.util' in sys.modules:
        sys.modules['mstodo.util']._workflow = None


def _create_mock_workflow():
    """Create a configured mock workflow instance."""
    wf_mock = MagicMock()
    wf_mock.version = '0.3.0'
    wf_mock.datadir = '/tmp/alfred-test'
    wf_mock.workflowfile = lambda x: f'/tmp/workflow/{x}'
    wf_mock.cachefile = lambda x: f'/tmp/cache/{x}'
    wf_mock.logfile = '/tmp/workflow.log'
    wf_mock.settings = {}
    wf_mock.update_available = False
    wf_mock.debugging = False
    wf_mock.alfred_version = MagicMock()
    wf_mock.alfred_version.tuple = (5, 0, 0)
    wf_mock.info = {'webaddress': 'https://github.com/johandebeurs/alfred-mstodo-workflow'}

    # Alfred environment variables - theme_background is rgba formatted
    wf_mock.alfred_env = {
        'theme_background': 'rgba(40,40,40,0.90)',  # Dark theme
    }

    # Mock stored_data to return empty list by default
    wf_mock.stored_data = MagicMock(return_value=[])
    wf_mock.cached_data = MagicMock(return_value=None)
    wf_mock.cache_data = MagicMock()
    wf_mock.clear_data = MagicMock()
    wf_mock.clear_cache = MagicMock()
    wf_mock.filter = MagicMock(return_value=[])

    # Track items added to workflow - use dict for easier assertion
    wf_mock._items = []
    def track_add_item(*args, **kwargs):
        item = {
            'title': args[0] if args else kwargs.get('title'),
            'subtitle': args[1] if len(args) > 1 else kwargs.get('subtitle'),
            'arg': kwargs.get('arg'),
            'autocomplete': kwargs.get('autocomplete'),
            'valid': kwargs.get('valid', True),
            'icon': kwargs.get('icon'),
        }
        wf_mock._items.append(item)
        mock_item = MagicMock()
        mock_item.add_modifier = MagicMock(return_value=mock_item)
        return mock_item
    wf_mock.add_item = MagicMock(side_effect=track_add_item)
    wf_mock.send_feedback = MagicMock()

    return wf_mock


def _clear_module(module_name):
    """Clear a module from sys.modules and from its parent package."""
    # Clear from sys.modules
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Also clear from parent package's namespace to force reimport
    parts = module_name.rsplit('.', 1)
    if len(parts) == 2:
        parent_name, child_name = parts
        if parent_name in sys.modules:
            parent = sys.modules[parent_name]
            if hasattr(parent, child_name):
                delattr(parent, child_name)


@pytest.fixture(autouse=True)
def clear_modules_with_import_side_effects():
    """Clear cached modules before each test.

    This ensures that module-level code (like wf = wf_wrapper()) runs
    after our mocks are in place.
    """
    # Reset the _workflow singleton before clearing modules
    _reset_util_module()

    # Clear modules from cache before the test
    for module_name in MODULES_TO_CLEAR:
        _clear_module(module_name)
    yield
    # Reset and clear again after the test for clean slate
    _reset_util_module()
    for module_name in MODULES_TO_CLEAR:
        _clear_module(module_name)


def _create_mock_preferences():
    """Create mock preferences with default values."""
    prefs = MagicMock()
    prefs.show_completed_tasks = False
    prefs.reminder_time = time(9, 0, 0)
    prefs.reminder_today_offset = time(1, 0, 0)
    # reminder_today_offset_timedelta is a computed property
    prefs.reminder_today_offset_timedelta = timedelta(hours=1, minutes=0)
    prefs.default_task_list_id = None
    prefs.last_task_list_id = None
    prefs.automatic_reminders = False
    prefs.explicit_keywords = False
    prefs.prerelease_channel = False
    prefs.date_locale = None
    prefs.icon_theme = 'dark'  # Set explicit theme to avoid alfred_is_dark() call
    prefs.due_order = ['order', 'due_date', 'TaskList.id']
    prefs.hoist_skipped_tasks = False
    prefs.upcoming_duration = 7
    prefs.completed_duration = 7
    return prefs


@pytest.fixture
def mock_workflow(mocker):
    """Mock the workflow instance used throughout the app.

    Returns a MagicMock configured with common workflow attributes.
    The wf_wrapper is patched at mstodo.util level BEFORE handler imports.
    Also patches Preferences.current_prefs since icons module calls it at import.
    """
    wf_mock = _create_mock_workflow()
    prefs_mock = _create_mock_preferences()

    # Patch the wf_wrapper function at the source
    mocker.patch('mstodo.util.wf_wrapper', return_value=wf_mock)
    mocker.patch('mstodo.util._workflow', wf_mock)

    # Patch Preferences.current_prefs - called by icons module at import
    mocker.patch('mstodo.models.preferences.Preferences.current_prefs', return_value=prefs_mock)

    # Store prefs_mock on wf_mock for test access
    wf_mock._prefs = prefs_mock

    return wf_mock


@pytest.fixture
def mock_authorized(mocker):
    """Mock is_authorised to return True."""
    return mocker.patch('mstodo.auth.is_authorised', return_value=True)


@pytest.fixture
def mock_unauthorized(mocker):
    """Mock is_authorised to return False."""
    return mocker.patch('mstodo.auth.is_authorised', return_value=False)


@pytest.fixture
def mock_oauth_token(mocker):
    """Mock oauth_token to return a valid token."""
    return mocker.patch('mstodo.auth.oauth_token', return_value='mock_token_123')


@pytest.fixture
def mock_authorise(mocker):
    """Mock the authorise function."""
    return mocker.patch('mstodo.auth.authorise', return_value=True)


@pytest.fixture
def mock_deauthorise(mocker):
    """Mock the deauthorise function."""
    return mocker.patch('mstodo.auth.deauthorise')


@pytest.fixture
def mock_background_sync(mocker):
    """Mock background_sync to prevent actual sync calls."""
    return mocker.patch('mstodo.sync.background_sync')


@pytest.fixture
def mock_sync(mocker):
    """Mock sync function."""
    return mocker.patch('mstodo.sync.sync', return_value=True)


@pytest.fixture
def mock_notify(mocker):
    """Mock desktop notifications."""
    return mocker.patch('workflow.notify.notify')


@pytest.fixture
def mock_relaunch_alfred(mocker):
    """Mock relaunch_alfred function."""
    return mocker.patch('mstodo.util.relaunch_alfred')


@pytest.fixture
def mock_webbrowser(mocker):
    """Mock webbrowser.open for testing URL opening."""
    return mocker.patch('webbrowser.open')


@pytest.fixture
def mock_task_lists_data():
    """Sample task list data."""
    return [
        {'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'},
        {'id': 'list2', 'title': 'Shopping', 'wellknownListName': ''},
        {'id': 'list3', 'title': 'Work', 'wellknownListName': ''},
    ]


@pytest.fixture
def mock_tasks_data():
    """Sample task data."""
    now = datetime.now(timezone.utc)
    return [
        {
            'id': 'task1',
            'title': 'Buy milk',
            'status': 'notStarted',
            'dueDateTime': now.isoformat(),
            'list': 'list2',
            'importance': 'normal'
        },
        {
            'id': 'task2',
            'title': 'Finish report',
            'status': 'notStarted',
            'dueDateTime': now.isoformat(),
            'list': 'list3',
            'importance': 'high'
        },
    ]


@pytest.fixture
def mock_preferences(mocker):
    """Mock Preferences.current_prefs() with default values."""
    prefs = MagicMock()
    prefs.show_completed_tasks = False
    prefs.reminder_time = time(9, 0, 0)
    prefs.reminder_today_offset = time(1, 0, 0)
    prefs.reminder_today_offset_timedelta = timedelta(hours=1, minutes=0)
    prefs.default_task_list_id = None
    prefs.last_task_list_id = None
    prefs.automatic_reminders = False
    prefs.explicit_keywords = False
    prefs.prerelease_channel = False
    prefs.date_locale = None
    prefs.icon_theme = 'dark'
    prefs.due_order = ['order', 'due_date', 'TaskList.id']
    prefs.hoist_skipped_tasks = False
    prefs.upcoming_duration = 7
    prefs.completed_duration = 7

    mocker.patch('mstodo.models.preferences.Preferences.current_prefs', return_value=prefs)
    return prefs


@pytest.fixture
def mock_db(mocker):
    """Mock database operations."""
    db_mock = MagicMock()
    mocker.patch('mstodo.models.base.db', db_mock)
    return db_mock


@pytest.fixture
def mock_is_running(mocker):
    """Mock is_running from workflow.background."""
    return mocker.patch('workflow.background.is_running', return_value=False)


@pytest.fixture
def mock_run_in_background(mocker):
    """Mock run_in_background from workflow.background."""
    return mocker.patch('workflow.background.run_in_background')


