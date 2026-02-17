# encoding: utf-8

from datetime import date
import logging
from typing import List, Optional

from requests import codes
from workflow.notify import notify

from mstodo import icons
from mstodo.models.task import Task
from mstodo.models.task_parser import TaskParser
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)


def _task(args: List[str]) -> TaskParser:
    """Parse command-line arguments into a TaskParser object.

    Args:
        args: List of command-line arguments representing task input.

    Returns:
        A TaskParser instance with the parsed task information.
    """
    return TaskParser(' '.join(args))


def display(args: List[str]) -> None:
    """Display task detail view with available actions.

    Shows task information and action options including:
    - Toggle completion status
    - View in ToDo app
    - Delete task

    Args:
        args: List of command-line arguments. Second element should be
            the task ID.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
    """
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

def commit(args: List[str], modifier: Optional[str] = None) -> None:
    """Execute task actions like completion toggle, delete, or view.

    Args:
        args: List of command-line arguments. Expected format:
            [command, task_id, action] where action is one of
            'toggle-completion', 'delete', or 'view'.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.
            If 'alt' with toggle-completion, also sets due date to today.

    Side effects:
        - Updates task status via Microsoft ToDo API.
        - May delete task via API.
        - May open task in ToDo app.
        - Triggers background sync.
        - Sends notifications about action results.
    """
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
            res = tasks.update_task(task.list.id, task.id, completed=False, due_date=due_date)
            if res.status_code == codes.get('ok'):
                notify(
                    title='Task updated',
                    message='The task was marked incomplete'
                )
            else:
                log.error(f"An unhandled error occurred when attempting to complete task {task.id}")
                #@TODO raise these as errors properly
        else:
            res = tasks.update_task(task.list.id, task.id, completed=True, due_date=due_date)
            if res.status_code == codes.get('ok'):
                notify(
                    title='Task updated',
                    message='The task was marked complete'
                )
            else:
                log.error(f"An unhandled error occurred when attempting to update task {task.id}")

    elif action == 'delete':
        res = tasks.delete_task(task.list.id, task.id)
        if res.status_code == codes.get('no_content'):
            notify(
                title='Task updated',
                message='The task was marked deleted'
            )
        else:
            log.error(f"An unhandled error occurred when attempting to update task {task.id}")

    elif action == 'view':
        import webbrowser
        webbrowser.open(f"ms-to-do://search/{task.title}")

    background_sync()
