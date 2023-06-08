# encoding: utf-8

import logging
from datetime import date

from workflow.notify import notify
from requests import codes
from mstodo import icons
from mstodo.models.task import Task
from mstodo.models.task_parser import TaskParser
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

_star = '★'
_recurrence = '↻'
_reminder = '⏰'

def _task(args):
    return TaskParser(' '.join(args))

def filter(args):
    task_id = args[1]
    wf = wf_wrapper()
    task = None

    try:
        task = Task.get(Task.id == task_id)
    except Task.DoesNotExist:
        pass

    if not task:
        wf.add_item('Unknown task', 'The ID does not match a task', autocomplete='', icon=icons.BACK)
    else:
        subtitle = task.subtitle()

        if task.status == 'completed':
            wf.add_item('Mark task not completed', subtitle, arg=' '.join(args + ['toggle-completion']),
                        valid=True, icon=icons.TASK_COMPLETED)
        else:
            wf.add_item('Complete this task', subtitle, arg=' '.join(args + ['toggle-completion']),
                        valid=True, icon=icons.TASK) \
                            .add_modifier(key='alt', subtitle=f"…and set due today    {subtitle}")

        wf.add_item('View in ToDo', 'View and edit this task in the ToDo app',
                    arg=' '.join(args + ['view']), valid=True, icon=icons.OPEN)

        if task.recurrence_type and not task.status == 'completed':
            wf.add_item('Delete', 'Delete this task and cancel recurrence',
                        arg=' '.join(args + ['delete']), valid=True, icon=icons.TRASH)
        else:
            wf.add_item('Delete', 'Delete this task', arg=' '.join(args + ['delete']),
                        valid=True, icon=icons.TRASH)

        wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

def commit(args, modifier=None):
    from mstodo.api import tasks
    from mstodo.sync import background_sync

    task_id = args[1]
    action = args[2]
    task = Task.get(Task.id == task_id)

    if action == 'toggle-completion':
        due_date = task.dueDateTime

        if modifier == 'alt':
            due_date = date.today()

        if task.status == 'completed':
            res = tasks.update_task(task.id, task.changeKey, completed=False, due_date=due_date)
            if res.status_code == codes.ok:
                notify(
                    title='Task updated',
                    message='The task was marked incomplete'
                )
            else:
                log.debug(f"An unhandled error occurred when attempting to complete task {task.id}")
                #@TODO raise these as errors properly
        else:
            res = tasks.update_task(task.id, task.changeKey, completed=True, due_date=due_date)
            if res.status_code == codes.ok:
                notify(
                    title='Task updated',
                    message='The task was marked complete'
                )
            else:
                log.debug(f"An unhandled error occurred when attempting to update task {task.id}")

    elif action == 'delete':
        res = tasks.delete_task(task.id, task.changeKey)
        if res.status_code == codes.no_content:
            notify(
                title='Task updated',
                message='The task was marked deleted'
            )
        else:
            log.debug(f"An unhandled error occurred when attempting to update task {task.id}")

    elif action == 'view':
        import webbrowser
        webbrowser.open(f"ms-to-do://search/{task.title}")

    background_sync()
