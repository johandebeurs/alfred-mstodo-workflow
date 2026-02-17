# encoding: utf-8
"""
Tests for the completed handler.
"""

import pytest
from unittest.mock import MagicMock
from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items


def _create_peewee_mock():
    """Create a mock that properly simulates Peewee's query interface.

    Peewee fields support comparison operators that return Expression objects,
    so we need mocks that support __gt__, __lt__, etc.
    """
    mock_field = MagicMock()
    mock_field.__gt__ = MagicMock(return_value=MagicMock())
    mock_field.__lt__ = MagicMock(return_value=MagicMock())
    mock_field.__ge__ = MagicMock(return_value=MagicMock())
    mock_field.__le__ = MagicMock(return_value=MagicMock())
    mock_field.desc.return_value = MagicMock()
    mock_field.asc.return_value = MagicMock()
    mock_field.is_null.return_value = MagicMock()
    mock_field.contains.return_value = MagicMock()

    mock_task_class = MagicMock()
    mock_task_class.completedDateTime = mock_field
    mock_task_class.reminderDateTime = mock_field
    mock_task_class.dueDateTime = mock_field
    mock_task_class.list = mock_field
    mock_task_class.id = mock_field
    mock_task_class.title = mock_field
    mock_task_class.status = mock_field
    mock_task_class.select.return_value.join.return_value.where.return_value.order_by.return_value = []

    mock_tasklist_class = MagicMock()
    mock_tasklist_class.title = mock_field
    mock_tasklist_class.id = mock_field

    return mock_task_class, mock_tasklist_class


class TestCompletedDisplay:
    """Test completed handler display function."""

    def test_display_duration_submenu_shows_back(self, mock_workflow, mocker, mock_preferences):
        """Duration submenu has back option."""
        mock_preferences.completed_duration = 7
        mocker.patch('mstodo.handlers.completed.Preferences.current_prefs', return_value=mock_preferences)

        from mstodo.handlers.completed import display
        display(['completed', 'duration'])

        assert_item_added(mock_workflow, title='Back', autocomplete='-completed ')

    def test_display_shows_main_menu_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Main menu option is shown."""
        from mstodo.handlers import completed

        mock_task_class, mock_tasklist_class = _create_peewee_mock()
        monkeypatch.setattr(completed, 'Task', mock_task_class)
        monkeypatch.setattr(completed, 'TaskList', mock_tasklist_class)
        monkeypatch.setattr(completed, 'background_sync', MagicMock())

        completed.display(['due'])

        assert_item_added(mock_workflow, title='Main menu', autocomplete='')


class TestCompletedCommit:
    """Test completed handler commit function."""

    def test_commit_changes_duration(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Commit changes duration preference."""
        mocker.patch('mstodo.handlers.completed.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.completed.relaunch_alfred', mock_relaunch_alfred)

        from mstodo.handlers.completed import commit
        commit(['completed', 'duration', '14'])

        assert mock_preferences.completed_duration == 14

    def test_commit_relaunches_alfred(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """After preference change, Alfred is relaunched."""
        mocker.patch('mstodo.handlers.completed.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.completed.relaunch_alfred', mock_relaunch_alfred)

        from mstodo.handlers.completed import commit
        commit(['completed', 'duration', '3'])

        mock_relaunch_alfred.assert_called()
