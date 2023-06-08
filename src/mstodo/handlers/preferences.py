# encoding: utf-8
from peewee import OperationalError

from workflow import MATCH_ALL, MATCH_ALLCHARS
from workflow.notify import notify

from mstodo import icons
from mstodo.models.preferences import Preferences, DEFAULT_TASKFOLDER_MOST_RECENT
from mstodo.models.user import User
from mstodo.util import format_time, parsedatetime_calendar, relaunch_alfred, user_locale, wf_wrapper

wf = wf_wrapper()

def _parse_time(phrase):
    from datetime import date, time

    cal = parsedatetime_calendar()

    # Use a sourceTime so that time expressions are relative to 00:00:00
    # rather than the current time
    datetime_info = cal.parse(phrase, sourceTime=date.today().timetuple())

    # Ensure that only a time was provided and not a date
    if datetime_info[1].hasTime:
        return time(*datetime_info[0][3:5])
    return None

def _format_time_offset(dt):
    if dt is None:
        return 'disabled'

    offset = []

    if dt.hour > 0:
        offset.append(f"{dt.hour}h")
    if dt.minute > 0:
        offset.append(f"{dt.minute}m")

    return ' '.join(offset)

def filter(args):
    prefs = Preferences.current_prefs()

    if 'reminder' in args:
        reminder_time = _parse_time(' '.join(args))

        if reminder_time is not None:
            wf.add_item(
                'Change default reminder time',
                f"⏰ {format_time(reminder_time, 'short')}",
                arg=' '.join(args), valid=True, icon=icons.REMINDER
            )
        else:
            wf.add_item(
                'Type a new reminder time',
                'Date offsets like the morning before the due date are not supported yet',
                valid=False, icon=icons.REMINDER
            )

        wf.add_item(
            'Cancel',
            autocomplete='-pref', icon=icons.BACK
        )
    elif 'reminder_today' in args:
        reminder_today_offset = _parse_time(' '.join(args))

        if reminder_today_offset is not None:
            wf.add_item(
                'Set a custom reminder offset',
                f"⏰ now + {_format_time_offset(reminder_today_offset)}",
                arg=' '.join(args), valid=True, icon=icons.REMINDER
            )
        else:
            wf.add_item(
                'Type a custom reminder offset',
                'Use the formats hh:mm or 2h 5m',
                valid=False, icon=icons.REMINDER
            )

        wf.add_item(
            '30 minutes',
            arg='-pref reminder_today 30m', valid=True, icon=icons.REMINDER
        )

        wf.add_item(
            '1 hour',
            '(default)',
            arg='-pref reminder_today 1h', valid=True, icon=icons.REMINDER
        )

        wf.add_item(
            '90 minutes',
            arg='-pref reminder_today 90m', valid=True, icon=icons.REMINDER
        )

        wf.add_item(
            'Always use the default reminder time',
            'Avoids adjusting the reminder based on the current date',
            arg='-pref reminder_today disabled', valid=True, icon=icons.CANCEL
        )

        wf.add_item(
            'Cancel',
            autocomplete='-pref', icon=icons.BACK
        )
    elif 'default_folder' in args:
        taskfolders = wf.stored_data('taskfolders')
        matching_taskfolders = taskfolders

        if len(args) > 2:
            taskfolder_query = ' '.join(args[2:])
            if taskfolder_query:
                matching_taskfolders = wf.filter(
                    taskfolder_query,
                    taskfolders,
                    lambda f: f['title'],
                    # Ignore MATCH_ALLCHARS which is expensive and inaccurate
                    match_on=MATCH_ALL ^ MATCH_ALLCHARS
                )

        for i, f in enumerate(matching_taskfolders):
            if i == 1:
                wf.add_item(
                    'Most recently used folder',
                    'Default to the last folder to which a task was added',
                    arg=f"-pref default_folder {DEFAULT_TASKFOLDER_MOST_RECENT}",
                    valid=True, icon=icons.RECURRENCE
                )
            icon = icons.INBOX if f['isDefaultFolder'] else icons.LIST
            wf.add_item(
                f['title'],
                arg=f"-pref default_folder {f['id']}",
                valid=True, icon=icon
            )

        wf.add_item(
            'Cancel',
            autocomplete='-pref', icon=icons.BACK
        )
    else:
        current_user = None
        taskfolders = wf.stored_data('taskfolders')
        loc = user_locale()
        default_folder_name = 'Tasks'

        try:
            current_user = User.get()
        except User.DoesNotExist:
            pass
        except OperationalError:
            from mstodo.sync import background_sync
            background_sync()

        if prefs.default_taskfolder_id == DEFAULT_TASKFOLDER_MOST_RECENT:
            default_folder_name = 'Most recent folder'
        else:
            default_taskfolder_id = prefs.default_taskfolder_id
            default_folder_name = next(
                (f['title'] for f in taskfolders if f['id'] == default_taskfolder_id),
                'Tasks'
            )

        if current_user and current_user.userPrincipalName:
            #@TODO double check this handling if the user schema changes on move to new APIs
            wf.add_item(
                'Sign out',
                f"You are logged in as {current_user.userPrincipalName}",
                autocomplete='-logout', icon=icons.CANCEL
            )

        wf.add_item(
            'Show completed tasks',
            'Includes completed tasks in search results',
            arg='-pref show_completed_tasks', valid=True,
            icon=icons.TASK_COMPLETED if prefs.show_completed_tasks else icons.TASK
        )

        wf.add_item(
            'Default reminder time',
            f"⏰ {format_time(prefs.reminder_time, 'short')}      Reminders without a specific time will be set to this time",
            autocomplete='-pref reminder ', icon=icons.REMINDER
        )

        wf.add_item(
            'Default reminder when due today',
            f"⏰ {_format_time_offset(prefs.reminder_today_offset)}      Default reminder time for tasks due today is \
{'relative to the current time' if prefs.reminder_today_offset else 'always %s' % format_time(prefs.reminder_time, 'short')}",
            autocomplete='-pref reminder_today ', icon=icons.REMINDER
        )

        wf.add_item(
            'Default folder',
            f"{default_folder_name}      Change the default folder when creating new tasks",
            autocomplete='-pref default_folder ', icon=icons.LIST
        )

        wf.add_item(
            'Automatically set a reminder on the due date',
            'Sets a default reminder for tasks with a due date.',
            arg='-pref automatic_reminders', valid=True,
            icon=icons.TASK_COMPLETED if prefs.automatic_reminders else icons.TASK
        )

        if loc != 'en_US' or prefs.date_locale:
            wf.add_item(
                'Force US English for dates',
                f"Rather than the current locale ({loc})",
                arg='-pref force_en_US', valid=True,
                icon=icons.TASK_COMPLETED if prefs.date_locale == 'en_US' else icons.TASK
            )

        wf.add_item(
            'Require explicit due keyword',
            'Requires the due keyword to avoid accidental due date extraction',
            arg='-pref explicit_keywords', valid=True,
            icon=icons.TASK_COMPLETED if prefs.explicit_keywords else icons.TASK
        )

        wf.add_item(
            'Check for experimental updates to this workflow',
            'The workflow automatically checks for updates; enable this to include pre-releases',
            arg=':pref prerelease_channel', valid=True,
            icon=icons.TASK_COMPLETED if prefs.prerelease_channel else icons.TASK
        )

        wf.add_item(
            'Force sync',
            'The workflow syncs automatically, but feel free to be forcible.',
            arg='-pref sync', valid=True, icon=icons.SYNC
        )

        wf.add_item(
            'Switch theme',
            'Toggle between light and dark icons',
            arg='-pref retheme',
            valid=True,
            icon=icons.PAINTBRUSH
        )

        wf.add_item(
            'Main menu',
            autocomplete='', icon=icons.BACK
        )

def commit(args, modifier=None):
    prefs = Preferences.current_prefs()
    relaunch_command = '-pref'
    if '--alfred' in args:
        relaunch_command = ' '.join(args[args.index('--alfred') + 1:])
    if 'sync' in args:
        from mstodo.sync import sync
        sync(background=('background' in args))
        relaunch_command = None
    elif 'show_completed_tasks' in args:
        prefs.show_completed_tasks = not prefs.show_completed_tasks

        if prefs.show_completed_tasks:
            notify(
                title='Preferences changed',
                message='Completed tasks are now visible in the workflow'
            )
        else:
            notify(
                title='Preferences changed',
                message='Completed tasks will not be visible in the workflow'
            )
    elif 'default_folder' in args:
        default_taskfolder_id = None
        taskfolders = wf.stored_data('taskfolders')
        if len(args) > 2:
            default_taskfolder_id = args[2]
        prefs.default_taskfolder_id = default_taskfolder_id
        if default_taskfolder_id:
            default_folder_name = next(
                (f['title'] for f in taskfolders if f['id'] == default_taskfolder_id),
                'most recent'
            )
            notify(
                title='Preferences changed',
                message=f"Tasks will be added to your {default_folder_name} folder by default"
            )
        else:
            notify(
                title='Preferences changed',
                message='Tasks will be added to the Tasks folder by default'
            )
    elif 'explicit_keywords' in args:
        prefs.explicit_keywords = not prefs.explicit_keywords
        if prefs.explicit_keywords:
            notify(
                title='Preferences changed',
                message='Remember to use the "due" keyword'
            )
        else:
            notify(
                title='Preferences changed',
                message='Implicit due dates enabled (e.g. "Recycling tomorrow")'
            )
    elif 'reminder' in args:
        reminder_time = _parse_time(' '.join(args))
        if reminder_time is not None:
            prefs.reminder_time = reminder_time
            notify(
                title='Preferences changed',
                message=f"Reminders will now default to {format_time(reminder_time, 'short')}"
            )
    elif 'reminder_today' in args:
        reminder_today_offset = None
        if not 'disabled' in args:
            reminder_today_offset = _parse_time(' '.join(args))
        prefs.reminder_today_offset = reminder_today_offset
        notify(
                title='Preferences changed',
                message=f"The offset for current-day reminders is now {_format_time_offset(reminder_today_offset)}"
            )
    elif 'automatic_reminders' in args:
        prefs.automatic_reminders = not prefs.automatic_reminders
        if prefs.automatic_reminders:
            notify(
                title='Preferences changed',
                message='A reminder will automatically be set for due tasks'
            )
        else:
            notify(
                title='Preferences changed',
                message='A reminder will not be added automatically'
            )
    elif 'retheme' in args:
        prefs.icon_theme = 'light' if icons.icon_theme() == 'dark' else 'dark'
        notify(
                title='Preferences changed',
                message=f"The workflow is now using the {prefs.icon_theme} icon theme"
            )
    elif 'prerelease_channel' in args:
        prefs.prerelease_channel = not prefs.prerelease_channel
        # Update the workflow settings and reverify the update data
        wf.check_update(True)
        if prefs.prerelease_channel:
            notify(
                title='Preferences changed',
                message='The workflow will prompt you to update to experimental pre-releases'
            )
        else:
            notify(
                title='Preferences changed',
                message='The workflow will only prompt you to update to final releases'
            )
    elif 'force_en_US' in args:
        if prefs.date_locale:
            prefs.date_locale = None
            notify(
                title='Preferences changed',
                message='The workflow will expect your local language and date format'
            )
        else:
            prefs.date_locale = 'en_US'
            notify(
                title='Preferences changed',
                message='The workflow will expect dates in US English'
            )

    if relaunch_command:
        relaunch_alfred(f"td{relaunch_command}")
