# encoding: utf-8
"""
Tests for the welcome handler.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, assert_item_count


class TestWelcomeDisplay:
    """Test welcome handler display function."""

    def test_display_shows_new_task_option(self, mock_workflow, mocker):
        """New task option is displayed."""
        from mstodo.handlers.welcome import display
        display([])

        assert_item_added(mock_workflow, title='New task...', autocomplete=' ')

    def test_display_shows_preferences_option(self, mock_workflow, mocker):
        """Preferences option is displayed."""
        from mstodo.handlers.welcome import display
        display([])

        assert_item_added(mock_workflow, title='Preferences', autocomplete='-pref ')

    def test_display_shows_about_option(self, mock_workflow, mocker):
        """About option is displayed."""
        from mstodo.handlers.welcome import display
        display([])

        assert_item_added(mock_workflow, title='About', autocomplete='-about ')

    def test_display_shows_all_8_menu_items(self, mock_workflow, mocker):
        """All 8 main menu items are displayed."""
        from mstodo.handlers.welcome import display
        display([])

        assert_item_count(mock_workflow, 8)
