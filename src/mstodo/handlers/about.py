from typing import List, Optional

from workflow.notify import notify
from mstodo import icons
from mstodo.util import wf_wrapper

wf = wf_wrapper()


def display(args: List[str]) -> None: # pylint: disable=W0613
    """Display the about menu with workflow information and support options.

    Shows menu items for viewing changelog, reporting issues, and checking
    for updates.

    Args:
        args: List of command-line arguments from Alfred.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
    """
    wf.add_item(
        'New in this version',
        'Installed: ' + str(wf.version) + '. See the changes from the previous version',
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

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Execute about-related actions.

    Handles workflow updates, opening changelog, Microsoft ToDo website,
    or issues page based on the provided arguments.

    Args:
        args: List of command-line arguments specifying the action.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.

    Side effects:
        - May start workflow update process.
        - May open URLs in the default web browser.
        - Sends notifications about update status.
    """
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

        url = wf.info.get('webaddress', '')
        github_slug = url.replace('https://github.com/', '') if url else 'johandebeurs/alfred-mstodo-workflow'

        if 'changelog' in args:
            webbrowser.open(f"https://github.com/{github_slug}/releases/tag/{str(wf.version)}")
        elif 'mstodo' in args:
            webbrowser.open('https://todo.microsoft.com/')
        elif 'issues' in args:
            webbrowser.open(f"https://github.com/{github_slug}/issues")
