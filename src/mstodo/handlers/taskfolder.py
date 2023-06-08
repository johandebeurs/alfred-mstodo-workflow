import logging
from workflow.notify import notify
from requests import codes
from mstodo import icons
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

def _taskfolder_name(args):
    return ' '.join(args[1:]).strip()

def filter(args):
    wf = wf_wrapper()
    taskfolder_name = _taskfolder_name(args)
    subtitle = taskfolder_name if taskfolder_name else 'Type the name of the task folder'

    wf.add_item('New folder...', subtitle, arg='--stored-query',
                             valid=taskfolder_name != '', icon=icons.LIST_NEW)

    wf.add_item(
        'Main menu',
        autocomplete='', icon=icons.BACK
    )

def commit(args, modifier=None):
    from mstodo.api import taskfolders
    from mstodo.sync import background_sync

    taskfolder_name = _taskfolder_name(args)

    req = taskfolders.create_taskfolder(taskfolder_name)
    if req.status_code == codes.created:
        notify(
            title='Taskfolder updated',
            message=f"The folder {taskfolder_name} was created"
        )
        background_sync()
    elif req.status_code > 400:
        log.debug(str(req.json()['error']['message']))
    else:
        log.debug('Unknown API error. Please try again')