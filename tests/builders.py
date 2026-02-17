# encoding: utf-8
"""
Test data builders for the Alfred MS ToDo Workflow test suite.

This module provides builder pattern classes for creating test data objects
with sensible defaults that can be customized for specific test scenarios.
"""

from datetime import datetime, timezone, date, time, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class TaskBuilder:
    """Builder for creating test task data.

    Usage:
        task = TaskBuilder().with_title("Buy milk").with_due_date(1).build()
    """

    def __init__(self):
        self.data = {
            'id': 'test_task_1',
            'title': 'Test Task',
            'status': 'notStarted',
            'importance': 'normal',
            'list': 'list1',
            'dueDateTime': None,
            'reminderDateTime': None,
            'completedDateTime': None,
            'recurrence': None,
            'lastModifiedDateTime': datetime.now(timezone.utc).isoformat(),
            'createdDateTime': datetime.now(timezone.utc).isoformat(),
            'body': {'content': '', 'contentType': 'text'},
        }
        self._counter = 0

    def with_id(self, task_id: str) -> 'TaskBuilder':
        """Set the task ID."""
        self.data['id'] = task_id
        return self

    def with_title(self, title: str) -> 'TaskBuilder':
        """Set the task title."""
        self.data['title'] = title
        return self

    def with_status(self, status: str) -> 'TaskBuilder':
        """Set the task status (notStarted, inProgress, completed)."""
        self.data['status'] = status
        return self

    def with_list(self, list_id: str) -> 'TaskBuilder':
        """Set the task list ID."""
        self.data['list'] = list_id
        return self

    def with_due_date(self, days_from_now: int = 0) -> 'TaskBuilder':
        """Set due date as days from today."""
        due = date.today() + timedelta(days=days_from_now)
        self.data['dueDateTime'] = datetime.combine(
            due, time(0, 0, 0), tzinfo=timezone.utc
        ).isoformat()
        return self

    def with_due_datetime(self, dt: datetime) -> 'TaskBuilder':
        """Set due date as a specific datetime."""
        self.data['dueDateTime'] = dt.isoformat()
        return self

    def with_reminder(self, days_from_now: int = 0, hour: int = 9, minute: int = 0) -> 'TaskBuilder':
        """Set reminder date and time."""
        reminder_date = date.today() + timedelta(days=days_from_now)
        self.data['reminderDateTime'] = datetime.combine(
            reminder_date, time(hour, minute, 0), tzinfo=timezone.utc
        ).isoformat()
        return self

    def with_reminder_datetime(self, dt: datetime) -> 'TaskBuilder':
        """Set reminder as a specific datetime."""
        self.data['reminderDateTime'] = dt.isoformat()
        return self

    def completed(self) -> 'TaskBuilder':
        """Mark the task as completed."""
        self.data['status'] = 'completed'
        self.data['completedDateTime'] = datetime.now(timezone.utc).isoformat()
        return self

    def completed_days_ago(self, days: int) -> 'TaskBuilder':
        """Mark the task as completed N days ago."""
        self.data['status'] = 'completed'
        completed_date = datetime.now(timezone.utc) - timedelta(days=days)
        self.data['completedDateTime'] = completed_date.isoformat()
        return self

    def starred(self) -> 'TaskBuilder':
        """Mark the task as starred (high importance)."""
        self.data['importance'] = 'high'
        return self

    def with_recurrence(self, recurrence_type: str = 'daily', interval: int = 1) -> 'TaskBuilder':
        """Set recurrence pattern.

        Args:
            recurrence_type: One of 'daily', 'weekly', 'absoluteMonthly', 'absoluteYearly'
            interval: Recurrence interval
        """
        self.data['recurrence'] = {
            'pattern': {
                'type': recurrence_type,
                'interval': interval
            }
        }
        return self

    def with_note(self, note: str) -> 'TaskBuilder':
        """Set the task note/body."""
        self.data['body'] = {'content': note, 'contentType': 'text'}
        return self

    def overdue(self, days: int = 1) -> 'TaskBuilder':
        """Set the task as overdue by N days."""
        due = date.today() - timedelta(days=days)
        self.data['dueDateTime'] = datetime.combine(
            due, time(0, 0, 0), tzinfo=timezone.utc
        ).isoformat()
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the task dictionary."""
        return self.data.copy()

    def build_model_mock(self) -> MagicMock:
        """Build a mock Task model instance."""
        mock_task = MagicMock()
        for key, value in self.data.items():
            setattr(mock_task, key, value)

        # Add computed properties
        mock_task.list_title = 'Test List'
        mock_task.subtitle = MagicMock(return_value='Test subtitle')
        mock_task.overdue_times = 0

        # Parse dueDateTime if present
        if self.data['dueDateTime']:
            mock_task.dueDateTime = datetime.fromisoformat(
                self.data['dueDateTime'].replace('Z', '+00:00')
            )

        return mock_task


class TaskListBuilder:
    """Builder for creating test task list data."""

    def __init__(self):
        self.data = {
            'id': 'test_list_1',
            'title': 'Test List',
            'wellknownListName': '',
            'isOwner': True,
            'isShared': False,
        }

    def with_id(self, list_id: str) -> 'TaskListBuilder':
        """Set the list ID."""
        self.data['id'] = list_id
        return self

    def with_title(self, title: str) -> 'TaskListBuilder':
        """Set the list title."""
        self.data['title'] = title
        return self

    def as_default_list(self) -> 'TaskListBuilder':
        """Mark as the default Tasks list."""
        self.data['wellknownListName'] = 'defaultList'
        return self

    def as_flagged_emails(self) -> 'TaskListBuilder':
        """Mark as the flagged emails list."""
        self.data['wellknownListName'] = 'flaggedEmails'
        return self

    def shared(self) -> 'TaskListBuilder':
        """Mark as a shared list."""
        self.data['isShared'] = True
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the task list dictionary."""
        return self.data.copy()

    def build_model_mock(self) -> MagicMock:
        """Build a mock TaskList model instance."""
        mock_list = MagicMock()
        for key, value in self.data.items():
            setattr(mock_list, key, value)
        return mock_list


class UserBuilder:
    """Builder for creating test user data."""

    def __init__(self):
        self.data = {
            'id': 'test_user_1',
            'displayName': 'Test User',
            'userPrincipalName': 'test@example.com',
            'mail': 'test@example.com',
        }

    def with_id(self, user_id: str) -> 'UserBuilder':
        """Set the user ID."""
        self.data['id'] = user_id
        return self

    def with_name(self, name: str) -> 'UserBuilder':
        """Set the display name."""
        self.data['displayName'] = name
        return self

    def with_email(self, email: str) -> 'UserBuilder':
        """Set the email address."""
        self.data['userPrincipalName'] = email
        self.data['mail'] = email
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the user dictionary."""
        return self.data.copy()

    def build_model_mock(self) -> MagicMock:
        """Build a mock User model instance."""
        mock_user = MagicMock()
        for key, value in self.data.items():
            setattr(mock_user, key, value)
        return mock_user


class HashtagBuilder:
    """Builder for creating test hashtag data."""

    def __init__(self):
        self.data = {
            'id': '#test',
            'tag': '#test',
        }

    def with_tag(self, tag: str) -> 'HashtagBuilder':
        """Set the hashtag (with or without #)."""
        if not tag.startswith('#'):
            tag = f'#{tag}'
        self.data['id'] = tag.lower()
        self.data['tag'] = tag
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the hashtag dictionary."""
        return self.data.copy()

    def build_model_mock(self) -> MagicMock:
        """Build a mock Hashtag model instance."""
        mock_hashtag = MagicMock()
        for key, value in self.data.items():
            setattr(mock_hashtag, key, value)
        return mock_hashtag


class PreferencesBuilder:
    """Builder for creating test preferences."""

    def __init__(self):
        self.data = {
            'show_completed_tasks': False,
            'reminder_time': time(9, 0, 0),
            'reminder_today_offset': time(1, 0, 0),
            'default_task_list_id': None,
            'last_task_list_id': None,
            'automatic_reminders': False,
            'explicit_keywords': False,
            'prerelease_channel': False,
            'date_locale': None,
            'icon_theme': 'dark',
            'due_order': ['order', 'due_date', 'TaskList.id'],
            'hoist_skipped_tasks': False,
            'upcoming_duration': 7,
            'completed_duration': 7,
        }

    def show_completed(self, value: bool = True) -> 'PreferencesBuilder':
        """Set show_completed_tasks preference."""
        self.data['show_completed_tasks'] = value
        return self

    def with_reminder_time(self, hour: int, minute: int = 0) -> 'PreferencesBuilder':
        """Set default reminder time."""
        self.data['reminder_time'] = time(hour, minute, 0)
        return self

    def with_reminder_today_offset(self, hours: int = 1, minutes: int = 0) -> 'PreferencesBuilder':
        """Set reminder today offset."""
        self.data['reminder_today_offset'] = time(hours, minutes, 0)
        return self

    def disable_reminder_today_offset(self) -> 'PreferencesBuilder':
        """Disable reminder today offset."""
        self.data['reminder_today_offset'] = None
        return self

    def with_default_list(self, list_id: str) -> 'PreferencesBuilder':
        """Set default task list ID."""
        self.data['default_task_list_id'] = list_id
        return self

    def with_automatic_reminders(self, value: bool = True) -> 'PreferencesBuilder':
        """Enable automatic reminders."""
        self.data['automatic_reminders'] = value
        return self

    def with_explicit_keywords(self, value: bool = True) -> 'PreferencesBuilder':
        """Enable explicit keywords."""
        self.data['explicit_keywords'] = value
        return self

    def with_prerelease_channel(self, value: bool = True) -> 'PreferencesBuilder':
        """Enable prerelease channel."""
        self.data['prerelease_channel'] = value
        return self

    def with_locale(self, locale: str) -> 'PreferencesBuilder':
        """Set date locale."""
        self.data['date_locale'] = locale
        return self

    def with_light_theme(self) -> 'PreferencesBuilder':
        """Set light icon theme."""
        self.data['icon_theme'] = 'light'
        return self

    def hoist_skipped_tasks(self, value: bool = True) -> 'PreferencesBuilder':
        """Enable hoisting of skipped tasks."""
        self.data['hoist_skipped_tasks'] = value
        return self

    def with_upcoming_duration(self, days: int) -> 'PreferencesBuilder':
        """Set upcoming duration."""
        self.data['upcoming_duration'] = days
        return self

    def with_completed_duration(self, days: int) -> 'PreferencesBuilder':
        """Set completed duration."""
        self.data['completed_duration'] = days
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the preferences dictionary."""
        return self.data.copy()

    def build_mock(self) -> MagicMock:
        """Build a mock Preferences instance."""
        mock_prefs = MagicMock()
        for key, value in self.data.items():
            setattr(mock_prefs, key, value)
        return mock_prefs


# Convenience functions for creating multiple items

def create_task_lists(count: int = 3) -> List[Dict[str, Any]]:
    """Create a list of task list dictionaries.

    Args:
        count: Number of task lists to create

    Returns:
        List of task list dictionaries
    """
    lists = []
    for i in range(count):
        builder = TaskListBuilder().with_id(f'list{i+1}').with_title(f'List {i+1}')
        if i == 0:
            builder.as_default_list()
        lists.append(builder.build())
    return lists


def create_tasks(count: int = 5, list_id: str = 'list1') -> List[Dict[str, Any]]:
    """Create a list of task dictionaries.

    Args:
        count: Number of tasks to create
        list_id: List ID to assign to all tasks

    Returns:
        List of task dictionaries
    """
    tasks = []
    for i in range(count):
        task = (TaskBuilder()
                .with_id(f'task{i+1}')
                .with_title(f'Task {i+1}')
                .with_list(list_id)
                .build())
        tasks.append(task)
    return tasks


def create_due_tasks(overdue_count: int = 2, today_count: int = 2) -> List[Dict[str, Any]]:
    """Create a mix of overdue and due today tasks.

    Args:
        overdue_count: Number of overdue tasks
        today_count: Number of tasks due today

    Returns:
        List of task dictionaries
    """
    tasks = []

    for i in range(overdue_count):
        task = (TaskBuilder()
                .with_id(f'overdue_task{i+1}')
                .with_title(f'Overdue Task {i+1}')
                .overdue(days=i+1)
                .build())
        tasks.append(task)

    for i in range(today_count):
        task = (TaskBuilder()
                .with_id(f'today_task{i+1}')
                .with_title(f'Today Task {i+1}')
                .with_due_date(0)
                .build())
        tasks.append(task)

    return tasks


def create_completed_tasks(count: int = 3) -> List[Dict[str, Any]]:
    """Create completed tasks from recent days.

    Args:
        count: Number of completed tasks

    Returns:
        List of completed task dictionaries
    """
    tasks = []
    for i in range(count):
        task = (TaskBuilder()
                .with_id(f'completed_task{i+1}')
                .with_title(f'Completed Task {i+1}')
                .completed_days_ago(i)
                .build())
        tasks.append(task)
    return tasks
