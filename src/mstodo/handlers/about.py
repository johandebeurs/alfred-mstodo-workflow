from workflow.notify import notify
from mstodo import icons, __version__, __githubslug__
from mstodo.util import wf_wrapper

wf = wf_wrapper()

def filter(args):
    wf.add_item(
        'New in this version',
        'Installed: ' + __version__ + '. See the changes from the previous version',
        arg='-about changelog', valid=True, icon=icons.INFO
    )

    wf.add_item(
        'Questions or concerns?',
        'See outstanding issues and report your own bugs or feedback',
        arg='-about issues', valid=True, icon=icons.HELP
    )

    wf.add_item(
        'Update workflow',
        'Check for updates to the workflow (automatically checked periodically)',
        arg='-about update', valid=True, icon=icons.DOWNLOAD
    )

    wf.add_item(
        'Main menu',
        autocomplete='', icon=icons.BACK
    )

def commit(args, modifier=None):
    if 'update' in args:
        if wf.start_update():
            notify(
                title='Workflow update',
                message='The workflow is being updated'
            )
        else:
            notify(
                title='Workflow update',
                message='You already have the latest workflow version'
            )
    else:
        import webbrowser

        if 'changelog' in args:
            webbrowser.open(f"https://github.com/{__githubslug__}/releases/tag/{__version__}")
        elif 'mstodo' in args:
            webbrowser.open('https://todo.microsoft.com/')
        elif 'issues' in args:
            webbrowser.open(f"https://github.com/{__githubslug__}/issues")
