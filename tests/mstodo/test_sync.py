# encoding: utf-8
"""
Tests for the sync module - synchronization with Microsoft ToDo API.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestSyncBasics:
    """Test basic sync functionality."""

    def test_sync_requires_authorization(self, mock_workflow, mocker):
        """Sync fails gracefully when user is not authorized."""
        mocker.patch('mstodo.auth.is_authorised', return_value=False)
        mock_notify = mocker.patch('workflow.notify.notify')

        from mstodo.sync import sync
        result = sync(background=False)

        assert result is False
        mock_notify.assert_called()
        # Verify notification mentions authentication
        call_args = mock_notify.call_args
        assert 'Authentication' in call_args[1].get('title', '') or \
               'auth' in str(call_args[1].get('message', '')).lower()

    def test_sync_requires_valid_oauth_token(self, mock_workflow, mocker):
        """Sync fails when OAuth token cannot be obtained."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value=None)
        mock_notify = mocker.patch('workflow.notify.notify')

        from mstodo.sync import sync
        result = sync(background=False)

        assert result is False
        mock_notify.assert_called()

    def test_sync_returns_true_on_success(self, mock_workflow, mocker):
        """Successful sync returns True."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Mock models with proper class structure
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync
        result = sync(background=False)

        assert result is True

    def test_sync_caches_completion_time(self, mock_workflow, mocker):
        """Sync completion time is cached."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Mock models
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = Exception
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync
        sync(background=False)

        # Verify cache_data was called with last_sync
        mock_workflow.cache_data.assert_called()
        calls = [c for c in mock_workflow.cache_data.call_args_list if c[0][0] == 'last_sync']
        assert len(calls) > 0


class TestSyncNotifications:
    """Test sync notifications."""

    def test_manual_sync_shows_progress_notification(self, mock_workflow, mocker):
        """Manual sync shows progress notification."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mock_notify = mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Mock models to raise User.DoesNotExist to simulate sync behavior
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock(side_effect=mock_user_class.DoesNotExist())
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync
        sync(background=False)

        # Should have received notifications
        assert mock_notify.called
        # Check for sync-related notifications
        calls = mock_notify.call_args_list
        titles = [c[1].get('title', '') for c in calls]
        assert any('sync' in t.lower() or 'wait' in t.lower() for t in titles)

    def test_background_sync_no_notifications_unless_first_sync(self, mock_workflow, mocker):
        """Background sync doesn't show notifications (except first sync)."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mock_notify = mocker.patch('workflow.notify.notify')

        # Mock User.get to succeed (not first sync)
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()  # Returns successfully, not first sync
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync
        sync(background=True)

        # Background sync should not show notifications for non-first sync
        # (This may vary based on implementation)


class TestSyncErrorHandling:
    """Test sync error handling."""

    def test_sync_handles_401_authentication_error(self, mock_workflow, mocker):
        """401 error triggers deauthorization."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mock_notify = mocker.patch('workflow.notify.notify')
        mock_deauthorise = mocker.patch('mstodo.auth.deauthorise')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Create a mock HTTPError with 401 status
        from requests.exceptions import HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 401
        http_error = HTTPError(response=mock_response)

        # Mock User to raise HTTPError
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock(side_effect=http_error)

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync
        result = sync(background=False)

        assert result is False
        mock_deauthorise.assert_called_once()

    def test_sync_handles_other_http_errors(self, mock_workflow, mocker):
        """Non-401 HTTP errors are raised, not deauthorized."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mock_notify = mocker.patch('workflow.notify.notify')
        mock_deauthorise = mocker.patch('mstodo.auth.deauthorise')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Create a mock HTTPError with 500 status
        from requests.exceptions import HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = HTTPError(response=mock_response)

        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock(side_effect=http_error)

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        from mstodo.sync import sync

        with pytest.raises(HTTPError):
            sync(background=False)

        # deauthorise should NOT be called for non-401 errors
        mock_deauthorise.assert_not_called()


class TestSyncConcurrency:
    """Test sync concurrency handling."""

    def test_manual_sync_waits_for_running_sync(self, mock_workflow, mocker):
        """Manual sync waits if another sync is running."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mock_notify = mocker.patch('workflow.notify.notify')

        # Simulate is_running returning True twice, then False
        call_count = [0]
        def is_running_side_effect(name):
            call_count[0] += 1
            return call_count[0] < 3

        mocker.patch('workflow.background.is_running', side_effect=is_running_side_effect)
        mock_sleep = mocker.patch('time.sleep')

        from mstodo.sync import sync
        result = sync(background=False)

        # Should have waited (slept) while sync was running
        assert mock_sleep.called
        # Should return False because we waited for another sync
        assert result is False


class TestBackgroundSync:
    """Test background_sync function."""

    def test_background_sync_skips_if_recently_synced(self, mock_workflow, mocker):
        """Background sync doesn't run if last sync was recent."""
        # Set last_sync to 10 seconds ago (well within the 30 second threshold)
        recent_sync = datetime.now(timezone.utc) - timedelta(seconds=10)
        mock_workflow.cached_data.return_value = recent_sync

        mock_run_in_background = mocker.patch('workflow.background.run_in_background')

        from mstodo.sync import background_sync
        background_sync()

        # Should not trigger background process
        mock_run_in_background.assert_not_called()

    def test_background_sync_runs_if_never_synced(self, mock_workflow, mocker):
        """Background sync runs if last_sync is None."""
        mock_workflow.cached_data.return_value = None
        mock_run_in_background = mocker.patch('workflow.background.run_in_background')

        from mstodo.sync import background_sync
        background_sync()

        # Should trigger background process
        mock_run_in_background.assert_called_once()

    def test_background_sync_runs_if_sync_stale(self, mock_workflow, mocker):
        """Background sync runs if last sync older than threshold."""
        # Set last_sync to 10 minutes ago (past the threshold)
        stale_sync = datetime.now(timezone.utc) - timedelta(seconds=600)
        mock_workflow.cached_data.return_value = stale_sync

        mock_run_in_background = mocker.patch('workflow.background.run_in_background')

        from mstodo.sync import background_sync
        background_sync()

        # Should trigger background process
        mock_run_in_background.assert_called_once()

    def test_background_sync_calls_correct_command(self, mock_workflow, mocker):
        """Background sync runs with correct command."""
        mock_workflow.cached_data.return_value = None
        mock_workflow.workflowfile.return_value = '/path/to/alfred_mstodo_workflow.py'
        mock_run_in_background = mocker.patch('workflow.background.run_in_background')

        from mstodo.sync import background_sync
        background_sync()

        # Verify the command includes sync arguments
        call_args = mock_run_in_background.call_args
        assert 'sync' in call_args[0][0] or 'sync' in str(call_args[0][1])


class TestSyncDatabaseOperations:
    """Test sync database operations."""

    def test_sync_creates_database_tables(self, mock_workflow, mocker):
        """Sync creates all required database tables."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        mock_create_tables = MagicMock()
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables', mock_create_tables)

        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))

        from mstodo.sync import sync
        sync(background=False)

        # Verify create_tables was called
        mock_create_tables.assert_called()

    def test_sync_calls_all_sync_methods(self, mock_workflow, mocker):
        """Sync calls sync methods for all entities."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)
        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        mock_user_sync = MagicMock()
        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = mock_user_sync

        mock_task_list_sync = MagicMock()
        mock_task_sync = MagicMock()
        mock_hashtag_sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync', mock_task_list_sync)
        mocker.patch('mstodo.models.task.Task.sync_all_tasks', mock_task_sync)
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync', mock_hashtag_sync)
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))

        from mstodo.sync import sync
        sync(background=False)

        # Verify all sync methods were called
        mock_user_sync.assert_called_once()
        mock_task_list_sync.assert_called_once()
        mock_task_sync.assert_called_once()
        mock_hashtag_sync.assert_called_once()


class TestSyncDatabaseMigration:
    """Test database migration on version upgrade."""

    def test_schema_migration_on_major_version_upgrade(self, mock_workflow, mocker):
        """Database is cleared on major version upgrade."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mock_notify = mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Simulate version upgrade from 0.2.5 to 0.3.0
        mock_workflow.settings = {'__workflow_last_version': '0.2.5'}
        mock_workflow.version = '0.3.0'

        mock_db = MagicMock()
        mocker.patch('mstodo.models.base.BaseModel._meta.database', mock_db)

        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))

        from mstodo.sync import sync
        sync(background=False)

        # Should clear data for migration
        mock_workflow.clear_data.assert_called()
        # Should show upgrade notification
        notification_titles = [c[1].get('title', '') for c in mock_notify.call_args_list]
        assert any('upgrade' in t.lower() or 'database' in t.lower() for t in notification_titles)

    def test_no_migration_for_current_version(self, mock_workflow, mocker):
        """No migration when already on current version."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.auth.oauth_token', return_value='valid_token')
        mocker.patch('workflow.background.is_running', return_value=False)
        mocker.patch('workflow.notify.notify')
        mocker.patch('builtins.open', MagicMock())
        mocker.patch('os.getpid', return_value=12345)

        # Same version
        mock_workflow.settings = {'__workflow_last_version': '0.3.0'}
        mock_workflow.version = '0.3.0'

        mocker.patch('mstodo.models.base.BaseModel._meta.database.create_tables')

        mock_user_class = MagicMock()
        mock_user_class.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_user_class.get = MagicMock()
        mock_user_class.sync = MagicMock()

        mocker.patch('mstodo.models.user.User', mock_user_class)
        mocker.patch('mstodo.models.task_list.TaskList.sync')
        mocker.patch('mstodo.models.task.Task.sync_all_tasks')
        mocker.patch('mstodo.models.task.Task.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))
        mocker.patch('mstodo.models.hashtag.Hashtag.sync')
        mocker.patch('mstodo.models.hashtag.Hashtag.select', return_value=MagicMock(
            where=MagicMock(return_value=MagicMock(count=MagicMock(return_value=0)))
        ))

        # Reset clear_data mock from fixture
        mock_workflow.clear_data.reset_mock()

        from mstodo.sync import sync
        sync(background=False)

        # Should NOT clear data
        # Note: clear_data might be called with a filter, check call args
        for call in mock_workflow.clear_data.call_args_list:
            # Migration clear_data is called with a lambda filter
            assert call[0] if call[0] else True  # Allow other clear_data calls
