# @TODO check operation of this file and handle secondary task attributes

import logging
import time

from requests import codes
from datetime import timezone

import mstodo.api.base as api
from mstodo.util import NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

NO_CHANGE = '!nochange!'

def tasks(list_id, completed=False, subtasks=False, positions=None):
    start = time.time()
    req = api.get('me/outlook/taskFolders/' + list_id + '/tasks?$filter=status+eq+' + '''completed''' if completed else '''notStarted''')
    #     ('subtasks' if subtasks else 'tasks'), {
    #     'list_id': int(list_id),
    #     'completed': completed
    # })
    tasks = []
    positions = []
    task_type = ''

    if completed:
        task_type += 'completed '
    if subtasks:
        task_type += 'sub'

    tasks = req.json()
    log.info('Retrieved %stasks for list %d in %s', task_type, list_id, time.time() - start)

    return tasks

# def task_positions(list_id):
#     start = time.time()
#     positions = []

#     from concurrent import futures

#     with futures.ThreadPoolExecutor(max_workers=2) as executor:
#         jobs = (
#             executor.submit(api.get, 'task_positions', {'list_id': list_id}),
#             executor.submit(api.get, 'subtask_positions', {'list_id': list_id})
#         )

#         for job in futures.as_completed(jobs):
#             req = job.result()
#             data = req.json()

#             if len(data) > 0:
#                 positions += data[0]['values']

#     log.info('Retrieved task positions for list %d in %s', list_id, time.time() - start)

#     return positions

def task(id):
    req = api.get('me/outlook/tasks/' + id)
    info = req.json()

    return info

def create_task(list_id, title, assignee_id=None, recurrence_type=None, recurrence_count=None, due_date=None, reminder_date=None, starred=False, completed=False, note=None):
    params = {
        'subject': title,
        'importance': 'high' if starred else 'normal',
        'status': 'completed' if completed else 'notStarted',
        'sensitivity': 'normal'
    }

    #@TODO maybe add these if required
    params_new = {
        "categories": ["String"],
        "isReminderOn": True,
        "recurrence": {
            "pattern": {
                "dayOfMonth": 1024,
                "daysOfWeek": ["sunday, monday, tuesday, wednesday, thursday, friday, saturday"],
                "firstDayOfWeek": "sunday, monday, tuesday, wednesday, thursday, friday, saturday",
                "index": "first, second, third, fourth, last",
                "interval": 1024,
                "month": 1024,
                "type": "daily, weekly, absoluteMonthly, relativeMonthly, absoluteYearly, relativeYearly"
                },
            "range": {
                "endDate": "String (timestamp)",
                "numberOfOccurrences": 1024,
                "recurrenceTimeZone": "string",
                "startDate": "String (timestamp)",
                "type": "endDate / noEnd / numbered"
                }
            },
        "reminderDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
        "startDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
    }

    if note:
        params['body'] = {
            'contentType':'text',
            'content': note
        }

    #@TODO check these and add back if needed
    # if assignee_id:
    #     params['assignedTo'] = int(assignee_id)

    # if recurrence_type and recurrence_count:
    #     params['recurrence_type'] = recurrence_type
    #     params['recurrence_count'] = int(recurrence_count)

    if due_date:
        #@TODO check if this needs date = date.replace(tzinfo=tzlocal()) for tz awareness
        params['dueDateTime'] = {
            "dateTime": due_date.astimezone(timezone.utc).isoformat(),
            "timeZone": "UTC"
        }
    
    if reminder_date:
        params['reminderDateTime'] = {
            "dateTime": reminder_date.astimezone(timezone.utc).isoformat(),
            "timeZone": "UTC"
        }

    req = api.post('me/outlook/taskFolders/' + list_id + '/tasks', params)
    info = req.json()

    return info

def update_task(id, revision, title=NO_CHANGE, assignee_id=NO_CHANGE, recurrence_type=NO_CHANGE, recurrence_count=NO_CHANGE, due_date=NO_CHANGE, reminder_date=NO_CHANGE, starred=NO_CHANGE, completed=NO_CHANGE):
    params = {}
    # remove = []
    changes = {
        'subject': title,
        # 'assignedTo': assignee_id,
        # 'recurrence_type': recurrence_type,
        # 'recurrence_count': recurrence_count,
        'due_date': due_date,
        'starred': starred,
        'completed': completed
    }

    for (key, value) in changes.items():
        if value is None:
            # remove.append(key)
            params[key] = None
        elif value != NO_CHANGE:
            params[key] = value

    if due_date:
        params['dueDateTime'] = {
            "dateTime": due_date.astimezone(timezone.utc).isoformat(),
            "timeZone": "UTC"
        }

    # if remove:
    #     params['remove'] = remove

    if params:
        req = api.patch('me/outlook/tasks/' + id, params)
        info = req.json()

        return info

    return None

def delete_task(id, revision):
    req = api.delete('me/outlook/tasks/' + id)

    return req.status_code == codes.no_content
