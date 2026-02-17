# encoding: utf-8
"""
Tests for the due handler.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items


def _create_peewee_mock():
    """Create a mock that properly simulates Peewee's query interface."""
    mock_field = MagicMock()
    mock_field.__gt__ = MagicMock(return_value=MagicMock())
    mock_field.__lt__ = MagicMock(return_value=MagicMock())
    mock_field.__ge__ = MagicMock(return_value=MagicMock())
    mock_field.__le__ = MagicMock(return_value=MagicMock())
    mock_field.__eq__ = MagicMock(return_value=MagicMock())
    mock_field.__ne__ = MagicMock(return_value=MagicMock())
    mock_field.desc.return_value = MagicMock()
    mock_field.asc.return_value = MagicMock()
    mock_field.is_null.return_value = MagicMock()
    mock_field.contains.return_value = MagicMock()

    # Create a query mock that supports chaining (order_by returns itself)
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.__iter__ = lambda self: iter([])  # Makes it iterable (empty list)

    mock_task_class = MagicMock()
    mock_task_class.completedDateTime = mock_field
    mock_task_class.reminderDateTime = mock_field
    mock_task_class.dueDateTime = mock_field
    mock_task_class.lastModifiedDateTime = mock_field
    mock_task_class.list = mock_field
    mock_task_class.id = mock_field
    mock_task_class.title = mock_field
    mock_task_class.status = mock_field
    mock_task_class.select.return_value.join.return_value.where.return_value = mock_query

    mock_tasklist_class = MagicMock()
    mock_tasklist_class.title = mock_field
    mock_tasklist_class.id = mock_field

    return mock_task_class, mock_tasklist_class


class TestDueDisplay:
    """Test due handler display function."""

    def test_display_sort_submenu(self, mock_workflow, mocker, mock_preferences):
        """Sort submenu shows sort options."""

        mocker.patch('mstodo.handlers.due.Preferences.current_prefs', return_value=mock_preferences)

        from mstodo.handlers.due import display
        display(['due', 'sort'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show sort options
        assert any('overdue' in t.lower() for t in titles)
        # Should show hoist skipped option
        assert any('skipped' in t.lower() for t in titles)
        # Should show back option
        assert any('back' in t.lower() for t in titles)

    def test_display_shows_main_menu_option(self, mock_workflow, mocker, mock_preferences, monkeypatch):
        """Main menu option is shown."""
        from mstodo.handlers import due

        mock_task_class, mock_tasklist_class = _create_peewee_mock()
        monkeypatch.setattr(due, 'Task', mock_task_class)
        monkeypatch.setattr(due, 'TaskList', mock_tasklist_class)
        monkeypatch.setattr(due, 'background_sync', MagicMock())

        due.display(['due'])

        assert_item_added(mock_workflow, title='Main menu', autocomplete='')

class TestDueCommit:
    """Test due handler commit function."""

    def test_commit_changes_sort_order(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Selecting sort option updates preference."""
        mocker.patch('mstodo.handlers.due.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.due.relaunch_alfred', mock_relaunch_alfred)

        from mstodo.handlers.due import commit
        commit(['due', 'sort', '2'])

        # Verify due_order was updated
        assert mock_preferences.due_order is not None

    def test_commit_toggles_hoist_skipped_tasks(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """Toggle skipped tasks preference."""
        mocker.patch('mstodo.handlers.due.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.due.relaunch_alfred', mock_relaunch_alfred)
        original_value = mock_preferences.hoist_skipped_tasks

        from mstodo.handlers.due import commit
        commit(['due', 'sort', 'toggle-skipped'])

        assert mock_preferences.hoist_skipped_tasks != original_value

    def test_commit_relaunches_alfred(self, mock_workflow, mocker, mock_preferences, mock_relaunch_alfred):
        """After preference change, Alfred is relaunched."""
        mocker.patch('mstodo.handlers.due.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.due.relaunch_alfred', mock_relaunch_alfred)

        from mstodo.handlers.due import commit
        commit(['due', 'sort', '1'])

        mock_relaunch_alfred.assert_called()
