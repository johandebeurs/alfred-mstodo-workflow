import logging
import time
import datetime
from dateutil import tz

from mstodo import config
import mstodo.api.base as api

log = logging.getLogger(__name__)

def _build_querystring(completed=None, dt=None, afterdt=True, fields=None):
    if fields is None:
        fields = []
    query = f"?$top={config.MS_TODO_PAGE_SIZE}&count=true&$select= \
        {''.join([field + ',' for field in fields])[:-1]}"
    if (completed is not None or dt is not None):
        query += '&$filter='
        if completed is True:
            query += "status+eq+'completed'"
        elif completed is False:
            query += "status+ne+'completed'"
        if completed is not None:
            query += "&"
        if dt is not None:
            query += f"lastModifiedDateTime+{'ge+' if afterdt else 'lt+'}{dt.isoformat()[:-4]}Z"
    else:
        query += ''
    return query

def tasks(taskfolder_id=None, completed=None, dt=None, afterdt=None, fields=None):
    if fields is None:
        fields = []
    if taskfolder_id is not None:
        root_uri = f"me/outlook/taskFolders/{taskfolder_id}/tasks"
    else:
        root_uri = "me/outlook/tasks"
    next_link = root_uri + _build_querystring(
        completed=completed,
        dt=dt,
        afterdt=afterdt,
        fields=fields
    )
    task_data = []
    while True:
        start_page = time.time()
        req = api.get(next_link)
        task_data.extend(req.json()['value'])
        log.debug(f"Retrieved {len(req.json()['value'])} {'modified ' if afterdt else ''}\
{'completed ' if completed else ''}tasks in {round(time.time() - start_page, 3)} seconds")
        if '@odata.nextLink' in req.json():
            next_link= req.json()['@odata.nextLink'].replace(f"{config.MS_TODO_API_BASE_URL}/",'')
        else:
            break

    return task_data

def task(_id):
    req = api.get('me/outlook/tasks/' + _id)
    info = req.json()

    return info

def set_due_date(due_date):
    due_date = datetime.datetime.combine(due_date, datetime.time(0, 0, 0, 1))
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
            "dateTime": reminder_date.astimezone(tz.tzutc()) \
                .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
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

def create_task(taskfolder_id, title, assignee_id=None, recurrence_type=None,
                recurrence_count=None, due_date=None, reminder_date=None,
                starred=False, completed=False, note=None):
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
            "dateTime": reminder_date.astimezone(tz.tzutc()) \
                .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
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

    req = api.post(f"me/outlook/taskFolders/{taskfolder_id}/tasks", params)
    log.debug(req.status_code)

    return req

def update_task(_id, revision, title=None, assignee_id=None, recurrence_type=None,
                recurrence_count=None, due_date=None, reminder_date=None, starred=None,
                completed=None):
    params = {}

    if not completed is None:
        if completed:
            res = api.post(f"me/outlook/tasks/{_id}/complete")
            return res
        else:
            params['status'] = 'notStarted'
            params['completedDateTime'] = {}

    if title is not None:
        params['subject'] = title

    if starred is not None:
        if starred is True:
            params['importance'] = 'high'
        elif starred is False:
            params['importance'] = 'normal'

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
        res = api.patch(f"me/outlook/tasks/{_id}", params)

        return res

    return None

def delete_task(_id, revision):
    res = api.delete(f"me/outlook/tasks/{_id}")

    return res
