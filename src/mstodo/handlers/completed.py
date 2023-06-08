# encoding: utf-8

from datetime import date, timedelta

from peewee import JOIN, OperationalError

from mstodo import icons
from mstodo.models.preferences import Preferences
from mstodo.models.task import Task
from mstodo.models.taskfolder import TaskFolder
from mstodo.sync import background_sync, background_sync_if_necessary
from mstodo.util import relaunch_alfred, wf_wrapper

_hashtag_prompt_pattern = r'#\S*$'

_durations = [
    {
        'days': 1,
        'label': 'In the past 1 day',
        'subtitle': 'Show tasks that were completed in the past day'
    },
    {
        'days': 3,
        'label': 'In the past 3 days',
        'subtitle': 'Show tasks that were completed in the past 3 days'
    },
    {
        'days': 7,
        'label': 'In the past week',
        'subtitle': 'Show tasks that were completed in the past 7 days'
    },
    {
        'days': 14,
        'label': 'In the past 2 weeks',
        'subtitle': 'Show tasks that were completed in the past 14 days'
    },
    {
        'days': 30,
        'label': 'In the past month',
        'subtitle': 'Show tasks that were completed in the past 30 days'
    }
]


def _default_label(days):
    return f"In the past {days} day{'' if days == 1 else 's'}"


def _duration_info(days):
    duration_info = [d for d in _durations if d['days'] == days]

    if len(duration_info) > 0:
        return duration_info[0]
    else:
        return {
            'days': days,
            'label': _default_label(days),
            'subtitle': 'Your custom duration',
            'custom': True
        }


def filter(args):
    wf = wf_wrapper()
    prefs = Preferences.current_prefs()
    command = args[1] if len(args) > 1 else None
    duration_info = _duration_info(prefs.completed_duration)

    if command == 'duration':
        selected_duration = prefs.completed_duration

        # Apply selected duration option
        if len(args) > 2:
            try:
                selected_duration = int(args[2])
            except:
                pass

        duration_info = _duration_info(selected_duration)

        if 'custom' in duration_info:
            wf.add_item(duration_info['label'], duration_info['subtitle'],
                        arg=f"-completed duration {duration_info['days']}", valid=True,
                        icon=icons.RADIO_SELECTED if duration_info['days'] == selected_duration else icons.RADIO)

        for duration_info in _durations:
            wf.add_item(duration_info['label'], duration_info['subtitle'],
                        arg=f"-completed duration {duration_info['days']}", valid=True,
                        icon=icons.RADIO_SELECTED if duration_info['days'] == selected_duration else icons.RADIO)

        wf.add_item('Back', autocomplete='-completed ', icon=icons.BACK)

        return

    # Force a sync if not done recently or join if already running
    background_sync_if_necessary()

    wf.add_item(duration_info['label'], subtitle='Change the duration for completed tasks',
                autocomplete='-completed duration ', icon=icons.YESTERDAY)

    conditions = True

    # Build task title query based on the args
    for arg in args[1:]:
        if len(arg) > 1:
            conditions = conditions & (Task.title.contains(arg) | TaskFolder.title.contains(arg))

    if conditions is None:
        conditions = True

    tasks = Task.select().join(TaskFolder).where(
        (Task.completedDateTime > date.today() - timedelta(days=duration_info['days'])) &
        Task.list.is_null(False) &
        conditions
    )\
        .order_by(Task.completedDateTime.desc(), Task.reminderDateTime.asc(), Task.changeKey.asc())

    try:
        for task in tasks:
            wf.add_item(f"{task.list_title} – {task.title}", task.subtitle(), autocomplete=f"-task {task.id}",
                        icon=icons.TASK_COMPLETED if task.status == 'completed' else icons.TASK)
    except OperationalError:
        background_sync()

    wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

def commit(args, modifier=None):
    relaunch_command = None
    prefs = Preferences.current_prefs()
    action = args[1]

    if action == 'duration':
        relaunch_command = 'td-completed '
        prefs.completed_duration = int(args[2])

    if relaunch_command:
        relaunch_alfred(relaunch_command)
