# encoding: utf-8

import re
from typing import List, Optional

from mstodo import auth, icons
from mstodo.util import wf_wrapper

ACTION_PATTERN = re.compile(r'^\W+', re.UNICODE)
wf = wf_wrapper()


def display(args: List[str]) -> None:
    """Display the login prompt and help options.

    Shows a login prompt for unauthenticated users, along with help options
    for troubleshooting authentication issues.

    Args:
        args: List of command-line arguments from Alfred. May include
            'help' to show troubleshooting options.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
    """
    getting_help = False

    if len(args) > 0:
        action = re.sub(ACTION_PATTERN, '', args[0])
        getting_help = action and 'help'.find(action) == 0

    if not getting_help:
        wf.add_item(
            'Please log in',
            'Authorise Alfred ToDo Workflow to use your Microsoft account',
            valid=True, icon=icons.ACCOUNT
        )

    if getting_help:
        wf.add_item(
            'I need to log in to a different account',
            'Go to microsoft.com in your browser and sign out of your account first',
            arg='-about mstodo', valid=True, icon=icons.ACCOUNT
        )
        wf.add_item(
            'Other issues?',
            'See outstanding issues and report your own bugs or feedback',
            arg='-about issues', valid=True, icon=icons.HELP
        )
    else:
        wf.add_item(
            'Having trouble?',
            autocomplete='-help ', valid=False, icon=icons.HELP
        )

    if not getting_help:
        wf.add_item(
            'About',
            'Learn about the workflow and get support',
            autocomplete='-about ',
            icon=icons.INFO
        )

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Execute login action to authorize with Microsoft.

    Args:
        args: List of command-line arguments.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.

    Side effects:
        - Initiates Microsoft OAuth authorization flow.
    """
    command = ' '.join(args).strip()

    if not command:
        auth.authorise()
