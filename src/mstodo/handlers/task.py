# encoding: utf-8

from datetime import date

from mstodo import icons
from mstodo.models.task import Task
from mstodo.models.task_parser import TaskParser
from mstodo.util import workflow

_star = u'★'
_recurrence = u'↻'
_reminder = u'⏰'

def _task(args):
    return TaskParser(' '.join(args))

def filter(args):
    task_id = args[1]
    wf = workflow()
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
            wf.add_item('Mark task not completed', subtitle, modifier_subtitles={
            }, arg=' '.join(args + ['toggle-completion']), valid=True, icon=icons.TASK_COMPLETED)
        else:
            wf.add_item('Complete this task', subtitle, modifier_subtitles={
                'alt': u'…and set due today    %s' % subtitle
            }, arg=' '.join(args + ['toggle-completion']), valid=True, icon=icons.TASK)

        wf.add_item('View in ToDo', 'View and edit this task in the ToDo app', arg=' '.join(args + ['view']), valid=True, icon=icons.OPEN)

        if task.recurrence_type and not task.status == 'completed':
            wf.add_item('Delete', 'Delete this task and cancel recurrence', arg=' '.join(args + ['delete']), valid=True, icon=icons.TRASH)
        else:
            wf.add_item('Delete', 'Delete this task', arg=' '.join(args + ['delete']), valid=True, icon=icons.TRASH)

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
            if res.status_code == 200:
                print('The task was marked incomplete')
            else:
                print('An unhandled error occurred')
        else:
            res = tasks.update_task(task.id, task.changeKey, completed=True, due_date=due_date)
            if res.status_code == 200:
                print('The task was marked complete')
            else:
                print('An unhandled error occurred')

    elif action == 'delete':
        res = tasks.delete_task(task.id, task.changeKey)
        if res.status_code == 204:
            print('The task was deleted')
        else:
            print('Please try again')

    elif action == 'view':
        import webbrowser

        webbrowser.open('ms-to-do://search/%s' % task.title)

    background_sync()
