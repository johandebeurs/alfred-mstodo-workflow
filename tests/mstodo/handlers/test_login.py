# encoding: utf-8
"""
Tests for the login handler.
"""

from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added


class TestLoginDisplay:
    """Test login handler display function."""

    def test_display_shows_login_prompt(self, mock_workflow, mocker):
        """Primary login option is displayed."""

        from mstodo.handlers.login import display
        display([])

        assert_item_added(mock_workflow, title='Please log in', valid=True)

    def test_display_shows_help_option_initially(self, mock_workflow, mocker):
        """'Having trouble?' option shown when not in help mode."""

        from mstodo.handlers.login import display
        display([])

        assert_item_added(mock_workflow, title='Having trouble?')

    def test_display_shows_about_option(self, mock_workflow, mocker):
        """About option available from login screen."""

        from mstodo.handlers.login import display
        display([])

        assert_item_added(mock_workflow, title='About')


class TestLoginCommit:
    """Test login handler commit function."""

    def test_commit_empty_triggers_auth(self, mock_workflow, mocker):
        """Committing with no args starts OAuth flow."""
        mock_authorise = mocker.patch('mstodo.auth.authorise', return_value=True)

        from mstodo.handlers.login import commit
        commit([])

        mock_authorise.assert_called_once()

    def test_commit_with_whitespace_triggers_auth(self, mock_workflow, mocker):
        """Committing with whitespace-only args starts OAuth flow."""
        mock_authorise = mocker.patch('mstodo.auth.authorise', return_value=True)

        from mstodo.handlers.login import commit
        commit(['  '])

        mock_authorise.assert_called_once()

    def test_commit_with_args_does_not_trigger_auth(self, mock_workflow, mocker):
        """Commit with non-empty args (like help) doesn't trigger auth."""
        mock_authorise = mocker.patch('mstodo.auth.authorise', return_value=True)

        from mstodo.handlers.login import commit
        commit(['help'])

        mock_authorise.assert_not_called()
