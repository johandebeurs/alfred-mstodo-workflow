import logging
import os
import time
from datetime import datetime, timezone

from workflow.notify import notify
from workflow.background import is_running
from mstodo.auth import is_authorised
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)
wf = wf_wrapper()

def sync(background: bool = False) -> bool:
    """Synchronize local database with Microsoft ToDo API.

    Args:
        background: If True, runs as a background sync without user notifications.
                   If False, runs as manual sync with progress notifications.

    Returns:
        bool: True if sync completed successfully, False if sync failed or was skipped.

    Side effects:
        - Creates/updates local SQLite database tables
        - Sends desktop notifications about sync progress
        - May trigger deauthorization if authentication fails
    """
    from mstodo.models import base, task, user, task_list, hashtag
    from mstodo.auth import oauth_token, deauthorise
    from peewee import OperationalError
    from requests.exceptions import HTTPError

    pid_name = 'sync'

    # Check if user is still authorized before attempting sync
    if not is_authorised():
        log.error("Sync failed: User is not authorized")
        if not background:
            notify(
                title='Authentication Required',
                message='Please log in to Microsoft ToDo to sync your tasks'
            )
        return False

    # Verify we can get a valid OAuth token
    token = oauth_token()
    if not token:
        log.error("Sync failed: Unable to obtain valid OAuth token")
        if not background:
            notify(
                title='Authentication Failed',
                message='Your session has expired. Please log in again'
            )
        return False

    # If a sync is already running, wait for it to finish. Otherwise, store
    # the current pid in alfred-workflow's pid cache file
    if not background:
        if is_running(pid_name):
            wait_count = 0
            while is_running(pid_name):
                time.sleep(.25)
                wait_count += 1

                if wait_count == 2:
                    notify(
                        title='Please wait...',
                        message='The workflow is making sure your tasks are up-to-date'
                    )

            return False

        log.info("Running manual sync")
        notify(
            title='Manual sync initiated',
            message='The workflow is making sure your tasks are up-to-date'
        )

        pidfile = wf.cachefile(f"{pid_name}.pid")
        with open(pidfile, 'w', encoding='utf-8') as file_obj:
            file_obj.write(str(os.getpid()))
    else:
        log.info('Running background sync')

    # Database schema migration for v1.0 API
    last_version = wf.settings.get('__workflow_last_version', str(wf.version))
    current_version = str(wf.version)

    if (last_version < current_version) & (last_version < '0.3.0'):
        log.info(f"Schema migration from {last_version} to {current_version}")
        base.BaseModel._meta.database.close()
        wf.clear_data(lambda f: 'mstodo.db' in f)
        wf.settings['__workflow_last_version'] = current_version
        notify(
            title='Database Upgraded',
            message='Your tasks will now re-synced with the new MS ToDo API'
        )

    base.BaseModel._meta.database.create_tables([
        task_list.TaskList,
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
        wf.clear_data(lambda f: 'mstodo.db' in f)

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
        wf.cache_data('last_sync',datetime.now(timezone.utc))
        notify(
            title='Please wait...',
            message='The workflow is syncing tasks for the first time'
        )

    # Wrap API sync calls in try-except to handle authentication failures
    try:
        user.User.sync()
        task_list.TaskList.sync()
        task.Task.sync_all_tasks()
        hashtag.Hashtag.sync()
        #@TODO move this into a child sync of the relevant tasks once bugfix is completed

    except HTTPError as e:
        # Check if this is an authentication error (401 Unauthorized)
        if e.response is not None and e.response.status_code == 401:
            log.error(f"Sync failed with 401 Unauthorized: {e}")
            if not background:
                notify(
                    title='Authentication Failed',
                    message='Your session has expired. Please log in again to sync'
                )
            deauthorise()
            return False
        # Re-raise other HTTP errors
        log.error(f"Sync failed with HTTP error: {e}")
        if not background:
            notify(
                title='Sync Failed',
                message=f'An error occurred during sync: {e.response.status_code if e.response else "Unknown"}'
            )
        raise
    except Exception as e:
        log.error(f"Sync failed with unexpected error: {e}", exc_info=True)
        if not background:
            notify(
                title='Sync Failed',
                message='An unexpected error occurred. Check logs for details'
            )
        raise

    sync_completion_time = datetime.now(timezone.utc)

    if first_sync or not background:
        notify(
            title='Sync has completed',
            message='All of your tasks are now available for browsing'
        )

    wf.cache_data('last_sync', sync_completion_time)
    log.info(f"{'Backgound sync' if background else 'Sync'} completed at {sync_completion_time}")
    return True


def background_sync() -> None:
    """Initiate a background synchronization if one is not already running.

    Side effects:
        Starts a background process to sync tasks with Microsoft ToDo API.
    """
    from workflow.background import run_in_background
    from mstodo.config import BACKGROUND_SYNC_MAX_AGE_SECONDS

    pid_name = 'sync'
    current_timestamp = datetime.now(timezone.utc)
    last_sync = wf.cached_data('last_sync', max_age=0)

    log.debug(f"Last sync time was: {str(last_sync)}")

    # Avoid syncing on every keystroke, background_sync will also prevent
    # multiple concurrent syncs
    if last_sync is None or (current_timestamp - last_sync.astimezone(timezone.utc)).total_seconds() \
        > BACKGROUND_SYNC_MAX_AGE_SECONDS:
        log.info(f"Triggering background sync at {current_timestamp}")
        run_in_background(pid_name, [
            '/usr/bin/env',
            'python3',
            wf.workflowfile('alfred_mstodo_workflow.py'),
            'pref sync background',
            '--commit'
        ])
