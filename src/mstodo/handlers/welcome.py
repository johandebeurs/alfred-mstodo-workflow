from mstodo import icons
from mstodo.util import wf_wrapper

def filter(args):
    wf = wf_wrapper()
    wf.add_item(
        'New task...',
        'Begin typing to add a new task',
        autocomplete=' ',
        icon=icons.TASK_COMPLETED
    )

    wf.add_item(
        'Due today',
        'Due and overdue tasks',
        autocomplete='-due ',
        icon=icons.TODAY
    )

    wf.add_item(
        'Upcoming',
        'Tasks due soon',
        autocomplete='-upcoming ',
        icon=icons.UPCOMING
    )

    wf.add_item(
        'Completed',
        'Tasks recently completed',
        autocomplete='-completed ',
        icon=icons.YESTERDAY
    )

    wf.add_item(
        'Find and update tasks',
        'Search or browse by folder',
        autocomplete='-search ',
        icon=icons.SEARCH
    )

    wf.add_item(
        'New folder',
        autocomplete='-folder ',
        icon=icons.LIST_NEW
    )

    wf.add_item(
        'Preferences',
        autocomplete='-pref ',
        icon=icons.PREFERENCES
    )

    wf.add_item(
        'About',
        'Learn about the workflow and get support',
        autocomplete='-about ',
        icon=icons.INFO
    )
