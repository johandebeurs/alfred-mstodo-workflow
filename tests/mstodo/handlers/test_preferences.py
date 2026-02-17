# encoding: utf-8
"""
Tests for the preferences handler.
"""

import pytest
from unittest.mock import MagicMock
from datetime import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items, assert_notify_called


class TestPreferencesDisplay:
    """Test preferences handler display function."""

    def test_display_shows_sign_out_option(self, mock_workflow, mocker, mock_preferences):
        """Sign out option is displayed."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks'}]

        # Mock User
        mock_user = MagicMock()
        mock_user.userPrincipalName = 'test@example.com'
        mock_user_class = MagicMock()
        mock_user_class.get.return_value = mock_user
        mock_user_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.preferences.User', mock_user_class)

        from mstodo.handlers.preferences import display
        display(['pref'])

        assert_item_added(mock_workflow, title='Sign out')

    def test_display_shows_show_completed_tasks_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Show completed tasks option is displayed."""
        mock_workflow.stored_data.return_value = []

        from mstodo.handlers import preferences

        # Mock User.get to raise exception (no user logged in scenario)
        mock_user_class = MagicMock()
        mock_user_class.get.side_effect = Exception()
        mock_user_class.DoesNotExist = Exception
        monkeypatch.setattr(preferences, 'User', mock_user_class)

        preferences.display(['pref'])

        assert_item_added(mock_workflow, title='Show completed tasks')

    def test_display_shows_default_reminder_time(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Default reminder time option is displayed."""
        mock_workflow.stored_data.return_value = []

        from mstodo.handlers import preferences

        mock_user_class = MagicMock()
        mock_user_class.get.side_effect = Exception()
        mock_user_class.DoesNotExist = Exception
        monkeypatch.setattr(preferences, 'User', mock_user_class)

        preferences.display(['pref'])

        assert_item_added(mock_workflow, title='Default reminder time')

    def test_display_shows_force_sync_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Force sync option is displayed."""
        mock_workflow.stored_data.return_value = []

        from mstodo.handlers import preferences

        mock_user_class = MagicMock()
        mock_user_class.get.side_effect = Exception()
        mock_user_class.DoesNotExist = Exception
        monkeypatch.setattr(preferences, 'User', mock_user_class)

        preferences.display(['pref'])

        assert_item_added(mock_workflow, title='Force sync')

    def test_display_shows_switch_theme_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Switch theme option is displayed."""
        mock_workflow.stored_data.return_value = []

        from mstodo.handlers import preferences

        mock_user_class = MagicMock()
        mock_user_class.get.side_effect = Exception()
        mock_user_class.DoesNotExist = Exception
        monkeypatch.setattr(preferences, 'User', mock_user_class)

        preferences.display(['pref'])

        assert_item_added(mock_workflow, title='Switch theme')

    def test_display_shows_main_menu_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Main menu option is shown."""
        mock_workflow.stored_data.return_value = []

        from mstodo.handlers import preferences

        mock_user_class = MagicMock()
        mock_user_class.get.side_effect = Exception()
        mock_user_class.DoesNotExist = Exception
        monkeypatch.setattr(preferences, 'User', mock_user_class)

        preferences.display(['pref'])

        assert_item_added(mock_workflow, title='Main menu', autocomplete='')

    def test_display_reminder_time_submenu(self, mock_workflow, mocker, mock_preferences):
        """Reminder time submenu shows time input."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)

        from mstodo.handlers.preferences import display
        display(['pref', 'reminder', '10:00'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        assert any('reminder time' in t.lower() for t in titles)

    def test_display_reminder_today_submenu(self, mock_workflow, mocker, mock_preferences):
        """Reminder today offset submenu shows options."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)

        from mstodo.handlers.preferences import display
        display(['pref', 'reminder_today'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show offset options
        assert any('30' in t or 'hour' in t.lower() for t in titles)

    def test_display_default_list_submenu(self, mock_workflow, mocker, mock_preferences):
        """Default list submenu shows available lists."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mock_workflow.stored_data.return_value = [
            {'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'},
            {'id': '2', 'title': 'Shopping', 'wellknownListName': ''}
        ]

        from mstodo.handlers.preferences import display
        display(['pref', 'default_list'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        assert 'Tasks' in titles or 'Shopping' in titles

    def test_display_shows_user_email(self, mock_workflow, mocker, mock_preferences):
        """Sign out shows current user email."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mock_workflow.stored_data.return_value = []

        mock_user = MagicMock()
        mock_user.userPrincipalName = 'test@example.com'
        mock_user_class = MagicMock()
        mock_user_class.get.return_value = mock_user
        mock_user_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.preferences.User', mock_user_class)

        from mstodo.handlers.preferences import display
        display(['pref'])

        items = get_added_items(mock_workflow)
        subtitles = ' '.join([str(i.get('subtitle', '')) for i in items])
        assert 'test@example.com' in subtitles


class TestPreferencesCommit:
    """Test preferences handler commit function."""

    def test_commit_toggle_show_completed_tasks(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle show_completed_tasks preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mock_notify = mocker.patch('workflow.notify.notify')

        original_value = mock_preferences.show_completed_tasks

        from mstodo.handlers.preferences import commit
        commit(['pref', 'show_completed_tasks'])

        assert mock_preferences.show_completed_tasks != original_value

    def test_commit_set_default_reminder_time(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Set default reminder time."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'reminder', '10:00'])

        assert mock_preferences.reminder_time == time(10, 0)

    def test_commit_set_reminder_today_offset(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Set reminder today offset."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'reminder_today', '2:00'])

        assert mock_preferences.reminder_today_offset == time(2, 0)

    def test_commit_disable_reminder_today_offset(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Disable reminder today offset."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'reminder_today', 'disabled'])

        assert mock_preferences.reminder_today_offset is None

    def test_commit_set_default_list(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Set default task list."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')
        mock_workflow.stored_data.return_value = [{'id': 'list123', 'title': 'Shopping'}]

        from mstodo.handlers.preferences import commit
        commit(['pref', 'default_list', 'list123'])

        assert mock_preferences.default_task_list_id == 'list123'

    def test_commit_toggle_explicit_keywords(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle explicit keywords preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        original_value = mock_preferences.explicit_keywords

        from mstodo.handlers.preferences import commit
        commit(['pref', 'explicit_keywords'])

        assert mock_preferences.explicit_keywords != original_value

    def test_commit_toggle_automatic_reminders(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle automatic reminders preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        original_value = mock_preferences.automatic_reminders

        from mstodo.handlers.preferences import commit
        commit(['pref', 'automatic_reminders'])

        assert mock_preferences.automatic_reminders != original_value

    def test_commit_switch_theme(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Switch theme preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')
        mocker.patch('mstodo.handlers.preferences.icons.icon_theme', return_value='dark')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'retheme'])

        assert mock_preferences.icon_theme == 'light'

    def test_commit_toggle_prerelease_channel(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle prerelease channel preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        original_value = mock_preferences.prerelease_channel

        from mstodo.handlers.preferences import commit
        commit(['pref', 'prerelease_channel'])

        assert mock_preferences.prerelease_channel != original_value

    def test_commit_force_sync(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Force sync triggers manual sync."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)

        mock_sync = mocker.patch('mstodo.sync.sync')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'sync'])

        mock_sync.assert_called_once_with(background=False)

    def test_commit_background_sync(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Background sync option triggers background sync."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)

        mock_sync = mocker.patch('mstodo.sync.sync')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'sync', 'background'])

        mock_sync.assert_called_once_with(background=True)

    def test_commit_shows_notifications(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred, monkeypatch):
        """Preference changes show notification."""
        from mstodo.handlers import preferences

        mock_notify = MagicMock()
        monkeypatch.setattr(preferences, 'notify', mock_notify)
        monkeypatch.setattr(preferences, 'relaunch_alfred', mock_relaunch_alfred)

        preferences.commit(['pref', 'show_completed_tasks'])

        assert_notify_called(mock_notify, title='Preferences changed')

    def test_commit_relaunches_alfred(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Most preference changes relaunch Alfred."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'show_completed_tasks'])

        mock_relaunch_alfred.assert_called()

    def test_commit_with_alfred_flag_relaunches_to_custom_command(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """--alfred flag allows custom relaunch command."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.preferences import commit
        commit(['pref', 'show_completed_tasks', '--alfred', '-search', 'milk'])

        mock_relaunch_alfred.assert_called()
        call_arg = mock_relaunch_alfred.call_args[0][0]
        assert 'search' in call_arg.lower()

    def test_commit_force_en_us_locale(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle en_US locale preference."""

        mocker.patch('mstodo.handlers.preferences.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.preferences.relaunch_alfred', mock_relaunch_alfred)
        mocker.patch('workflow.notify.notify')

        mock_preferences.date_locale = None

        from mstodo.handlers.preferences import commit
        commit(['pref', 'force_en_US'])

        assert mock_preferences.date_locale == 'en_US'
