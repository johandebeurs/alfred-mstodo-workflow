# encoding: utf-8

import re
import logging
from typing import List, Optional

from peewee import fn, OperationalError
from workflow import MATCH_ALL, MATCH_ALLCHARS

from mstodo import icons
from mstodo.models.task_list import TaskList
from mstodo.models.preferences import Preferences
from mstodo.models.task import Task
from mstodo.sync import background_sync
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

_hashtag_prompt_pattern = re.compile(r'#\S*$', re.UNICODE)


def display(args: List[str]) -> None:
    """Display task search interface with filtering options.

    Provides search functionality with support for:
    - Hashtag filtering (using # prefix)
    - List filtering (using list_name: prefix)
    - Free text search across task titles

    Args:
        args: List of command-line arguments from Alfred. First element
            is the command, remaining elements form the search query.

    Side effects:
        - Adds menu items to Alfred workflow feedback.
        - Triggers background sync to ensure up-to-date results.
        - May trigger additional sync if database error occurs.
    """
    query = ' '.join(args[1:])
    wf = wf_wrapper()
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
            wf.add_item(hashtag.tag[1:], '',
                        autocomplete=f"-search {query[:hashtag_match.start()]}{hashtag.tag} ",
                        icon=icons.HASHTAG)

    else:
        conditions = True
        task_lists = TaskList.select()
        matching_task_lists = None
        query = ' '.join(args[1:]).strip()
        task_list_query = None

        # Show all task lists on the main search screen
        if not query:
            matching_task_lists = task_lists
        # Filter task lists when colon is used
        if ':' in query:
            matching_task_lists = task_lists
            components = re.split(r':\s*', query, 1)
            task_list_query = components[0]
            if task_list_query:
                matching_task_lists = wf.filter(
                    task_list_query,
                    task_lists if task_lists else [],
                    lambda l: l.title,
                    # Ignore MATCH_ALLCHARS which is expensive and inaccurate
                    match_on=MATCH_ALL ^ MATCH_ALLCHARS
                )

                # If no matching task list search against all tasks
                if matching_task_lists:
                    query = components[1] if len(components) > 1 else ''

                # If there is a task list exactly matching the query ignore
                # anything else. This takes care of task_lists that are substrings
                # of other task_lists
                if len(matching_task_lists) > 1:
                    for task_list in matching_task_lists:
                        if task_list.title.lower() == task_list_query.lower():
                            matching_task_lists = [task_list]
                            break

        if matching_task_lists:
            if not task_list_query:
                wf.add_item('Browse by hashtag', autocomplete='-search #', icon=icons.HASHTAG)

            if len(matching_task_lists) > 1:
                for task_list in matching_task_lists:
                    icon = icons.INBOX if task_list.wellknownListName == 'defaultList' else icons.LIST
                    wf.add_item(task_list.title, autocomplete=f"-search {task_list.title}: ", icon=icon)
            else:
                conditions = conditions & (Task.list == matching_task_lists[0].id)

        if not matching_task_lists or len(matching_task_lists) <= 1:
            for arg in query.split(' '):
                if len(arg) > 1:
                    conditions = conditions & (Task.title.contains(arg) | TaskList.title.contains(arg))

            if conditions:
                if not prefs.show_completed_tasks:
                    conditions = (Task.status != 'completed') & conditions

                tasks = Task.select().where(Task.list.is_null(False) & conditions)

                tasks = tasks.join(TaskList).order_by(Task.lastModifiedDateTime.desc(), TaskList.id.asc())

                # Avoid excessive results
                tasks = tasks.limit(50)

                try:
                    for task in tasks:
                        wf.add_item(f"{task.list_title} – {task.title}", task.subtitle(),
                                    autocomplete=f"-task {task.id}  ",
                                    icon=icons.TASK_COMPLETED if task.status == 'completed' else icons.TASK)
                except OperationalError:
                    background_sync()


            if prefs.show_completed_tasks:
                wf.add_item('Hide completed tasks', arg=f"-pref show_completed_tasks --alfred {' '.join(args)}",
                            valid=True, icon=icons.HIDDEN)
            else:
                wf.add_item('Show completed tasks', arg=f"-pref show_completed_tasks --alfred {' '.join(args)}",
                            valid=True, icon=icons.VISIBLE)

        wf.add_item('New search', autocomplete='-search ', icon=icons.CANCEL)
        wf.add_item('Main menu', autocomplete='', icon=icons.BACK)

        # Make sure tasks are up-to-date while searching
        background_sync()

def commit(args: List[str], modifier: Optional[str] = None) -> None: # pylint: disable=W0613
    """Execute search-related actions.

    Currently a placeholder for future search commit functionality.

    Args:
        args: List of command-line arguments specifying the action.
        modifier: Optional modifier key (alt, cmd, ctrl, fn) pressed during action.
    """
    _ = args[1]  # action - unused placeholder for future implementation
