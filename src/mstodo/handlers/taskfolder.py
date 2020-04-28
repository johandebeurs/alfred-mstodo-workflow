from mstodo import icons, util


def _taskfolder_name(args):
    return ' '.join(args[1:]).strip()

def filter(args):
    taskfolder_name = _taskfolder_name(args)
    subtitle = taskfolder_name if taskfolder_name else 'Type the name of the task folder'

    util.workflow().add_item('New folder...', subtitle, arg='--stored-query', valid=taskfolder_name != '', icon=icons.LIST_NEW)

    util.workflow().add_item(
        'Main menu',
        autocomplete='', icon=icons.BACK
    )

def commit(args, modifier=None):
    from mstodo.api import taskfolders
    from mstodo.sync import background_sync

    taskfolder_name = _taskfolder_name(args)

    req = taskfolders.create_taskFolder(taskfolder_name)
    if req.status_code == 201:
        print('The new task folder was created')
        background_sync()
    elif req.status_code > 400:
        print(str(req.json()['error']['message']))
    else:
        print('Unknown API error. Please try again')