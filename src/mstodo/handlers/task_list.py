import logging
from typing import List, Optional

from requests import codes
from workflow.notify import notify

from mstodo import icons
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)


def _task_list_name(args: List[str]) -> str:
    """Extract the task list name from command-line arguments.

    Args:
        args: List of command-line arguments. All elements after the
            first are joined to form the list name.

    Returns:
        The task list name as a trimmed string.
    """
    return ' '.join(args[1:]).strip()


def display(args: List[str]) -> None:
    """Display new task list creation interface.

    Shows a prompt for creating a new task list with the entered name.

    Args:
        args: List of command-line arguments from Alfred. Elements after
            the first form the task list name.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
    """
    wf = wf_wrapper()
    task_list_name = _task_list_name(args)
    subtitle = task_list_name if task_list_name else 'Type the name of the task list'

    wf.add_item('New list...', subtitle, arg='--stored-query',
                             valid=task_list_name != '', icon=icons.LIST_NEW)

    wf.add_item(
        'Main menu',
        autocomplete='', icon=icons.BACK
    )

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Create a new task list via the Microsoft ToDo API.

    Args:
        args: List of command-line arguments. Elements after the first
            form the task list name.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.

    Side effects:
        - Creates a task list via the Microsoft ToDo API.
        - Triggers background sync on success.
        - Sends notification about creation status.
        - Logs errors on failure.
    """
    from mstodo.api import task_lists
    from mstodo.sync import background_sync

    task_list_name = _task_list_name(args)

    req = task_lists.create_task_list(task_list_name)
    if req.status_code == codes.get('created'):
        notify(
            title='Task list updated',
            message=f"The list {task_list_name} was created"
        )
        background_sync()
    elif req.status_code > 400:
        log.error(str(req.json()['error']['message']))
    else:
        log.warning("Unknown API error. Please try again")
