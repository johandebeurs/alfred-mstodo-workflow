# encoding: utf-8
"""
End-to-end lifecycle tests for tasks: create via API → store in DB → retrieve → delete via API.

These tests hit the real Microsoft Graph API and use a real SQLite database.
They require a valid MSAL token stored in the macOS Keychain (via the workflow's
normal authentication flow). Tests are skipped if no valid token is available.
"""

import os
import shutil
import tempfile
import uuid

import pytest
from peewee import SqliteDatabase
from requests import codes


def _get_keychain_password(service, account):
    """Get password from macOS Keychain using security command.

    The Alfred Workflow library stores passwords as hex-encoded strings,
    so we need to decode them.
    """
    import subprocess

    cmd = [
        'security', 'find-generic-password',
        '-s', service,
        '-a', account,
        '-w'  # Output password only
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        hex_data = result.stdout.strip()
        return bytes.fromhex(hex_data).decode('utf-8')
    except (subprocess.CalledProcessError, ValueError):
        return None


def _is_authorized():
    """Check if we have valid MSAL credentials in the keychain."""
    bundle_id = 'com.johandebeurs.alfred.mstodo'
    cached_data = _get_keychain_password(bundle_id, 'msal')
    return cached_data is not None


skip_without_auth = pytest.mark.skipif(
    not _is_authorized(),
    reason='No valid MSAL token in keychain. Run workflow login first.'
)

pytestmark = skip_without_auth


@pytest.fixture(autouse=True)
def real_workflow(clear_modules_with_import_side_effects):
    """Ensure tests use the real workflow with keychain access.

    This fixture ensures the auth module is properly initialized with
    MSAL credentials from the keychain after conftest clears modules.
    It bypasses wf_wrapper() to avoid getting a mocked workflow.

    Depends on clear_modules_with_import_side_effects to ensure it runs AFTER
    the conftest module clearing is done.
    """
    import sys

    # Clear mstodo.util's _workflow singleton to get fresh real workflow
    if 'mstodo.util' in sys.modules:
        sys.modules['mstodo.util']._workflow = None

    # Clear all API and auth modules to ensure fresh imports
    # These need to reimport to get the new oauth_token reference
    modules_to_clear = [
        'mstodo.auth',
        'mstodo.api',
        'mstodo.api.base',
        'mstodo.api.tasks',
        'mstodo.api.task_lists',
        'mstodo.api.user',
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    # Now import auth fresh - this will set up MSAL with empty cache
    from mstodo import auth

    bundle_id = 'com.johandebeurs.alfred.mstodo'

    try:
        cached_data = _get_keychain_password(bundle_id, 'msal')
        if cached_data:
            auth.cache.deserialize(cached_data)
        else:
            pytest.skip("No MSAL credentials found in keychain")
    except Exception as e:
        pytest.skip(f"Could not load MSAL credentials from keychain: {e}")

    yield

    # Cleanup: reset singleton after test
    if 'mstodo.util' in sys.modules:
        sys.modules['mstodo.util']._workflow = None

    global _cached_default_list_id
    _cached_default_list_id = None


# Cache the default list ID across tests to avoid redundant API calls.
_cached_default_list_id = None


@pytest.fixture()
def default_list_id():
    """Get the user's default task list ID from the real API."""
    global _cached_default_list_id
    if _cached_default_list_id is not None:
        return _cached_default_list_id

    import mstodo.api.base as api

    req = api.get('me/todo/lists')

    if req.status_code != 200:
        pytest.fail(f"Failed to fetch task lists: {req.status_code} - {req.text[:200]}")

    response = api.safe_json_decode(req, 'lists')
    lists = response.get('value', [])

    default_list = next(
        (l for l in lists if l.get('wellknownListName') == 'defaultList'),
        None
    )
    assert default_list is not None, 'No default task list found in Microsoft ToDo account'
    _cached_default_list_id = default_list['id']
    return _cached_default_list_id


@pytest.fixture()
def test_db():
    """Create a real temporary SQLite database with Task and TaskList tables.

    Binds models to the test database and patches the module-level ``db``
    reference used by ``_perform_updates`` for atomic transactions.
    """
    from mstodo.models.task_list import TaskList
    from mstodo.models.task import Task
    import mstodo.models.base as base_module

    tmpdir = tempfile.mkdtemp(prefix='mstodo_test_')
    db_path = os.path.join(tmpdir, 'mstodo_test.db')
    test_database = SqliteDatabase(db_path)

    test_database.bind([TaskList, Task])
    test_database.connect()
    test_database.create_tables([TaskList, Task])

    original_db = base_module.db
    base_module.db = test_database

    yield test_database

    base_module.db = original_db
    test_database.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


def _unique_title(prefix='Test task'):
    """Generate a unique task title to avoid collisions."""
    return f'{prefix} {uuid.uuid4().hex[:8]}'


class TestTaskLifecycle:
    """End-to-end tests for the task create → retrieve → delete lifecycle."""

    def test_create_task_returns_success(self, default_list_id):
        """Creating a task via the API returns a 201 response with task data."""
        from mstodo.api.tasks import create_task, delete_task

        title = _unique_title()
        task_id = None

        try:
            res = create_task(default_list_id, title)

            assert res.status_code == codes.created
            data = res.json()
            assert data['title'] == title
            assert 'id' in data
            task_id = data['id']
        finally:
            if task_id:
                delete_task(default_list_id, task_id)

    def test_create_task_store_in_db_and_retrieve(
        self, default_list_id, test_db
    ):
        """A task created via the API can be stored in and retrieved from the database."""
        from mstodo.api.tasks import create_task, delete_task
        from mstodo.models.task import Task
        from mstodo.models.task_list import TaskList

        title = _unique_title()
        task_id = None

        try:
            # Create task via real API
            res = create_task(default_list_id, title)
            assert res.status_code == codes.created
            task_data = res.json()
            task_id = task_data['id']

            # Insert the parent list into the DB so the foreign key resolves
            TaskList.insert({
                'id': default_list_id,
                'title': 'Tasks',
                'isOwner': True,
                'isShared': False,
                'wellknownListName': 'defaultList',
            }).execute()

            # Transform API response and store in DB
            task_data['list'] = default_list_id
            transformed = Task.transform_datamodel([task_data])
            Task._perform_updates([], transformed)

            # Retrieve from DB and verify
            db_task = Task.get(Task.id == task_id)
            assert db_task.title == title
            assert db_task.status == 'notStarted'
            assert db_task.importance == 'normal'
        finally:
            if task_id:
                delete_task(default_list_id, task_id)

    def test_full_lifecycle_create_retrieve_delete(
        self, default_list_id, test_db
    ):
        """Full lifecycle: create via API, store in DB, retrieve, delete via API."""
        import mstodo.api.base as api
        from mstodo.api.tasks import create_task, delete_task
        from mstodo.models.task import Task
        from mstodo.models.task_list import TaskList

        title = _unique_title('Lifecycle test')
        task_id = None
        deleted = False

        try:
            # 1. Create task via real API
            create_res = create_task(default_list_id, title, starred=True)
            assert create_res.status_code == codes.created
            created_data = create_res.json()
            task_id = created_data['id']

            # 2. Store in local DB
            TaskList.get_or_create(
                id=default_list_id,
                defaults={
                    'title': 'Tasks',
                    'isOwner': True,
                    'isShared': False,
                    'wellknownListName': 'defaultList',
                },
            )

            created_data['list'] = default_list_id
            transformed = Task.transform_datamodel([created_data])
            Task._perform_updates([], transformed)

            # 3. Retrieve from DB and verify
            db_task = Task.get(Task.id == task_id)
            assert db_task.title == title
            assert db_task.status == 'notStarted'
            assert db_task.importance == 'high'  # starred

            # 4. Delete via real API
            delete_res = delete_task(default_list_id, task_id)
            assert delete_res.status_code == codes.no_content
            deleted = True

            # 5. Verify the task is no longer accessible via API
            get_res = api.get(f'me/todo/lists/{default_list_id}/tasks/{task_id}')
            # Microsoft Graph returns 404 for deleted resources
            assert get_res.status_code == 404
        finally:
            if task_id and not deleted:
                delete_task(default_list_id, task_id)

    def test_delete_task_returns_no_content(self, default_list_id):
        """Deleting a task via the API returns a 204 No Content response."""
        from mstodo.api.tasks import create_task, delete_task

        title = _unique_title('Delete test')

        res = create_task(default_list_id, title)
        assert res.status_code == codes.created
        task_id = res.json()['id']

        delete_res = delete_task(default_list_id, task_id)
        assert delete_res.status_code == codes.no_content
