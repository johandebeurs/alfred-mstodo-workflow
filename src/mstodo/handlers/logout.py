from typing import List, Optional

from workflow.notify import notify
from mstodo import auth, icons
from mstodo.util import wf_wrapper

wf = wf_wrapper()


def display(args: List[str]) -> None:
    """Display logout confirmation prompt.

    Shows a confirmation dialog before logging out of the Microsoft account.

    Args:
        args: List of command-line arguments from Alfred.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
    """
    wf.add_item(
        'Are you sure?',
        'You will need to log in to a Microsoft account to continue using the workflow',
        arg=' '.join(args),
        valid=True,
        icon=icons.CHECKMARK
    )

    wf.add_item(
        'Nevermind',
        autocomplete='',
        icon=icons.CANCEL
    )

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Execute logout action and clear all workflow data.

    Args:
        args: List of command-line arguments.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.

    Side effects:
        - Removes Microsoft authentication tokens.
        - Clears all workflow data and cache.
        - Sends notification confirming logout.
    """
    auth.deauthorise()
    wf.clear_data()
    wf.clear_cache()

    notify(title='Authentication', message='You are now logged out')
