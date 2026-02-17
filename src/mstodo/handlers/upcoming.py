# encoding: utf-8

from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

from peewee import OperationalError

from mstodo import icons
from mstodo.models.preferences import Preferences
from mstodo.models.task import Task
from mstodo.models.task_list import TaskList
from mstodo.sync import background_sync
from mstodo.util import relaunch_alfred, wf_wrapper

log = logging.getLogger(__name__)

_durations = [
    {
        'days': 7,
        'label': 'In the next week',
        'subtitle': 'Show tasks that are due in the next 7 days'
    },
    {
        'days': 14,
        'label': 'In the next 2 weeks',
        'subtitle': 'Show tasks that are due in the next 14 days'
    },
    {
        'days': 30,
        'label': 'In the next month',
        'subtitle': 'Show tasks that are due in the next 30 days'
    },
    {
        'days': 90,
        'label': 'In the next 3 months',
        'subtitle': 'Show tasks that are due in the next 90 days'
    }
]


def _default_label(days: int) -> str:
    """Generate a default label for a custom duration.

    Args:
        days: Number of days for the duration.

    Returns:
        A formatted string like "In the next 7 days".
    """
    return f"In the next {days} day{'' if days == 1 else 's'}"


def _duration_info(days: int) -> Dict:
    """Get duration information for the specified number of days.

    Looks up predefined duration options, or creates a custom one if
    no predefined option matches.

    Args:
        days: Number of days for the duration.

    Returns:
        A dictionary containing 'days', 'label', 'subtitle', and optionally 'custom'.
    """
    duration_info = [d for d in _durations if d['days'] == days]

    if len(duration_info) > 0:
        return duration_info[0]
    return {
        'days': days,
        'label': _default_label(days),
        'subtitle': 'Your custom duration',
        'custom': True
    }


def display(args: List[str]) -> None:
    """Display upcoming tasks and duration options.

    Shows tasks due within the configured upcoming duration period
    (excluding today). Can also display duration selection menu when
    'duration' subcommand is used.

    Args:
        args: List of command-line arguments from Alfred. May include
            'duration' subcommand and optional search terms.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
        - Triggers background sync.
        - May trigger additional sync if database error occurs.
    """
    wf = wf_wrapper()
    prefs = Preferences.current_prefs()
    command = args[1] if len(args) > 1 else None
    duration_info = _duration_info(prefs.upcoming_duration)

    if command == 'duration':
        selected_duration = prefs.upcoming_duration

        # Apply selected duration option
        if len(args) > 2:
            try:
                selected_duration = int(args[2])
            except ValueError:
                pass

        duration_info = _duration_info(selected_duration)

        if 'custom' in duration_info:
            wf.add_item(duration_info['label'], duration_info['subtitle'],
                        arg=f"-upcoming duration {duration_info['days']}", valid=True,
                        icon=icons.RADIO_SELECTED if duration_info['days'] == selected_duration else icons.RADIO
            )

        for duration_info in _durations:
            wf.add_item(duration_info['label'], duration_info['subtitle'],
                        arg=f"-upcoming duration {duration_info['days']}", valid=True,
                        icon=icons.RADIO_SELECTED if duration_info['days'] == selected_duration else icons.RADIO)

        wf.add_item('Back', autocomplete='-upcoming ', icon=icons.BACK)

        return

    # Force a sync if not done recently or join if already running
    background_sync()

    wf.add_item(duration_info['label'], subtitle='Change the duration for upcoming tasks',
                autocomplete='-upcoming duration ', icon=icons.UPCOMING)

    conditions = True

    # Build task title query based on the args
    for arg in args[1:]:
        if len(arg) > 1:
            conditions = conditions & (Task.title.contains(arg) | TaskList.title.contains(arg))

    if conditions is None:
        conditions = True

    tasks = Task.select().join(TaskList).where(
        (Task.status != 'completed') &
        (Task.dueDateTime < datetime.now() + timedelta(days=duration_info['days'] + 1)) &
        (Task.dueDateTime > datetime.now() + timedelta(days=1)) &
        Task.list.is_null(False) &
        conditions
    )\
        .order_by(Task.dueDateTime.asc(), Task.reminderDateTime.asc(), Task.lastModifiedDateTime.asc())

    try:
        for task in tasks:
            wf.add_item(f"{task.list_title} – {task.title}", task.subtitle(), autocomplete=f"-task {task.id} ",
                        icon=icons.TASK_COMPLETED if task.status == 'completed' else icons.TASK)
    except OperationalError:
        background_sync()

    wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Execute upcoming tasks actions, primarily duration changes.

    Args:
        args: List of command-line arguments. Expected format includes
            action type (e.g., 'duration') and value.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.

    Side effects:
        - Updates user preferences for upcoming task duration.
        - Relaunches Alfred with updated view.
    """
    relaunch_command = None
    prefs = Preferences.current_prefs()
    action = args[1]

    if action == 'duration':
        relaunch_command = 'td-upcoming '
        prefs.upcoming_duration = int(args[2])

    if relaunch_command:
        relaunch_alfred(relaunch_command)
