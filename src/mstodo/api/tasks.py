import logging
import time
from dateutil import tz
import datetime

from requests import codes

import mstodo.api.base as api
from mstodo.util import NullHandler
from mstodo import config

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

def tasks_all(completed=None, since_datetime=None):
    start = time.time()
    log.info(since_datetime)
    query = '?$top='+config.MS_TODO_PAGE_SIZE+'&count=true'
    if (completed is not None or since_datetime is not None):
        query += '&$filter='
        if completed == True: 
            query += "status+eq+'completed'"
        elif completed == False: 
            query += "status+ne+'completed'"
        if completed is not None: 
            query += "&"
        if since_datetime is not None: 
            query += "lastModifiedDateTime+ge+" + since_datetime.isoformat()[:-4] + "Z"
    else:
        query += ''
    next_link = "me/outlook/tasks" + query
    tasks = []
    while True:
        req = api.get(next_link)
        tasks.extend(req.json()['value'])
        if '@odata.nextLink' in req.json():
            next_link= req.json()['@odata.nextLink'].replace(config.MS_TODO_API_BASE_URL + '/','')
        else:
            break
    
    log.info('Retrieved %d %stasks in %s', len(tasks), 'completed ' if completed else '', time.time() - start)

    return tasks

def tasks(taskfolder_id, completed=False, subtasks=False, positions=None):
    start = time.time()
    req = api.get(("me/outlook/taskFolders/" + taskfolder_id + "/tasks?$filter=status+") + ("eq" if completed else "ne") + "+'completed'")
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

    log.info(req.json())
    tasks = req.json()['value']
    log.info('Retrieved %stasks for folder %s in %s', task_type, taskfolder_id, time.time() - start)

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

def set_due_date(due_date):
    due_date = datetime.datetime.combine(due_date,datetime.time(0,0,0,1)) 
    # Microsoft ignores the time component of the API response so we don't do TZ conversion here
    return {
        'dueDateTime': {
            "dateTime": due_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    }

def set_reminder_date(reminder_date):
    reminder_date = reminder_date.replace(tzinfo=tz.gettz())
    return {
        'isReminderOn': True,
        'reminderDateTime': {
            "dateTime": reminder_date.astimezone(tz.tzutc()).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    }

def set_recurrence(recurrence_count, recurrence_type, due_date):
    recurrence = {'pattern':{},'range':{}}
    if recurrence_type == 'day': 
        recurrence_type = 'daily'
    elif recurrence_type == 'week': 
        recurrence_type = 'weekly'
        recurrence['pattern']['firstDayOfWeek'] = 'sunday'
        recurrence['pattern']['daysOfWeek'] = [due_date.strftime('%A')]
    elif recurrence_type == 'month': 
        recurrence_type = 'absoluteMonthly'
        recurrence['pattern']['dayOfMonth'] = due_date.strftime('%d')
    elif recurrence_type == 'year': 
        recurrence_type = 'absoluteYearly'
        recurrence['pattern']['dayOfMonth'] = due_date.strftime('%d')
        recurrence['pattern']['month'] = due_date.strftime('%m')
    recurrence['pattern']['interval'] = recurrence_count
    recurrence['pattern']['type'] = recurrence_type
    recurrence['range'] = {
        # "endDate": "String (timestamp)", only for endDate types
        # "numberOfOccurrences": 1024,
        # "recurrenceTimeZone": "string",
        'startDate': due_date.strftime('%Y-%m-%d'),
        'type': 'noEnd' # "endDate / noEnd / numbered"
    }
    return recurrence

def create_task(taskfolder_id, title, assignee_id=None, recurrence_type=None, recurrence_count=None, due_date=None, reminder_date=None, starred=False, completed=False, note=None):
    params = {
        'subject': title,
        'importance': 'high' if starred else 'normal',
        'status': 'completed' if completed else 'notStarted',
        'sensitivity': 'normal',
        'isReminderOn': False,
        'body': {
            'contentType':'text',
            'content': note if note else ''
        }
    }
    if due_date:
        due_date = datetime.datetime.combine(due_date,datetime.time(0,0,0,1)) 
        # Microsoft ignores the time component of the API response so we don't do TZ conversion here
        params['dueDateTime'] = {
            "dateTime": due_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    if reminder_date:
        reminder_date = reminder_date.replace(tzinfo=tz.gettz())
        params['isReminderOn'] = True
        params['reminderDateTime'] = {
            "dateTime": reminder_date.astimezone(tz.tzutc()).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    if (recurrence_count is not None and recurrence_type is not None):
        params['recurrence'] = {'pattern':{},'range':{}}
        if recurrence_type == 'day': 
            recurrence_type = 'daily'
        elif recurrence_type == 'week': 
            recurrence_type = 'weekly'
            params['recurrence']['pattern']['firstDayOfWeek'] = 'sunday'
            params['recurrence']['pattern']['daysOfWeek'] = [due_date.strftime('%A')]
        elif recurrence_type == 'month': 
            recurrence_type = 'absoluteMonthly'
            params['recurrence']['pattern']['dayOfMonth'] = due_date.strftime('%d')
        elif recurrence_type == 'year': 
            recurrence_type = 'absoluteYearly'
            params['recurrence']['pattern']['dayOfMonth'] = due_date.strftime('%d')
            params['recurrence']['pattern']['month'] = due_date.strftime('%m')
        params['recurrence']['pattern']['interval'] = recurrence_count
        params['recurrence']['pattern']['type'] = recurrence_type
        params['recurrence']['range'] = {
            # "endDate": "String (timestamp)", only for endDate types
            # "numberOfOccurrences": 1024,
            # "recurrenceTimeZone": "string",
            'startDate': due_date.strftime('%Y-%m-%d'),
            'type': 'noEnd' # "endDate / noEnd / numbered"
        }

    #@TODO maybe add these if required
    # params_new = {
    #     "categories": ["String"],
    #     "startDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
    # }

    #@TODO check these and add back if needed
    # if assignee_id:
    #     params['assignedTo'] = int(assignee_id)

    req = api.post('me/outlook/taskFolders/' + taskfolder_id + '/tasks', params)
    info = req.json()

    log.debug(req.status_code)

    return req

def update_task(id, revision, title=None, assignee_id=None, recurrence_type=None, recurrence_count=None, due_date=None, reminder_date=None, starred=None, completed=None):
    params = {}

    if completed is True:
        res = api.post('me/outlook/tasks/'+id+'/complete')
        return res
    elif completed is False:
        params['status'] = 'notStarted'
        params['completedDateTime'] = {}
    
    if title is not None:
        params['subject'] = title
    
    if starred is not None:
        if starred == True: params['importance'] = 'high'
        elif starred == False: params['importance'] = 'normal'

    if due_date is not None:
        params.update(set_due_date(due_date)) 

    if reminder_date is not None:
        params.update(set_reminder_date(reminder_date)) 
        
    #@TODO this requires all three to be set. Need to ensure due_date is pulled from task on calling this function
    if (recurrence_count is not None and recurrence_type is not None and due_date is not None):
        params.update(set_recurrence(recurrence_count, recurrence_type, due_date)) 

    #@TODO maybe add these if required
    # params_new = {
    #     "categories": ["String"],
    #     "startDateTime": {"@odata.type": "microsoft.graph.dateTimeTimeZone"},
    # }

    #@TODO check these and add back if needed
    # if assignee_id:
    #     params['assignedTo'] = int(assignee_id)
    # remove = []

    if params:
        res = api.patch('me/outlook/tasks/' + id, params)

        return res

    return None

def delete_task(id, revision):
    req = api.delete('me/outlook/tasks/' + id)

    return req.status_code == codes.no_content
