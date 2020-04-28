# encoding: utf-8

import re
import logging

from peewee import fn, OperationalError
from workflow import MATCH_ALL, MATCH_ALLCHARS

from mstodo import icons
from mstodo.models.taskfolder import TaskFolder
from mstodo.models.preferences import Preferences
from mstodo.models.task import Task
from mstodo.sync import background_sync
from mstodo.util import workflow

log = logging.getLogger(__name__)

_hashtag_prompt_pattern = re.compile(r'#\S*$', re.UNICODE)

def filter(args):
    query = ' '.join(args[1:])
    wf = workflow()
    prefs = Preferences.current_prefs()
    matching_hashtags = []

    if not query:
        wf.add_item('Begin typing to search tasks', '', icon=icons.SEARCH)

    hashtag_match = re.search(_hashtag_prompt_pattern, query)
    if hashtag_match:
        from mstodo.models.hashtag import Hashtag

        hashtag_prompt = hashtag_match.group().lower()
        hashtags = Hashtag.select().where(Hashtag.id.contains(hashtag_prompt)).order_by(fn.Lower(Hashtag.tag).asc())

        for hashtag in hashtags:
            # If there is an exact match, do not show hashtags
            if hashtag.id == hashtag_prompt:
                matching_hashtags = []
                break

            matching_hashtags.append(hashtag)

    # Show hashtag prompt if there is more than one matching hashtag or the
    # hashtag being typed does not exactly match the single matching hashtag
    if len(matching_hashtags) > 0:
        for hashtag in matching_hashtags:
            wf.add_item(hashtag.tag[1:], '', autocomplete=u'-search %s%s ' % (query[:hashtag_match.start()], hashtag.tag), icon=icons.HASHTAG)

    else:
        conditions = True
        taskfolders = workflow().stored_data('taskfolders')
        matching_taskfolders = None
        query = ' '.join(args[1:]).strip()
        taskfolder_query = None

        # Show all task folders on the main search screen
        if not query:
            matching_taskfolders = taskfolders
        # Filter task folders when colon is used
        if ':' in query:
            matching_taskfolders = taskfolders
            components = re.split(r':\s*', query, 1)
            taskfolder_query = components[0]
            if taskfolder_query:
                matching_taskfolders = workflow().filter(
                    taskfolder_query,
                    taskfolders if taskfolders else [],
                    lambda f: f['title'],
                    # Ignore MATCH_ALLCHARS which is expensive and inaccurate
                    match_on=MATCH_ALL ^ MATCH_ALLCHARS
                )

                # If no matching task folder search against all tasks
                if matching_taskfolders:
                    query = components[1] if len(components) > 1 else ''

                # If there is a task folder exactly matching the query ignore
                # anything else. This takes care of taskfolders that are substrings
                # of other taskfolders
                if len(matching_taskfolders) > 1:
                    for f in matching_taskfolders:
                        if f['title'].lower() == taskfolder_query.lower():
                            matching_taskfolders = [f]
                            break

        if matching_taskfolders:
            if not taskfolder_query:
                wf.add_item('Browse by hashtag', autocomplete='-search #', icon=icons.HASHTAG)

            if len(matching_taskfolders) > 1:
                for f in matching_taskfolders:
                    icon = icons.INBOX if f['isDefaultFolder'] else icons.LIST
                    wf.add_item(f['title'], autocomplete='-search %s: ' % f['title'], icon=icon)
            else:
                conditions = conditions & (Task.list == matching_taskfolders[0]['id'])

        if not matching_taskfolders or len(matching_taskfolders) <= 1:
            for arg in query.split(' '):
                if len(arg) > 1:
                    conditions = conditions & (Task.title.contains(arg) | TaskFolder.title.contains(arg))

            if conditions:
                if not prefs.show_completed_tasks:
                    conditions = (Task.status != 'completed') & conditions

                tasks = Task.select().where(Task.list.is_null(False) & conditions)

                tasks = tasks.join(TaskFolder).order_by(Task.lastModifiedDateTime.desc(), TaskFolder.changeKey.asc())

                # Avoid excessive results
                tasks = tasks.limit(50)

                try:
                    for t in tasks:
                        wf.add_item(u'%s – %s' % (t.list_title, t.title), t.subtitle(), autocomplete='-task %s  ' % t.id, icon=icons.TASK_COMPLETED if t.status == 'completed' else icons.TASK) 
                except OperationalError:
                    background_sync()


            if prefs.show_completed_tasks:
                wf.add_item('Hide completed tasks', arg='-pref show_completed_tasks --alfred %s' % ' '.join(args), valid=True, icon=icons.HIDDEN)
            else:
                wf.add_item('Show completed tasks', arg='-pref show_completed_tasks --alfred %s' % ' '.join(args), valid=True, icon=icons.VISIBLE)

        wf.add_item('New search', autocomplete='-search ', icon=icons.CANCEL)
        wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

        # Make sure tasks are up-to-date while searching
        background_sync()

def commit(args, modifier=None):
    action = args[1]
