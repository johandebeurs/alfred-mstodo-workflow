from mstodo import icons
from mstodo.util import workflow


def filter(args):
    workflow().add_item(
        'New in this version',
        'Installed: __VERSION__   See the changes from the previous version',
        arg='-about changelog', valid=True, icon=icons.INFO
    )

    workflow().add_item(
        'Questions or concerns?',
        'See outstanding issues and report your own bugs or feedback',
        arg='-about issues', valid=True, icon=icons.HELP
    )

    workflow().add_item(
        'Update workflow',
        'Check for updates to the workflow (automatically checked periodically)',
        arg='-about update', valid=True, icon=icons.DOWNLOAD
    )

    workflow().add_item(
        'Main menu',
        autocomplete='', icon=icons.BACK
    )

def commit(args, modifier=None):
    if 'update' in args:
        if workflow().start_update():
            print('The workflow is being updated')
        else:
            print('You already have the latest workflow version')
    else:
        import webbrowser

        if 'changelog' in args:
            webbrowser.open('https://github.com/johandebeurs/alfred-mstodo-workflow/releases/tag/__VERSION__')
        elif 'mstodo' in args:
            webbrowser.open('https://www.todo.microsoft.com/')
        elif 'issues' in args:
            webbrowser.open('https://github.com/johandebeurs/alfred-mstodo-workflow/issues')
