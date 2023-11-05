# encoding: utf-8

from random import random
from requests import codes
from peewee import fn
from workflow.background import is_running
from workflow.notify import notify

from mstodo import icons
from mstodo.models.preferences import Preferences
from mstodo.models.task_parser import TaskParser
from mstodo.util import format_time, short_relative_formatted_date, wf_wrapper, SYMBOLS

def _task(args):
    return TaskParser(' '.join(args))

def task_subtitle(task):
    subtitle = []

    if task.starred:
        subtitle.append(SYMBOLS['star'])

    if task.due_date:
        subtitle.append(f"Due {short_relative_formatted_date(task.due_date)}")

    if task.recurrence_type:
        if task.recurrence_count > 1:
            subtitle.append(f"{SYMBOLS['recurrence']} Every {task.recurrence_count} {task.recurrence_type}s")
        # Cannot simply add -ly suffix
        elif task.recurrence_type == 'day':
            subtitle.append(f"{SYMBOLS['recurrence']} Daily")
        else:
            subtitle.append(f"{SYMBOLS['recurrence']} {task.recurrence_type.title()}ly")

    if task.reminder_date:
        reminder_date_phrase = None
        if task.reminder_date.date() == task.due_date:
            reminder_date_phrase = 'On due date'
        else:
            reminder_date_phrase = short_relative_formatted_date(task.reminder_date)

        subtitle.append(f"{SYMBOLS['reminder']} {reminder_date_phrase} \
at {format_time(task.reminder_date.time(), 'short')}")

    subtitle.append(task.title)

    if task.note:
        subtitle.append(f"{SYMBOLS['note']} {task.note}")

    return '   '.join(subtitle)

def display(args):
    task = _task(args)
    subtitle = task_subtitle(task)
    wf = wf_wrapper()
    matching_hashtags = []

    if not task.title:
        subtitle = 'Begin typing to add a new task'

    # Preload matching hashtags into a list so that we can get the length
    if task.has_hashtag_prompt:
        from mstodo.models.hashtag import Hashtag

        hashtags = Hashtag.select().where(Hashtag.id.contains(task.hashtag_prompt.lower())) \
            .order_by(fn.Lower(Hashtag.tag).asc())

        for hashtag in hashtags:
            matching_hashtags.append(hashtag)

    # Show hashtag prompt if there is more than one matching hashtag or the
    # hashtag being typed does not exactly match the single matching hashtag
    if task.has_hashtag_prompt and len(matching_hashtags) > 0 and \
    (len(matching_hashtags) > 1 or task.hashtag_prompt != matching_hashtags[0].tag):
        for hashtag in matching_hashtags:
            wf.add_item(hashtag.tag[1:], '', autocomplete=' ' + task.phrase_with(hashtag=hashtag.tag) + ' ',
                        icon=icons.HASHTAG)

    elif task.has_list_prompt:
        taskfolders = wf.stored_data('taskfolders')
        if taskfolders:
            for taskfolder in taskfolders:
                # Show some full list names and some concatenated in command
                # suggestions
                sample_command = taskfolder['title']
                if random() > 0.5:
                    sample_command = sample_command[:int(len(sample_command) * .75)]
                icon = icons.INBOX if taskfolder['isDefaultFolder'] else icons.LIST
                wf.add_item(taskfolder['title'], f"Assign task to this folder, e.g. {sample_command.lower()}: {task.title}",
                             autocomplete=' ' + task.phrase_with(list_title=taskfolder['title']), icon=icon)
            wf.add_item('Remove folder', 'Tasks without a folder are added to the Inbox',
                        autocomplete=f" {task.phrase_with(list_title=False)}", icon=icons.CANCEL)
        elif is_running('sync'):
            wf.add_item('Your folders are being synchronized', 'Please try again in a few moments',
                        autocomplete=f" {task.phrase_with(list_title=False)}", icon=icons.BACK)

    # Task has an unfinished recurrence phrase
    elif task.has_recurrence_prompt:
        wf.add_item('Every month', 'Same day every month, e.g. every mo', uid="recurrence_1m",
                    autocomplete=f" {task.phrase_with(recurrence='every month')} ", icon=icons.RECURRENCE)
        wf.add_item('Every week', 'Same day every week, e.g. every week, every Tuesday', uid="recurrence_1w",
                    autocomplete=f" {task.phrase_with(recurrence='every week')} ", icon=icons.RECURRENCE)
        wf.add_item('Every year', 'Same date every year, e.g. every 1 y, every April 15', uid="recurrence_1y",
                    autocomplete=f" {task.phrase_with(recurrence='every year')} ", icon=icons.RECURRENCE)
        wf.add_item('Every 3 months', 'Same day every 3 months, e.g. every 3 months', uid="recurrence_3m",
                    autocomplete=f" {task.phrase_with(recurrence='every 3 months')} ", icon=icons.RECURRENCE)
        wf.add_item('Remove recurrence', autocomplete=' ' + task.phrase_with(recurrence=False), icon=icons.CANCEL)

    # Task has an unfinished due date phrase
    elif task.has_due_date_prompt:
        wf.add_item('Today', 'e.g. due today',
                    autocomplete=f" {task.phrase_with(due_date='due today')} ", icon=icons.TODAY)
        wf.add_item('Tomorrow', 'e.g. due tomorrow',
                    autocomplete=f" {task.phrase_with(due_date='due tomorrow')} ", icon=icons.TOMORROW)
        wf.add_item('Next Week', 'e.g. due next week',
                    autocomplete=f" {task.phrase_with(due_date='due next week')} ", icon=icons.NEXT_WEEK)
        wf.add_item('Next Month', 'e.g. due next month',
                    autocomplete=f" {task.phrase_with(due_date='due next month')} ", icon=icons.CALENDAR)
        wf.add_item('Next Year', 'e.g. due next year, due April 15',
                    autocomplete=f" {task.phrase_with(due_date='due next year')} ", icon=icons.CALENDAR)
        wf.add_item('Remove due date', 'Add "not due" to fix accidental dates, or see td-pref',
                    autocomplete=f" {task.phrase_with(due_date=False)}", icon=icons.CANCEL)

    # Task has an unfinished reminder phrase
    elif task.has_reminder_prompt:
        prefs = Preferences.current_prefs()
        default_reminder_time = format_time(prefs.reminder_time, 'short')
        due_date_hint = ' on the due date' if task.due_date else ''
        wf.add_item(f"Reminder at {default_reminder_time}{due_date_hint}", f"e.g. r {default_reminder_time}",
                    autocomplete=f" {task.phrase_with(reminder_date='remind me at %s' % format_time(prefs.reminder_time, 'short'))} ",
                    icon=icons.REMINDER)
        wf.add_item(f"At noon{due_date_hint}", 'e.g. reminder noon',
                    autocomplete=f" {task.phrase_with(reminder_date='remind me at noon')} ",
                    icon=icons.REMINDER)
        wf.add_item(f"At 8:00 PM{due_date_hint}", 'e.g. remind at 8:00 PM',
                    autocomplete=f" {task.phrase_with(reminder_date='remind me at 8:00pm')} ",
                    icon=icons.REMINDER)
        wf.add_item(f"At dinner{due_date_hint}", 'e.g. alarm at dinner',
                    autocomplete=f" {task.phrase_with(reminder_date='remind me at dinner')} ",
                    icon=icons.REMINDER)
        wf.add_item('Today at 6:00 PM', 'e.g. remind me today at 6pm',
                    autocomplete=f" {task.phrase_with(reminder_date='remind me today at 6:00pm')} ",
                    icon=icons.REMINDER)
        wf.add_item('Remove reminder', autocomplete=f" {task.phrase_with(reminder_date=False)}", icon=icons.CANCEL)

    # Main menu for tasks
    else:
        wf.add_item(f"{task.list_title} – create a new task...", subtitle, arg='--stored-query',
                    valid=task.title != '', icon=icons.TASK) \
                        .add_modifier(key='alt', subtitle=f"…then edit it in the ToDo app    {subtitle}")

        title = 'Change folder' if task.list_title else 'Select a folder'
        wf.add_item(title, f"Prefix the task, e.g. Automotive: {task.title}",
                    autocomplete=f" {task.phrase_with(list_title=True)}", icon=icons.LIST)

        title = 'Change the due date' if task.due_date else 'Set a due date'
        wf.add_item(title, '"due" followed by any date-related phrase, e.g. due next Tuesday; due May 4',
                    autocomplete=f" {task.phrase_with(due_date=True)}", icon=icons.CALENDAR)

        title = 'Change the recurrence' if task.recurrence_type else 'Make it a recurring task'
        wf.add_item(title, '"every" followed by a unit of time, e.g. every 2 months; every year; every 4w',
                    autocomplete=f" {task.phrase_with(recurrence=True)}", icon=icons.RECURRENCE)

        title = 'Change the reminder' if task.reminder_date else 'Set a reminder'
        wf.add_item(title, '"remind me" followed by a time and/or date, e.g. remind me at noon; r 10am; alarm 8:45p',
                    autocomplete=f" {task.phrase_with(reminder_date=True)}", icon=icons.REMINDER)

        if task.starred:
            wf.add_item('Remove star', 'Remove * from the task',
                        autocomplete=f" {task.phrase_with(starred=False)}", icon=icons.STAR_REMOVE)
        else:
            wf.add_item('Star', 'End the task with * (asterisk)',
                        autocomplete=f" {task.phrase_with(starred=True)}", icon=icons.STAR)

        wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

def commit(args, modifier=None):
    from mstodo.api import tasks
    from mstodo.sync import background_sync

    task = _task(args)
    prefs = Preferences.current_prefs()

    prefs.last_taskfolder_id = task.list_id

    req = tasks.create_task(task.list_id, task.title,
                                  assignee_id=task.assignee_id,
                                  recurrence_type=task.recurrence_type,
                                  recurrence_count=task.recurrence_count,
                                  due_date=task.due_date,
                                  reminder_date=task.reminder_date,
                                  starred=task.starred,
                                  completed=task.completed,
                                  note=task.note)

    if req.status_code == codes.created:
        notify(title="Task creation success", message=f"The task was added to {task.list_title}")
        background_sync()
        if modifier == 'alt':
            import webbrowser
            webbrowser.open(f"ms-to-do://search/{task.title}")
    elif req.status_code > 400:
        notify(title="Task creation error", message=req.json()['error']['message'])
    else:
        notify(title="Task creation error", message="Unknown error. Try again or raise an issue on github")
