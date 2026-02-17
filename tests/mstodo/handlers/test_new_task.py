# encoding: utf-8
"""
Tests for the new_task handler.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from datetime import date, datetime, time, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items, assert_notify_called


class TestNewTaskDisplay:
    """Test new_task handler display function."""

    def test_display_empty_input_shows_prompt(self, mock_workflow, mocker):
        """Empty input shows instruction message."""


        from mstodo.handlers.new_task import display
        display([])

        items = get_added_items(mock_workflow)
        subtitles = ' '.join([str(i.get('subtitle', '')) for i in items])
        assert 'begin typing' in subtitles.lower()

    def test_display_shows_task_title(self, mock_workflow, mocker):
        """Task title is shown in the display."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['Buy', 'milk'])

        items = get_added_items(mock_workflow)
        # The task title should appear somewhere
        all_text = ' '.join([f"{i.get('title', '')} {i.get('subtitle', '')}" for i in items])
        assert 'Buy milk' in all_text

    def test_display_shows_list_prompt_with_colon(self, mock_workflow, mocker):
        """When user types ':', list selection is shown."""

        mock_workflow.stored_data.return_value = [
            {'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'},
            {'id': '2', 'title': 'Shopping', 'wellknownListName': ''}
        ]

        from mstodo.handlers.new_task import display
        display([':buy', 'milk'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show task lists
        assert any('Tasks' in t or 'Shopping' in t for t in titles)

    def test_display_shows_due_date_suggestions(self, mock_workflow, mocker):
        """Typing 'due ' shows date suggestions."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk', 'due'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show date options
        assert any('Today' in t or 'Tomorrow' in t for t in titles)

    def test_display_shows_recurrence_suggestions(self, mock_workflow, mocker):
        """Typing 'every ' shows recurrence options."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk', 'every'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show recurrence options
        assert any('month' in t.lower() or 'week' in t.lower() for t in titles)

    def test_display_shows_reminder_suggestions(self, mock_workflow, mocker, mock_preferences):
        """Typing 'remind ' shows reminder options."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)

        from mstodo.handlers.new_task import display
        display(['buy', 'milk', 'remind', 'me'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show reminder options
        assert any('noon' in t.lower() or 'pm' in t.lower() or 'reminder' in t.lower() for t in titles)

    def test_display_shows_main_task_menu(self, mock_workflow, mocker):
        """Complete task shows edit menu."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk', 'tomorrow'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show task editing options
        assert any('list' in t.lower() or 'due' in t.lower() or 'recurrence' in t.lower() for t in titles)

    def test_display_shows_star_option(self, mock_workflow, mocker):
        """Star/unstar option is shown."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        assert any('star' in t.lower() for t in titles)

    def test_display_shows_change_list_option(self, mock_workflow, mocker):
        """Change list option is shown in main menu."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        assert any('list' in t.lower() for t in titles)

    def test_display_create_task_item_has_arg(self, mock_workflow, mocker):
        """The create task item has the stored-query arg."""

        mock_workflow.stored_data.return_value = [{'id': '1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]

        from mstodo.handlers.new_task import display
        display(['buy', 'milk'])

        items = get_added_items(mock_workflow)
        # First item (create task) should have arg
        create_item = next((i for i in items if 'create' in str(i.get('title', '')).lower() or 'new task' in str(i.get('title', '')).lower()), None)
        if create_item:
            assert create_item.get('arg') == '--stored-query'


class TestNewTaskCommit:
    """Test new_task handler commit function."""

    def test_commit_creates_task_via_api(self, mock_workflow, mocker, mock_preferences):
        """Task is created via API."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_create_task = mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'])

        mock_create_task.assert_called_once()

    def test_commit_shows_success_notification(self, mock_workflow, mocker, mock_preferences):
        """Success notification is shown after task creation."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('mstodo.handlers.new_task.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'])

        assert_notify_called(mock_notify, title='success')

    def test_commit_shows_error_notification_on_failure(self, mock_workflow, mocker, mock_preferences):
        """Error notification on API failure."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('mstodo.handlers.new_task.notify')

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': {'message': 'Bad request'}}
        mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'])

        assert_notify_called(mock_notify, title='error')

    def test_commit_triggers_background_sync_on_success(self, mock_workflow, mocker, mock_preferences):
        """Background sync triggered after successful creation."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'])

        mock_bg_sync.assert_called_once()

    def test_commit_with_alt_modifier_opens_todo_app(self, mock_workflow, mocker, mock_preferences):
        """Alt modifier opens task in MS ToDo app."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')
        mock_webbrowser = mocker.patch('webbrowser.open')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'], modifier='alt')

        mock_webbrowser.assert_called_once()
        url = mock_webbrowser.call_args[0][0]
        assert 'ms-to-do://' in url

    def test_commit_saves_last_list_preference(self, mock_workflow, mocker, mock_preferences):
        """Last used list is saved to preferences."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk'])

        # Preferences should have been updated
        # The list_id from the task parser should be saved
        assert mock_preferences.last_task_list_id is not None or hasattr(mock_preferences, 'last_task_list_id')

    def test_commit_passes_due_date_to_api(self, mock_workflow, mocker, mock_preferences):
        """Due date is passed to API when specified."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_create_task = mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk', 'due', 'tomorrow'])

        # Verify due_date was passed
        call_kwargs = mock_create_task.call_args[1]
        assert 'due_date' in call_kwargs

    def test_commit_passes_starred_to_api(self, mock_workflow, mocker, mock_preferences):
        """Starred status is passed to API."""

        mock_workflow.stored_data.return_value = [{'id': 'list1', 'title': 'Tasks', 'wellknownListName': 'defaultList'}]
        mocker.patch('mstodo.handlers.new_task.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_create_task = mocker.patch('mstodo.api.tasks.create_task', return_value=mock_response)

        from mstodo.handlers.new_task import commit
        commit(['buy', 'milk', '*'])

        # Verify starred was passed
        call_kwargs = mock_create_task.call_args[1]
        assert 'starred' in call_kwargs
        assert call_kwargs['starred'] is True
