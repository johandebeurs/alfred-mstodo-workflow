# encoding: utf-8
"""
Tests for the task_list handler.
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items, assert_notify_called


class TestTaskListDisplay:
    """Test task_list handler display function."""

    def test_display_shows_new_list_prompt(self, mock_workflow, mocker):
        """Prompt to enter list name is shown."""
        from mstodo.handlers.task_list import display
        display(['list'])

        assert_item_added(mock_workflow, title='New list...')

    def test_display_shows_typed_name_in_subtitle(self, mock_workflow, mocker):
        """Typed name is shown in subtitle."""
        from mstodo.handlers.task_list import display
        display(['list', 'My', 'New', 'List'])

        items = get_added_items(mock_workflow)
        subtitles = [str(i.get('subtitle', '')) for i in items]
        assert any('My New List' in s for s in subtitles)

    def test_display_invalid_when_name_empty(self, mock_workflow, mocker):
        """Item is invalid when name is empty."""
        from mstodo.handlers.task_list import display
        display(['list'])

        items = get_added_items(mock_workflow)
        new_list_item = next((i for i in items if 'New list' in str(i.get('title', ''))), None)
        assert new_list_item is not None
        assert new_list_item.get('valid') is False

    def test_display_valid_when_name_provided(self, mock_workflow, mocker):
        """Item is valid when name is provided."""
        from mstodo.handlers.task_list import display
        display(['list', 'Shopping'])

        items = get_added_items(mock_workflow)
        new_list_item = next((i for i in items if 'New list' in str(i.get('title', ''))), None)
        assert new_list_item is not None
        assert new_list_item.get('valid') is True

    def test_display_shows_main_menu_option(self, mock_workflow, mocker):
        """Main menu option is shown."""
        from mstodo.handlers.task_list import display
        display(['list'])

        assert_item_added(mock_workflow, title='Main menu', autocomplete='')

    def test_display_has_stored_query_arg(self, mock_workflow, mocker):
        """New list item has stored-query arg."""
        from mstodo.handlers.task_list import display
        display(['list', 'Shopping'])

        items = get_added_items(mock_workflow)
        new_list_item = next((i for i in items if 'New list' in str(i.get('title', ''))), None)
        assert new_list_item is not None
        assert new_list_item.get('arg') == '--stored-query'


class TestTaskListCommit:
    """Test task_list handler commit function."""

    def test_commit_creates_list_via_api(self, mock_workflow, mocker):
        """Task list is created via API."""
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_create = mocker.patch('mstodo.api.task_lists.create_task_list', return_value=mock_response)

        from mstodo.handlers.task_list import commit
        commit(['list', 'My', 'List'])

        mock_create.assert_called_once_with('My List')

    def test_commit_shows_success_notification(self, mock_workflow, mocker):
        """Success notification is shown after creation."""
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.task_lists.create_task_list', return_value=mock_response)

        from mstodo.handlers.task_list import commit
        commit(['list', 'Shopping'])

        assert_notify_called(mock_notify, message='Shopping')

    def test_commit_logs_error_on_api_failure(self, mock_workflow, mocker):
        """Error is logged on API failure."""
        mocker.patch('mstodo.sync.background_sync')

        mock_response = MagicMock()
        mock_response.status_code = 401  # Must be > 400 to trigger error log
        mock_response.json.return_value = {'error': {'message': 'Unauthorized'}}
        mocker.patch('mstodo.api.task_lists.create_task_list', return_value=mock_response)

        mock_log = mocker.patch('mstodo.handlers.task_list.log')

        from mstodo.handlers.task_list import commit
        commit(['list', 'Shopping'])

        mock_log.error.assert_called()

    def test_commit_triggers_background_sync_on_success(self, mock_workflow, mocker):
        """Background sync is triggered on success."""
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mocker.patch('mstodo.api.task_lists.create_task_list', return_value=mock_response)

        from mstodo.handlers.task_list import commit
        commit(['list', 'Shopping'])

        mock_bg_sync.assert_called_once()

    def test_commit_handles_whitespace_in_name(self, mock_workflow, mocker):
        """Whitespace in list name is trimmed."""
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_create = mocker.patch('mstodo.api.task_lists.create_task_list', return_value=mock_response)

        from mstodo.handlers.task_list import commit
        commit(['list', '  My', 'List  '])

        # Should be trimmed
        mock_create.assert_called_once_with('My List')
