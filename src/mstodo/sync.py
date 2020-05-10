from datetime import datetime
import os
import time

from workflow.notify import notify
from workflow.background import is_running

from mstodo.models.preferences import Preferences
from mstodo.util import workflow

import logging
log = logging.getLogger('mstodo')

def sync(background=False):
    log.info('running mstodo/sync')
    from mstodo.models import base, task, user, taskfolder, hashtag
    from peewee import OperationalError

    # If a sync is already running, wait for it to finish. Otherwise, store
    # the current pid in alfred-workflow's pid cache file
    if not background:
        if is_running('sync'):
            wait_count = 0
            while is_running('sync'):
                time.sleep(.25)
                wait_count += 1

                if wait_count == 2:
                    notify('Please wait...', 'The workflow is making sure your tasks are up-to-date')

            return False

        pidfile = workflow().cachefile('sync.pid')
        with open(pidfile, 'wb') as file_obj:
            file_obj.write('{0}'.format(os.getpid()))


    base.BaseModel._meta.database.create_tables([
        taskfolder.TaskFolder,
        task.Task,
        user.User,
        hashtag.Hashtag
    ], safe=True)

    # Perform a query that requires the latest schema; if it fails due to a
    # mismatched scheme, delete the old database and re-sync
    try:
        task.Task.select().where(task.Task.recurrence_count > 0).count()
        hashtag.Hashtag.select().where(hashtag.Hashtag.tag == '').count()
    except OperationalError:
        base.BaseModel._meta.database.close()
        workflow().clear_data(lambda f: 'mstodo.db' in f)

        # Make sure that this sync does not try to wait until its own process
        # finishes
        sync(background=True)
        return

    first_sync = False
    

    try:
        # get root item from DB. If it doesn't exist then make this the first sync. 
        user.User.get()
    except user.User.DoesNotExist:
        first_sync = True
        Preferences.current_prefs().last_sync = datetime.utcnow()
        notify('Please wait...', 'The workflow is syncing tasks for the first time')

    user.User.sync(background=background)
    taskfolder.TaskFolder.sync(background=background)
    if first_sync:
        task.Task.sync_all_tasks(background=background)
    else:
        task.Task.sync_modified_tasks(background=background)

    if background:
        if first_sync:
            notify('Initial sync has completed', 'All of your tasks are now available for browsing')

        # If executed manually, this will pass on to the post notification action
        print('Sync completed successfully')
    
    log.debug('First sync: ' + str(first_sync))
    log.debug('Last sync time: ' + str(Preferences.current_prefs().last_sync))
    Preferences.current_prefs().last_sync = datetime.utcnow()
    log.debug('This sync time: ' + str(Preferences.current_prefs().last_sync))
    return True


def background_sync():
    from workflow.background import run_in_background
    task_id = 'sync'

    # Only runs if another sync is not already in progress
    run_in_background(task_id, [
        '/usr/bin/env',
        'python',
        workflow().workflowfile('alfred-mstodo-workflow.py'),
        'pref sync background',
        '--commit'
    ])


def background_sync_if_necessary(seconds=30):
    last_sync = Preferences.current_prefs().last_sync

    # Avoid syncing on every keystroke, background_sync will also prevent
    # multiple concurrent syncs
    if last_sync is None or (datetime.utcnow() - last_sync).total_seconds() > seconds:
        background_sync()
