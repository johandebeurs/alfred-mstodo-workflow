import os
import re
from typing import List

from mstodo import icons
from mstodo.auth import is_authorised
from mstodo.sync import background_sync
from mstodo.util import wf_wrapper

COMMAND_PATTERN = re.compile(r'^[^\w\s]+', re.UNICODE)
ACTION_PATTERN = re.compile(r'^\W+', re.UNICODE)

def route(args: List[str]) -> None:
    """Route commands to appropriate handlers based on user input.

    This is the main routing function for the Alfred workflow. It parses
    command-line arguments and dispatches to the appropriate handler module.

    Args:
        args: List of command-line arguments from Alfred.

    Side effects:
        - Imports and executes handler modules
        - Sends Alfred feedback via workflow
        - Triggers background sync if user is logged in
    """
    handler = None
    command = []
    command_string = ''
    action = 'none'
    wf = wf_wrapper()

    # Read the stored query, which will correspond to the user's alfred query
    # as of the very latest keystroke. This may be different than the query
    # when this script was launched due to the startup latency.
    if args[0] == '--stored-query':
        query_file = wf.workflowfile('.query')
        with open(query_file, 'r', encoding='utf-8') as fp:
            command_string = wf.decode(fp.read())
        os.remove(query_file)
    # Otherwise take the command from the first command line argument
    elif args:
        command_string = args[0]

    command_string = re.sub(COMMAND_PATTERN, '', command_string)
    command = re.split(r' +', command_string)

    if command:
        action = re.sub(ACTION_PATTERN, '', command[0]) or 'none'

    if 'about'.find(action) == 0:
        from mstodo.handlers import about
        handler = about
    elif not is_authorised():
        from mstodo.handlers import login
        handler = login
    elif 'list'.find(action) == 0:
        from mstodo.handlers import task_list
        handler = task_list
    elif 'task'.find(action) == 0:
        from mstodo.handlers import task
        handler = task
    elif 'search'.find(action) == 0:
        from mstodo.handlers import search
        handler = search
    elif 'due'.find(action) == 0:
        from mstodo.handlers import due
        handler = due
    elif 'upcoming'.find(action) == 0:
        from mstodo.handlers import upcoming
        handler = upcoming
    elif 'completed'.find(action) == 0:
        from mstodo.handlers import completed
        handler = completed
    elif 'logout'.find(action) == 0:
        from mstodo.handlers import logout
        handler = logout
    elif 'pref'.find(action) == 0:
        from mstodo.handlers import preferences
        handler = preferences
    # If the command starts with a space (no special keywords), the workflow
    # creates a new task
    elif not command_string:
        from mstodo.handlers import welcome
        handler = welcome
    else:
        from mstodo.handlers import new_task
        handler = new_task

    if handler:
        if '--commit' in args:
            modifier = re.search(r'--(alt|cmd|ctrl|fn)\b', ' '.join(args))

            if modifier:
                modifier = modifier.group(1)

            handler.commit(command, modifier)
        else:
            if wf.update_available:
                from workflow import Workflow # required for dev compatibility with different working directories
                latest_version_data = Workflow().cached_data('__workflow_latest_version', max_age=0)
                latest_version = latest_version_data.get('version') if latest_version_data else 'unknown'
                current_version = wf.settings.get('__workflow_last_version', wf.version)
                wf.add_item(
                    'An update is available!',
                    f"Update the ToDo workflow from version {current_version} to {latest_version}",
                    arg='-about update', valid=True, icon=icons.DOWNLOAD
                )
            handler.display(command)
            wf.send_feedback()

    if is_authorised():
        background_sync()
