# encoding: utf-8
"""
Tests for the task handler.
"""

import pytest
from unittest.mock import MagicMock
from datetime import date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from tests.test_utils import assert_item_added, get_added_items, assert_notify_called


class TestTaskDisplay:
    """Test task handler display function."""

    def test_display_shows_toggle_completion_option(self, mock_workflow, mocker):
        """Option to complete task is shown for uncompleted task."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        assert_item_added(mock_workflow, title='Complete this task')

    def test_display_shows_uncomplete_option_for_completed_task(self, mock_workflow, mocker):
        """Option to uncomplete task is shown for completed task."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'completed'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        assert_item_added(mock_workflow, title='Mark task not completed')

    def test_display_shows_view_in_todo_option(self, mock_workflow, mocker):
        """View in ToDo option is shown."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        assert_item_added(mock_workflow, title='View in ToDo')

    def test_display_shows_delete_option(self, mock_workflow, mocker):
        """Delete option is shown."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        assert_item_added(mock_workflow, title='Delete')

    def test_display_shows_recurring_task_delete_warning(self, mock_workflow, mocker):
        """Delete for recurring task mentions canceling recurrence."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = 'daily'
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        items = get_added_items(mock_workflow)
        delete_item = next((i for i in items if i.get('title') == 'Delete'), None)
        assert delete_item is not None
        assert 'recurrence' in str(delete_item.get('subtitle', '')).lower()

    def test_display_shows_unknown_task_error(self, mock_workflow, mocker):
        """Unknown task shows error message."""
        mock_task_class = MagicMock()
        mock_task_class.DoesNotExist = Exception
        mock_task_class.get.side_effect = mock_task_class.DoesNotExist()
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'unknown_id'])

        assert_item_added(mock_workflow, title='Unknown task')

    def test_display_shows_main_menu_option(self, mock_workflow, mocker):
        """Main menu option is shown."""
        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.recurrence_type = None
        mock_task.subtitle.return_value = 'Test subtitle'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mock_task_class.DoesNotExist = Exception
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import display
        display(['task', 'task123'])

        assert_item_added(mock_workflow, title='Main menu', autocomplete='')


class TestTaskCommit:
    """Test task handler commit function."""

    def test_commit_toggle_completion_completes_task(self, mock_workflow, mocker):
        """Toggle completion marks task complete."""
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.dueDateTime = None
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_update_task = mocker.patch('mstodo.api.tasks.update_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'toggle-completion'])

        mock_update_task.assert_called_once()
        call_kwargs = mock_update_task.call_args[1]
        assert call_kwargs.get('completed') is True

    def test_commit_toggle_completion_uncompletes_task(self, mock_workflow, mocker):
        """Toggle completion marks completed task incomplete."""
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'completed'
        mock_task.dueDateTime = None
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_update_task = mocker.patch('mstodo.api.tasks.update_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'toggle-completion'])

        mock_update_task.assert_called_once()
        call_kwargs = mock_update_task.call_args[1]
        assert call_kwargs.get('completed') is False

    def test_commit_toggle_with_alt_sets_due_today(self, mock_workflow, mocker):
        """Alt modifier sets due date to today when completing."""
        mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.dueDateTime = None
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_update_task = mocker.patch('mstodo.api.tasks.update_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'toggle-completion'], modifier='alt')

        call_kwargs = mock_update_task.call_args[1]
        assert call_kwargs.get('due_date') == date.today()

    def test_commit_delete_task(self, mock_workflow, mocker):
        """Delete action deletes the task."""
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 204  # No content
        mock_delete_task = mocker.patch('mstodo.api.tasks.delete_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'delete'])

        mock_delete_task.assert_called_once()

    def test_commit_view_opens_todo_app(self, mock_workflow, mocker):
        """View action opens MS ToDo app."""
        mocker.patch('mstodo.sync.background_sync')
        mock_webbrowser = mocker.patch('webbrowser.open')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.title = 'Test Task'

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'view'])

        mock_webbrowser.assert_called_once()
        url = mock_webbrowser.call_args[0][0]
        assert 'ms-to-do://' in url

    def test_commit_triggers_background_sync(self, mock_workflow, mocker):
        """Commit triggers background sync."""
        mock_bg_sync = mocker.patch('mstodo.sync.background_sync')
        mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.dueDateTime = None
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mocker.patch('mstodo.api.tasks.update_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'toggle-completion'])

        mock_bg_sync.assert_called()

    def test_commit_shows_success_notification(self, mock_workflow, mocker):
        """Success notification is shown after update."""
        mocker.patch('mstodo.sync.background_sync')
        mock_notify = mocker.patch('workflow.notify.notify')

        mock_task = MagicMock()
        mock_task.id = 'task123'
        mock_task.status = 'notStarted'
        mock_task.dueDateTime = None
        mock_task.list = MagicMock(id='list1')

        mock_task_class = MagicMock()
        mock_task_class.get.return_value = mock_task
        mocker.patch('mstodo.handlers.task.Task', mock_task_class)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mocker.patch('mstodo.api.tasks.update_task', return_value=mock_response)

        from mstodo.handlers.task import commit
        commit(['task', 'task123', 'toggle-completion'])

        assert_notify_called(mock_notify, title='Task updated')
