import datetime
import logging
import time
from typing import Optional, List, Dict, Any

from dateutil import tz
import requests

from mstodo import config
import mstodo.api.base as api

log = logging.getLogger(__name__)

def tasks(list_id: str) -> List[Dict[str, Any]]:
    """Retrieve tasks from a list using delta query for efficient synchronization.

    Args:
        list_id: Required task list ID.

    Returns:
        List[Dict[str, Any]]: List of task dictionaries (includes @removed items).
    """
    from mstodo.util import get_delta_token, set_delta_token
    import urllib.parse

    start = time.time()
    delta_key = f'tasks_{list_id}'
    delta_token = get_delta_token(delta_key)

    # Build delta query URL
    if delta_token:
        next_link = f"me/todo/lists/{list_id}/tasks/delta?$deltatoken={delta_token}"
    else:
        next_link = f"me/todo/lists/{list_id}/tasks/delta"

    task_data = []
    new_delta_link = None

    while True:
        try:
            req = api.get(next_link)
            response = api.safe_json_decode(req, f"tasks for list {list_id}")
        except (requests.RequestException, ValueError) as e:
            # Delta token expired or invalid - clear it and retry with full sync
            err_str = str(e).lower()
            if delta_token and ('token' in err_str or 'expired' in err_str or 'invalid' in err_str):
                log.warning(f"Delta token expired for list {list_id}, performing full sync")
                set_delta_token(delta_key, None)
                next_link = f"me/todo/lists/{list_id}/tasks/delta?$top={config.MS_TODO_PAGE_SIZE}"
                delta_token = None
                req = api.get(next_link)
                response = api.safe_json_decode(req, f"tasks delta retry for list {list_id}")
            else:
                raise

        # Process items - add list reference for database mapping
        for item in response.get('value', []):
            item['list'] = list_id
            task_data.append(item)

        # Handle pagination
        if '@odata.nextLink' in response:
            next_link = response['@odata.nextLink'].replace(f"{config.MS_TODO_API_BASE_URL}/", '')
        elif '@odata.deltaLink' in response:
            new_delta_link = response['@odata.deltaLink']
            break
        else:
            break

    # Store new delta token
    if new_delta_link:
        parsed = urllib.parse.urlparse(new_delta_link)
        params = urllib.parse.parse_qs(parsed.query)
        if '$deltatoken' in params:
            set_delta_token(delta_key, params['$deltatoken'][0])
            log.debug(f"Stored new delta token for list {list_id}")

    log.debug(f"Retrieved {len(task_data)} tasks in {round(time.time() - start, 3)} seconds")

    return task_data

def task(list_id: str, _id: str) -> Dict[str, Any]:
    """Retrieve a single task by ID.

    Args:
        list_id: The task list ID containing the task.
        _id: The task ID.

    Returns:
        Dict[str, Any]: Task information dictionary.
    """
    req = api.get(f'me/todo/lists/{list_id}/tasks/{_id}')
    info = api.safe_json_decode(req, f"single task {_id}")

    return info

def set_due_date(due_date: datetime.date) -> Dict[str, Any]:
    """Create a due date dictionary for Microsoft ToDo API.

    Args:
        due_date: The due date to set.

    Returns:
        Dict[str, Any]: Due date dictionary in API format.
    """
    due_date = datetime.datetime.combine(due_date, datetime.time(0, 0, 0, 1))
    # Microsoft ignores the time component of the API response so we don't do TZ conversion here
    return {
        'dueDateTime': {
            "dateTime": due_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    }

def set_reminder_date(reminder_date: datetime.datetime) -> Dict[str, Any]:
    """Create a reminder date dictionary for Microsoft ToDo API.

    Args:
        reminder_date: The reminder datetime to set.

    Returns:
        Dict[str, Any]: Reminder date dictionary in API format.
    """
    reminder_date = reminder_date.replace(tzinfo=tz.gettz())
    return {
        'isReminderOn': True,
        'reminderDateTime': {
            "dateTime": reminder_date.astimezone(tz.tzutc()) \
                .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
            "timeZone": "UTC"
        }
    }

def set_recurrence(recurrence_count: int, recurrence_type: str, due_date: datetime.date) -> Dict[str, Any]:
    """Create a recurrence pattern dictionary for Microsoft ToDo API.

    Args:
        recurrence_count: Interval between recurrences.
        recurrence_type: Type of recurrence ('day', 'week', 'month', 'year').
        due_date: The due date to base recurrence on.

    Returns:
        Dict[str, Any]: Recurrence pattern dictionary in API format.
    """
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

def create_task(list_id: str, title: str,
                recurrence_type: Optional[str] = None, recurrence_count: Optional[int] = None,
                due_date: Optional[datetime.date] = None, reminder_date: Optional[datetime.datetime] = None,
                starred: bool = False, completed: bool = False, note: Optional[str] = None) -> requests.Response:
    """Create a new task in Microsoft ToDo.

    Args:
        list_id: ID of the task list to create the task in.
        title: Title of the task.
        recurrence_type: Type of recurrence ('day', 'week', 'month', 'year').
        recurrence_count: Interval between recurrences.
        due_date: Optional due date.
        reminder_date: Optional reminder datetime.
        starred: Whether the task is starred/important.
        completed: Whether the task is completed.
        note: Optional note/body content.

    Returns:
        requests.Response: API response from task creation.
    """
    params = {
        'title': title,
        'importance': 'high' if starred else 'normal',
        'status': 'completed' if completed else 'notStarted',
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

    req = api.post(f"me/todo/lists/{list_id}/tasks", params)

    return req

def update_task(list_id: str, _id: str, title: Optional[str] = None,
                recurrence_type: Optional[str] = None, recurrence_count: Optional[int] = None,
                due_date: Optional[datetime.date] = None, reminder_date: Optional[datetime.datetime] = None,
                starred: Optional[bool] = None, completed: Optional[bool] = None) -> Optional[requests.Response]:
    """Update an existing task in Microsoft ToDo.

    Args:
        list_id: The task list ID containing the task.
        _id: Task ID to update.
        title: Optional new title.
        recurrence_type: Optional recurrence type ('day', 'week', 'month', 'year').
        recurrence_count: Optional interval between recurrences.
        due_date: Optional new due date.
        reminder_date: Optional new reminder datetime.
        starred: Optional starred/important status.
        completed: Optional completion status.

    Returns:
        Optional[requests.Response]: API response if updates were made, None otherwise.
    """
    params = {}

    if not completed is None:
        if completed:
            # v1.0 API doesn't have dedicated complete endpoint - use PATCH
            params['status'] = 'completed'
            # Set completedDateTime to current time in UTC
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            params['completedDateTime'] = {
                "dateTime": now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-4] + 'Z',
                "timeZone": "UTC"
            }
        else:
            params['status'] = 'notStarted'
            params['completedDateTime'] = None

    if title is not None:
        params['title'] = title

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

    if params:
        res = api.patch(f"me/todo/lists/{list_id}/tasks/{_id}", params)

        return res

    return None

def delete_task(list_id: str, _id: str) -> requests.Response:
    """Delete a task from Microsoft ToDo.

    Args:
        list_id: The task list ID containing the task.
        _id: Task ID to delete.

    Returns:
        requests.Response: API response from deletion.
    """
    res = api.delete(f"me/todo/lists/{list_id}/tasks/{_id}")

    return res
