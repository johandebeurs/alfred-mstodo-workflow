# encoding: utf-8
"""
Tests for the about handler.
"""

from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added


class TestAboutDisplay:
    """Test about handler display function."""

    def test_display_shows_back_to_main_menu(self, mock_workflow, mocker):
        """Back to main menu option is shown."""
        from mstodo.handlers.about import display
        display(['about'])

        assert_item_added(mock_workflow, autocomplete='')


class TestAboutCommit:
    """Test about handler commit function."""

    def test_commit_update_starts_workflow_update(self, mock_workflow, mocker):
        """Update command triggers workflow update."""
        mock_workflow.start_update = MagicMock(return_value=True)
        mock_notify = mocker.patch('workflow.notify.notify')

        from mstodo.handlers.about import commit
        commit(['about', 'update'])

        mock_workflow.start_update.assert_called_once()

    def test_commit_changelog_opens_browser(self, mock_workflow, mocker):
        """Changelog command opens GitHub release page."""
        mock_workflow.version = '0.2.2'
        mock_webbrowser = mocker.patch('webbrowser.open')

        from mstodo.handlers.about import commit
        commit(['about', 'changelog'])

        mock_webbrowser.assert_called_once()
        url = mock_webbrowser.call_args[0][0]
        assert 'github.com' in url
        assert 'releases' in url
        assert '0.2.2' in url

    def test_commit_issues_opens_github_issues(self, mock_workflow, mocker):
        """Issues command opens GitHub issues page."""
        mock_webbrowser = mocker.patch('webbrowser.open')

        from mstodo.handlers.about import commit
        commit(['about', 'issues'])

        mock_webbrowser.assert_called_once()
        url = mock_webbrowser.call_args[0][0]
        assert 'github.com' in url
        assert 'issues' in url

    def test_commit_mstodo_opens_todo_app(self, mock_workflow, mocker):
        """MS ToDo command opens web app."""
        mock_webbrowser = mocker.patch('webbrowser.open')

        from mstodo.handlers.about import commit
        commit(['about', 'mstodo'])

        mock_webbrowser.assert_called_once()
        url = mock_webbrowser.call_args[0][0]
        assert 'todo.microsoft.com' in url
