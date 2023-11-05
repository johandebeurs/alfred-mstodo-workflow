import os
import re

from mstodo import icons
from mstodo.auth import is_authorised
from mstodo.sync import background_sync_if_necessary
from mstodo.util import wf_wrapper

COMMAND_PATTERN = re.compile(r'^[^\w\s]+', re.UNICODE)
ACTION_PATTERN = re.compile(r'^\W+', re.UNICODE)

def route(args):
    handler = None
    command = []
    command_string = ''
    action = 'none'
    logged_in = is_authorised()
    wf = wf_wrapper()

    # Read the stored query, which will correspond to the user's alfred query
    # as of the very latest keystroke. This may be different than the query
    # when this script was launched due to the startup latency.
    if args[0] == '--stored-query':
        query_file = wf.workflowfile('.query')
        with open(query_file, 'r') as fp:
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
    elif not logged_in:
        from mstodo.handlers import login
        handler = login
    elif 'folder'.find(action) == 0:
        from mstodo.handlers import taskfolder
        handler = taskfolder
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
                wf.add_item(
                    'An update is available!',
                    f"Update the ToDo workflow from version {wf.settings['__workflow_last_version']} \
to {wf.cached_data('__workflow_latest_version').get('version')}",
                    arg='-about update', valid=True, icon=icons.DOWNLOAD
                )
            handler.display(command)
            wf.send_feedback()

    if logged_in:
        background_sync_if_necessary()
