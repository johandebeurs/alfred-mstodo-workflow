# encoding: utf-8

from datetime import datetime, timedelta
import logging

from peewee import OperationalError

from mstodo import icons
from mstodo.models.taskfolder import TaskFolder
from mstodo.models.preferences import Preferences
from mstodo.models.task import Task
from mstodo.sync import background_sync, background_sync_if_necessary
from mstodo.util import relaunch_alfred, wf_wrapper

log = logging.getLogger('mstodo')

_due_orders = (
    {
        'due_order': ['order', 'due_date', 'TaskFolder.id'],
        'title': 'Most overdue within each folder',
        'subtitle': 'Sort tasks by increasing due date within folders (Default)'
    },
    {
        'due_order': ['order', '-due_date', 'TaskFolder.id'],
        'title': 'Most recently due within each folder',
        'subtitle': 'Sort tasks by decreasing due date within folders'
    },
    {
        'due_order': ['order', 'due_date'],
        'title': 'Most overdue at the top',
        'subtitle': 'All tasks sorted by increasing due date'
    },
    {
        'due_order': ['order', '-due_date'],
        'title': 'Most recently due at the top',
        'subtitle': 'All tasks sorted by decreasing due date'
    }
)


def display(args):
    wf = wf_wrapper()
    prefs = Preferences.current_prefs()
    command = args[1] if len(args) > 1 else None

    # Show sort options
    if command == 'sort':
        for i, order_info in enumerate(_due_orders):
            wf.add_item(order_info['title'], order_info['subtitle'], arg=f"-due sort {(i + 1)}", valid=True,
                        icon=icons.RADIO_SELECTED if order_info['due_order'] == prefs.due_order else icons.RADIO)

        wf.add_item('Highlight skipped recurring tasks',
                    'Hoists recurring tasks that have been missed multiple times over to the top',
                    arg='-due sort toggle-skipped', valid=True,
                    icon=icons.CHECKBOX_SELECTED if prefs.hoist_skipped_tasks else icons.CHECKBOX)

        wf.add_item('Back', autocomplete='-due ', icon=icons.BACK)

        return

    background_sync_if_necessary()
    conditions = True

    # Build task title query based on the args
    for arg in args[1:]:
        if len(arg) > 1:
            conditions = conditions & (Task.title.contains(arg) | TaskFolder.title.contains(arg))

    if conditions is None:
        conditions = True

    tasks = Task.select().join(TaskFolder).where(
        (Task.status != 'completed') &
        (Task.dueDateTime < datetime.now() + timedelta(days=1)) &
        Task.list.is_null(False) &
        conditions
    )

    # Sort the tasks according to user preference
    for key in prefs.due_order:
        order = 'asc'
        field = None
        if key[0] == '-':
            order = 'desc'
            key = key[1:]

        if key == 'due_date':
            field = Task.dueDateTime
        elif key == 'taskfolder.id':
            field = TaskFolder.id
        elif key == 'order':
            field = Task.lastModifiedDateTime

        if field:
            if order == 'asc':
                tasks = tasks.order_by(field.asc())
            else:
                tasks = tasks.order_by(field.desc())

    try:
        if prefs.hoist_skipped_tasks:
            log.debug('hoisting skipped tasks')
            tasks = sorted(tasks, key=lambda t: -t.overdue_times)

        for task in tasks:
            wf.add_item(
                f"{task.list_title} – {task.title}", task.subtitle(), autocomplete=f"-task {task.id} ",
                icon=icons.TASK_COMPLETED if task.status == 'completed' else icons.TASK
            )
    except OperationalError:
        background_sync()

    wf.add_item(
        'Sort order', 'Change the display order of due tasks',
        autocomplete='-due sort', icon=icons.SORT
    )

    wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

def commit(args, modifier=None):
    action = args[1]
    prefs = Preferences.current_prefs()
    relaunch_command = None

    if action == 'sort' and len(args) > 2:
        command = args[2]

        if command == 'toggle-skipped':
            prefs.hoist_skipped_tasks = not prefs.hoist_skipped_tasks
            relaunch_command = 'td-due sort'
        else:
            try:
                index = int(command)
                order_info = _due_orders[index - 1]
                prefs.due_order = order_info['due_order']
                relaunch_command = 'td-due '
            except IndexError:
                pass
            except ValueError:
                pass

    if relaunch_command:
        relaunch_alfred(relaunch_command)
