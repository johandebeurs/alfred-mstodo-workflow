# encoding: utf-8
"""
Tests for the search handler.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items
from tests.builders import TaskBuilder, TaskListBuilder


class TestSearchDisplay:
    """Test search handler display function."""

    def test_display_filters_task_lists_by_query(self, mock_workflow, mocker, mock_preferences):
        """Typing filters task lists by name."""

        mocker.patch('mstodo.handlers.search.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.search.background_sync')

        # Create mock TaskList ORM objects (not dicts)
        mock_list_1 = MagicMock()
        mock_list_1.id = '1'
        mock_list_1.title = 'Tasks'
        mock_list_1.wellknownListName = 'defaultList'

        mock_list_2 = MagicMock()
        mock_list_2.id = '2'
        mock_list_2.title = 'Shopping'
        mock_list_2.wellknownListName = ''

        mock_task_list_class = MagicMock()
        mock_task_list_class.select.return_value = [mock_list_1, mock_list_2]
        mocker.patch('mstodo.handlers.search.TaskList', mock_task_list_class)

        # Mock Task model - needed because handler queries tasks after filtering list
        mock_task_class = MagicMock()
        mock_task_class.select.return_value.where.return_value.join.return_value.order_by.return_value.limit.return_value = []
        mocker.patch('mstodo.handlers.search.Task', mock_task_class)

        # Mock filter to return only Shopping (as ORM object)
        mock_workflow.filter.return_value = [mock_list_2]

        from mstodo.handlers.search import display
        display(['search', 'shop:'])

        # Filter should have been called
        mock_workflow.filter.assert_called()

    def test_display_list_colon_syntax(self, mock_workflow, mocker, mock_preferences):
        """'list: query' syntax filters by list then searches within."""

        mocker.patch('mstodo.handlers.search.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.search.background_sync')

        # Create mock TaskList ORM object (not dict)
        mock_list = MagicMock()
        mock_list.id = '1'
        mock_list.title = 'Shopping'
        mock_list.wellknownListName = ''

        mock_task_list_class = MagicMock()
        mock_task_list_class.select.return_value = [mock_list]
        mocker.patch('mstodo.handlers.search.TaskList', mock_task_list_class)

        # Mock filter to return the list (as ORM object)
        mock_workflow.filter.return_value = [mock_list]

        # Mock Task model
        mock_task_class = MagicMock()
        mock_task_class.select.return_value.where.return_value.join.return_value.order_by.return_value.limit.return_value = []
        mocker.patch('mstodo.handlers.search.Task', mock_task_class)

        from mstodo.handlers.search import display
        display(['search', 'Shopping:', 'milk'])

        # Should attempt to search tasks
        mock_task_class.select.assert_called()

    def test_display_hashtag_search(self, mock_workflow, mocker, mock_preferences):
        """Typing '#tag' shows hashtag suggestions."""

        mocker.patch('mstodo.handlers.search.Preferences.current_prefs', return_value=mock_preferences)
        mocker.patch('mstodo.handlers.search.background_sync')
        mock_workflow.stored_data.return_value = []

        # Mock Hashtag model
        mock_hashtag = MagicMock()
        mock_hashtag.tag = '#work'
        mock_hashtag.id = '#work'

        mock_hashtag_class = MagicMock()
        mock_hashtag_class.select.return_value.where.return_value.order_by.return_value = [mock_hashtag]
        mocker.patch('mstodo.handlers.search.Hashtag', mock_hashtag_class, create=True)
        mocker.patch('mstodo.models.hashtag.Hashtag', mock_hashtag_class)

        from mstodo.handlers.search import display
        display(['search', '#wor'])

        items = get_added_items(mock_workflow)
        titles = [i.get('title', '') for i in items]
        # Should show hashtag
        assert any('work' in t.lower() for t in titles)


class TestSearchCommit:
    """Test search handler commit function."""

    def test_commit_exists(self, mock_workflow, mocker):
        """Search handler has a commit function."""
        from mstodo.handlers.search import commit
        assert callable(commit)

    def test_commit_handles_action(self, mock_workflow, mocker, mock_preferences):
        """Commit handles the action argument."""


        from mstodo.handlers.search import commit
        # Should not raise an exception
        commit(['search', 'test'])
