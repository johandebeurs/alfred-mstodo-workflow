# @TODO check operation of this file and review e2e

from dateutil.tz import tzlocal
from datetime import timezone
from requests import codes

import mstodo.api.base as api
import mstodo.api.tasks as tasks

NO_CHANGE = '!nochange!'

def reminders(list_id=None, task_id=None, completed=False):
    data = {
        'completed': completed
    }
    if list_id:
        url = 'me/outlook/taskFolders/' + list_id + '/tasks' + '?$filter=status+eq+''completed''' if completed else ''
    elif task_id:
        url = 'me/outlook/tasks/' + task_id + '?$filter=status+eq+''completed''' if completed else ''
    req = api.get(url)
    reminders = req.json()

    return reminders

# def reminder(id):
#     req = api.get('reminders/' + id)
#     info = req.json()

#     return info

def create_reminder(task_id, date=None):
    date = date.replace(tzinfo=tzlocal())

    info = tasks.update_task(task_id,'',reminder_date=date)

    return info

# def update_reminder(id, revision, date=NO_CHANGE):
#     #@TODO refactor this to accept a taskID instead of a reminder id
#     if date != NO_CHANGE:
#         if date:
#             date = date.replace(tzinfo=tzlocal())
#             info = tasks.update_task(task_id,'',reminder_date=date)
#         else:
#             params['date'] = None

#     req = api.patch('reminders/' + id, params)
#     info = req.json()

#     return info

# def delete_task(id, revision):
#     req = api.delete('reminders/' + id, {'revision': revision})

#     return req.status_code == codes.no_content
