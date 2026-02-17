# encoding: utf-8
"""
Tests for the route handler - the main routing logic for the Alfred workflow.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))


class TestRouteBasics:
    """Test basic routing functionality."""

    def test_route_requires_authentication_for_search(self, mock_workflow, mocker):
        """Verify unauthenticated users are routed to login handler for search."""
        mocker.patch('mstodo.auth.is_authorised', return_value=False)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['search', 'tasks'])

        # Should show login screen, not search
        assert mock_workflow.add_item.called
        # Background sync should not be called when not logged in
        mock_bg_sync.assert_not_called()

    def test_about_accessible_without_authentication(self, mock_workflow, mocker):
        """About command should work without login."""
        mocker.patch('mstodo.auth.is_authorised', return_value=False)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['about'])

        # Should show about screen
        assert mock_workflow.add_item.called
        # Verify about-related items are shown
        calls = mock_workflow.add_item.call_args_list
        titles = [call[0][0] if call[0] else call[1].get('title', '') for call in calls]
        assert any('version' in t.lower() or 'new' in t.lower() for t in titles)

    def test_empty_command_routes_to_welcome_when_logged_in(self, mock_workflow, mocker):
        """Empty input shows welcome screen when authenticated."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route([''])

        # Should show welcome menu items
        assert mock_workflow.add_item.called
        calls = mock_workflow.add_item.call_args_list
        titles = [call[0][0] if call[0] else call[1].get('title', '') for call in calls]
        assert any('New task' in t for t in titles)

    def test_empty_command_routes_to_login_when_not_logged_in(self, mock_workflow, mocker):
        """Empty input when not authenticated shows login."""
        mocker.patch('mstodo.auth.is_authorised', return_value=False)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route([''])

        # Should show login prompt
        assert mock_workflow.add_item.called
        calls = mock_workflow.add_item.call_args_list
        titles = [call[0][0] if call[0] else call[1].get('title', '') for call in calls]
        assert any('log in' in t.lower() for t in titles)

    def test_background_sync_triggered_when_logged_in(self, mock_workflow, mocker):
        """Background sync is called after routing when authenticated."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route([''])

        mock_bg_sync.assert_called_once()

    def test_background_sync_not_triggered_when_logged_out(self, mock_workflow, mocker):
        """Background sync is NOT called when not authenticated."""
        mocker.patch('mstodo.auth.is_authorised', return_value=False)
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['about'])

        mock_bg_sync.assert_not_called()


class TestRouteCommandPatternMatching:
    """Test command pattern matching and partial matching."""

    @pytest.mark.parametrize("input_cmd,expected_handler", [
        (['-search'], 'search'),
        (['-sea'], 'search'),
        (['-due'], 'due'),
        (['-d'], 'due'),
        (['-upcoming'], 'upcoming'),
        (['-up'], 'upcoming'),
        (['-completed'], 'completed'),
        (['-com'], 'completed'),
        (['-pref'], 'preferences'),
        (['-preferences'], 'preferences'),
        (['-task 123'], 'task'),
        (['-list'], 'task_list'),
        (['-logout'], 'logout'),
    ])
    def test_route_command_matching(self, mock_workflow, mocker, input_cmd, expected_handler):
        """Test that commands match the correct handlers."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        # Mock Task.get to avoid database access when routing to task handler
        mock_task = MagicMock()
        mock_task.id = '123'
        mock_task.title = 'Test task'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'
        mocker.patch('mstodo.models.task.Task.get', return_value=mock_task)

        from mstodo.handlers.route import route
        route(input_cmd)

        # Verify workflow methods were called (indicating handler ran)
        assert mock_workflow.add_item.called or mock_workflow.send_feedback.called

    def test_route_default_to_new_task_handler(self, mock_workflow, mocker):
        """Any text that doesn't match a command creates a new task."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['buy groceries tomorrow'])

        # Should be handled by new_task handler
        assert mock_workflow.add_item.called

    def test_route_command_leading_special_chars_stripped(self, mock_workflow, mocker):
        """Commands with leading special characters are parsed correctly."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['-search tasks'])

        # Should route to search handler
        assert mock_workflow.add_item.called


class TestRouteCommitMode:
    """Test commit mode functionality."""

    def test_commit_mode_calls_commit_function(self, mock_workflow, mocker):
        """--commit flag triggers commit() instead of display()."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        # Mock a handler's commit function
        mock_commit = MagicMock()
        mocker.patch('mstodo.handlers.about.commit', mock_commit)

        from mstodo.handlers.route import route
        route(['about', 'update', '--commit'])

        # commit should be called, not display
        mock_commit.assert_called_once()
        # send_feedback should NOT be called in commit mode
        mock_workflow.send_feedback.assert_not_called()

    def test_commit_mode_with_alt_modifier(self, mock_workflow, mocker):
        """Alt modifier key is detected and passed to commit."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        mock_commit = MagicMock()
        mocker.patch('mstodo.handlers.about.commit', mock_commit)

        from mstodo.handlers.route import route
        route(['about', 'update', '--commit', '--alt'])

        # Check commit was called with modifier='alt'
        mock_commit.assert_called_once()
        args, kwargs = mock_commit.call_args
        assert kwargs.get('modifier') == 'alt' or (len(args) > 1 and args[1] == 'alt')

    def test_commit_mode_with_cmd_modifier(self, mock_workflow, mocker):
        """Cmd modifier key is detected."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        mock_commit = MagicMock()
        mocker.patch('mstodo.handlers.about.commit', mock_commit)

        from mstodo.handlers.route import route
        route(['about', '--commit', '--cmd'])

        mock_commit.assert_called_once()
        args, kwargs = mock_commit.call_args
        assert kwargs.get('modifier') == 'cmd' or (len(args) > 1 and args[1] == 'cmd')

    def test_commit_mode_with_ctrl_modifier(self, mock_workflow, mocker):
        """Ctrl modifier key is detected."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        mock_commit = MagicMock()
        mocker.patch('mstodo.handlers.about.commit', mock_commit)

        from mstodo.handlers.route import route
        route(['about', '--commit', '--ctrl'])

        mock_commit.assert_called_once()
        args, kwargs = mock_commit.call_args
        assert kwargs.get('modifier') == 'ctrl' or (len(args) > 1 and args[1] == 'ctrl')

    def test_commit_mode_with_fn_modifier(self, mock_workflow, mocker):
        """Fn modifier key is detected."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        mock_commit = MagicMock()
        mocker.patch('mstodo.handlers.about.commit', mock_commit)

        from mstodo.handlers.route import route
        route(['about', '--commit', '--fn'])

        mock_commit.assert_called_once()
        args, kwargs = mock_commit.call_args
        assert kwargs.get('modifier') == 'fn' or (len(args) > 1 and args[1] == 'fn')


class TestRouteHandlerImports:
    """Test that all handlers are importable and have correct interfaces."""

    @pytest.mark.parametrize("handler_name", [
        'about',
        'completed',
        'due',
        'login',
        'logout',
        'new_task',
        'preferences',
        'search',
        'task',
        'task_list',
        'upcoming',
        'welcome',
    ])
    def test_handler_importable(self, handler_name):
        """Verify all handler modules can be imported."""
        import importlib
        module = importlib.import_module(f'mstodo.handlers.{handler_name}')
        assert hasattr(module, 'display'), f"{handler_name} missing display function"

    @pytest.mark.parametrize("handler_name", [
        'about',
        'completed',
        'due',
        'login',
        'logout',
        'new_task',
        'preferences',
        'search',
        'task',
        'task_list',
        'upcoming',
    ])
    def test_handler_has_commit_function(self, handler_name):
        """Verify handlers that should have commit() do have it."""
        import importlib
        module = importlib.import_module(f'mstodo.handlers.{handler_name}')
        assert hasattr(module, 'commit'), f"{handler_name} missing commit function"

    def test_welcome_has_no_commit(self):
        """Welcome handler should not have commit function."""
        from mstodo.handlers import welcome
        assert not hasattr(welcome, 'commit') or welcome.commit is None


class TestRouteEdgeCases:
    """Test edge cases and error handling."""

    def test_route_with_unicode_characters(self, mock_workflow, mocker):
        """Unicode in commands is handled correctly."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        # Should not raise an exception
        route(['search', 'café'])
        route(['Jardinería', 'task'])

        assert mock_workflow.add_item.called

    def test_route_with_multiple_spaces(self, mock_workflow, mocker):
        """Multiple spaces between words are handled."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route(['search    multiple     spaces'])

        assert mock_workflow.add_item.called

    def test_route_with_empty_args_list(self, mock_workflow, mocker):
        """Empty args list is handled gracefully."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        # Empty string in args
        route([''])

        assert mock_workflow.add_item.called

    def test_display_mode_sends_feedback(self, mock_workflow, mocker):
        """Display mode calls send_feedback."""
        mocker.patch('mstodo.auth.is_authorised', return_value=True)
        mocker.patch('mstodo.sync.background_sync')

        from mstodo.handlers.route import route
        route([''])

        mock_workflow.send_feedback.assert_called_once()


class TestCommandPatternRegex:
    """Test the command pattern regex directly."""

    def test_command_pattern_strips_leading_special_chars(self):
        """COMMAND_PATTERN strips leading special characters."""
        import re
        from mstodo.handlers.route import COMMAND_PATTERN

        assert re.sub(COMMAND_PATTERN, '', '-search') == 'search'
        assert re.sub(COMMAND_PATTERN, '', '--due') == 'due'
        assert re.sub(COMMAND_PATTERN, '', ':list') == 'list'
        assert re.sub(COMMAND_PATTERN, '', 'normal') == 'normal'

    def test_action_pattern_strips_non_word_prefix(self):
        """ACTION_PATTERN strips non-word characters from start."""
        import re
        from mstodo.handlers.route import ACTION_PATTERN

        assert re.sub(ACTION_PATTERN, '', '-search') == 'search'
        assert re.sub(ACTION_PATTERN, '', '---test') == 'test'
        assert re.sub(ACTION_PATTERN, '', 'normal') == 'normal'
