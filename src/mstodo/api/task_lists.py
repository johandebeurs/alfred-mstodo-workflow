import logging
import time
from typing import List, Dict, Any

import requests
from requests import codes

from mstodo import config
import mstodo.api.base as api

log = logging.getLogger(__name__)

def task_lists(order: str = 'display', task_counts: bool = False) -> List[Dict[str, Any]]:
    """Retrieve task lists using delta query for efficient synchronization.

    Args:
        order: Ordering preference (legacy parameter, ignored).
        task_counts: If True, include task counts for each list.

    Returns:
        List[Dict[str, Any]]: List of task list dictionaries (includes @removed items).
    """
    from mstodo.util import get_delta_token, set_delta_token
    import urllib.parse

    start = time.time()
    delta_token = get_delta_token('lists')

    # Build delta query URL
    if delta_token:
        next_link = "me/todo/lists/delta?$deltatoken=" + delta_token
    else:
        # next_link = "me/todo/lists?$top=" + config.MS_TODO_PAGE_SIZE
        next_link = "me/todo/lists/delta"

    task_lists = []
    new_delta_link = None

    while True:
        try:
            req = api.get(next_link)
            response = api.safe_json_decode(req, "lists")
        except (requests.RequestException, ValueError) as e:
            # Delta token expired or invalid - clear it and retry with full sync
            err_str = str(e).lower()
            if delta_token and ('token' in err_str or 'expired' in err_str or 'invalid' in err_str):
                log.warning("Delta token expired for lists, performing full sync")
                set_delta_token('lists', None)
                next_link = "me/todo/lists/delta?$top=" + config.MS_TODO_PAGE_SIZE
                delta_token = None
                req = api.get(next_link)
                response = api.safe_json_decode(req, "lists retry")
            else:
                raise

        # Collect all items (including @removed for deletion tracking)
        task_lists.extend(response.get('value', []))

        # Check for continuation
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
            set_delta_token('lists', params['$deltatoken'][0])
            log.debug("Stored new delta token for lists")

    log.debug(f"Retrieved {len(task_lists)} lists in {round(time.time() - start, 3)} seconds")

    if task_counts:
        for task_list in task_lists:
            if '@removed' not in task_list:
                update_task_list_with_tasks_count(task_list)

    return task_lists

def task_list(_id: str, task_counts: bool = False) -> Dict[str, Any]:
    """Retrieve a single task list by ID.

    Args:
        _id: Task list ID.
        task_counts: If True, include task counts in the result.

    Returns:
        Dict[str, Any]: Task list information dictionary.
    """
    req = api.get(f"me/todo/lists/{_id}")
    info = api.safe_json_decode(req, f"single list {_id}")

    #@TODO: run this request in parallel
    if task_counts:
        update_task_list_with_tasks_count(info)

    return info

def task_list_tasks_count(_id: str) -> Dict[str, int]:
    """Get task counts for a specific task list.

    Args:
        _id: Task list ID.

    Returns:
        Dict[str, int]: Dictionary with 'completed_count' and 'uncompleted_count'.
    """
    info = {}
    req = api.get(f"me/todo/lists/{_id}/tasks?$count=true&$top=1&$filter=status+ne+'completed'")
    response = api.safe_json_decode(req, f"uncompleted count for list {_id}")
    info['uncompleted_count'] = response.get('@odata.count', 0)

    req = api.get(f"me/todo/lists/{_id}/tasks?$count=true&$top=1&$filter=status+eq+'completed'")
    response = api.safe_json_decode(req, f"completed count for list {_id}")
    info['completed_count'] = response.get('@odata.count', 0)

    return info

def update_task_list_with_tasks_count(info: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task list dictionary with task counts.

    Args:
        info: Task list information dictionary to update.

    Returns:
        Dict[str, Any]: Updated task list dictionary with count fields.
    """
    counts = task_list_tasks_count(info['id'])

    info['completed_count'] = counts['completed_count'] if 'completed_count' in counts else 0
    info['uncompleted_count'] = counts['uncompleted_count'] if 'uncompleted_count' in counts else 0

    return info

def create_task_list(title: str) -> requests.Response:
    """Create a new task list in Microsoft ToDo.

    Args:
        title: Name/title of the task list to create.

    Returns:
        requests.Response: API response from list creation.
    """
    req = api.post('me/todo/lists', {'displayName': title})

    return req

def delete_task_list(_id: str) -> bool:
    """Delete a task list from Microsoft ToDo.

    Args:
        _id: Task list ID to delete.

    Returns:
        bool: True if deletion was successful (204 No Content), False otherwise.
    """
    req = api.delete('me/todo/lists/' + _id)

    return req.status_code == codes.get('no_content')
