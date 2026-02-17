# encoding: utf-8
"""
Tests for the logout handler.
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_notify_called


class TestLogoutCommit:
    """Test logout handler commit function."""

    def test_commit_deauthorises_user(self, mock_workflow, mocker):
        """Logout removes authentication."""
        mock_deauthorise = mocker.patch('mstodo.auth.deauthorise')
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.logout import commit
        commit(['logout'])

        mock_deauthorise.assert_called_once()

    def test_commit_clears_workflow_data(self, mock_workflow, mocker):
        """All workflow data is cleared."""
        mocker.patch('mstodo.auth.deauthorise')
        mocker.patch('workflow.notify.notify')

        from mstodo.handlers.logout import commit
        commit(['logout'])

        mock_workflow.clear_data.assert_called_once()
        mock_workflow.clear_cache.assert_called_once()
