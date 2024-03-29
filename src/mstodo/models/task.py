# encoding: utf-8

from datetime import date, timedelta, datetime
import logging
import time

from peewee import (BooleanField, CharField, ForeignKeyField, IntegerField,
                    PeeweeException, TextField)

from mstodo.models.fields import DateTimeUTCField
from mstodo.models.base import BaseModel
from mstodo.models.taskfolder import TaskFolder
from mstodo.models.user import User
from mstodo.util import short_relative_formatted_date, SYMBOLS

log = logging.getLogger(__name__)

_days_by_recurrence_type = {
    'day': 1,
    'week': 7,
    'month': 30.43,
    'year': 365
}

_primary_api_fields = [
    'id',
    'parentFolderId',
    'lastModifiedDateTime',
    'changeKey',
    'status'
]
_secondary_api_fields = [
    'createdDateTime',
    'startDateTime',
    'dueDateTime',
    'isReminderOn',
    'reminderDateTime',
    'completedDateTime',
    'recurrence',
    'subject',
    'body',
    'importance',
    'sensitivity',
    'hasAttachments',
    'owner',
    'assignedTo'
]

class Task(BaseModel):
    """
    Extends the Base class and refines it for the Task data structure 
    """
    id = CharField(primary_key=True)
    list = ForeignKeyField(TaskFolder,index=True, related_name='tasks') #@TODO check related name syntax
    createdDateTime = DateTimeUTCField()
    lastModifiedDateTime = DateTimeUTCField()
    changeKey = CharField()
    hasAttachments = BooleanField(null=True)
    importance = CharField(index=True, null=True)
    isReminderOn = BooleanField(null=True)
    owner = ForeignKeyField(User, related_name='created_tasks', null=True)
    assignedTo = ForeignKeyField(User, related_name='assigned_tasks', null=True)
    sensitivity = CharField(index=True,null=True)
    status = CharField(index=True)
    title = TextField(index=True)
    completedDateTime = DateTimeUTCField(index=True, null=True)
    dueDateTime = DateTimeUTCField(index=True, null=True)
    reminderDateTime = DateTimeUTCField(index=True, null=True)
    startDateTime = DateTimeUTCField(index=True, null=True)
    body_contentType = TextField(null=True)
    body_content = TextField(null=True)
    recurrence_type = CharField(null=True)
    recurrence_count = IntegerField(null=True)
    # "categories": [],

    @staticmethod
    def transform_datamodel(tasks_data):
        for task in tasks_data:
            for (k, v) in task.copy().items():
                if k == "subject":
                    task['title'] = v
                elif k == "parentFolderId":
                    task['list'] = v
                if isinstance(v, dict):
                    if k.find("DateTime") > -1:
                        # Datetimes are shown as a dicts with naive datetime + separate timezone field
                        task[k] = v['dateTime']
                    elif k == "body":
                        task['body_contentType'] = v['contentType']
                        task['body_content'] = v['content']
                    elif k == 'recurrence':
                        # WL uses day, week month year, MSTODO uses
                        # daily weekly absoluteMonthly relativeMonthly a..Yearly r...Yearly
                        if 'week' in v['pattern']['type'].lower():
                            window = 'week'
                        elif 'month' in v['pattern']['type'].lower():
                            window = 'month'
                        elif 'year' in v['pattern']['type'].lower():
                            window = 'year'
                        elif 'da' in v['pattern']['type'].lower():
                            window = 'day'
                        else:
                            window = ''
                        task['recurrence_type'] = window
                        task['recurrence_count'] = v['pattern']['interval']
        return tasks_data

    @classmethod
    def sync_all_tasks(cls):
        from mstodo.api import tasks
        from concurrent import futures
        start = time.time()
        instances = []
        tasks_data = []

        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            fields = list(_primary_api_fields)
            fields.extend(_secondary_api_fields)
            kwargs = {'fields': fields}
            job = executor.submit(lambda p: tasks.tasks(**p),kwargs)
            tasks_data = job.result()

        log.debug(f"Retrieved all {len(tasks_data)} task ids in {round(time.time() - start, 3)} seconds")
        start = time.time()

        try:
            # Pull instances from DB if they exist
            instances = cls.select(cls.id, cls.title, cls.changeKey)
        except PeeweeException:
            pass

        log.debug(f"Retrieved all {len(instances)} tasks from database in {round(time.time() - start, 3)} seconds")
        start = time.time()

        tasks_data = cls.transform_datamodel(tasks_data)
        cls._perform_updates(instances, tasks_data)
        cls._sync_children()

        log.debug(f"Completed updates to tasks in {round(time.time() - start, 3)} seconds")

        return None

    @classmethod
    def sync_modified_tasks(cls):
        from mstodo.api import tasks
        from concurrent import futures
        from workflow import Workflow
        wf = Workflow()
        start = time.time()
        instances = []
        all_tasks = []

        # Remove 60 seconds to make sure all recent tasks are included
        # dt = Preferences.current_prefs().last_sync - timedelta(seconds=60)
        dt = wf.cached_data('last_sync', max_age=0) - timedelta(seconds=60)

        # run a single future for all tasks modified since last run
        with futures.ThreadPoolExecutor() as executor:
            job = executor.submit(lambda p: tasks.tasks(**p), {'dt':dt, 'afterdt':True})
            modified_tasks = job.result()

        # run a separate futures map over all taskfolders @TODO change this to be per taskfolder
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            jobs = (
                executor.submit(lambda p: tasks.tasks(**p),
                                {'fields': _primary_api_fields, 'completed':True}),
                executor.submit(lambda p: tasks.tasks(**p),
                                {'fields': _primary_api_fields, 'completed':False})
            )
            for job in futures.as_completed(jobs):
                all_tasks += job.result()

        # if task in modified_tasks then remove from all taskfolder data
        modified_tasks_ids = [task['id'] for task in modified_tasks]
        for task in all_tasks:
            if task['id'] in modified_tasks_ids:
                all_tasks.remove(task)
        all_tasks.extend(modified_tasks)

        log.debug(f"Retrieved all {len(all_tasks)} including {len(modified_tasks)}\
 modifications since {dt} in {round(time.time() - start, 3)} seconds")
        start = time.time()

        try:
            # Pull instances from DB
            instances = cls.select(cls.id, cls.title, cls.changeKey)
        except PeeweeException:
            pass

        log.debug(f"Loaded all {len(instances)} from database in {round(time.time() - start, 3)} seconds")
        start = time.time()

        all_tasks = cls.transform_datamodel(all_tasks)
        cls._perform_updates(instances, all_tasks)
        # cls._sync_children()
        #FIXME this causes errors, need to refactor

        log.debug(f"Completed updates to tasks in {round(time.time() - start, 3)} seconds")

        return None

    @classmethod
    def due_today(cls):
        return (
            cls.select(cls, TaskFolder)
            .join(TaskFolder)
            .where(cls.completedDateTime >> None)
            .where(cls.dueDateTime <= date.today())
            .order_by(cls.dueDateTime.asc())
        )

    @classmethod
    def search(cls, query):
        return (
            cls.select(cls, TaskFolder)
            .join(TaskFolder)
            .where(cls.completedDateTime >> None)
            .where(cls.title.contains(query))
            .order_by(cls.dueDateTime.asc())
        )

    @property
    def completed(self):
        return bool(self.completedDateTime)

    @property
    def overdue_times(self):
        if self.recurrence_type is None or self.completed:
            return 0
        recurrence_days = _days_by_recurrence_type[self.recurrence_type] * self.recurrence_count
        overdue_time = datetime.now() - self.dueDateTime.replace(tzinfo=None)
        return int(overdue_time.days / recurrence_days)

    @property
    def list_title(self):
        if self.list:
            return self.list.title
        return None

    def subtitle(self):
        from mstodo.util import format_time

        subtitle = []

        if self.importance == 'high':
            subtitle.append(SYMBOLS['star'])

        # Task is completed
        if self.status == 'completed':
            subtitle.append(f"Completed {short_relative_formatted_date(self.completedDateTime)}")
        # Task is not yet completed
        elif self.dueDateTime:
            subtitle.append(f"Due {short_relative_formatted_date(self.dueDateTime)}")

        if self.recurrence_type:
            if self.recurrence_count > 1:
                subtitle.append(f"{SYMBOLS['recurrence']} Every {self.recurrence_count} {self.recurrence_type}s")
            # Cannot simply add -ly suffix
            elif self.recurrence_type == 'day':
                subtitle.append(f"{SYMBOLS['recurrence']} Daily")
            else:
                subtitle.append(f"{SYMBOLS['recurrence']} {self.recurrence_type.title()}ly")

        if self.status != 'completed':
            overdue_times = self.overdue_times
            if overdue_times > 1:
                subtitle.insert(0, f"{SYMBOLS['overdue_2x']} {overdue_times}X OVERDUE!")
            elif overdue_times == 1:
                subtitle.insert(0, f"{SYMBOLS['overdue_1x']} OVERDUE!")

            if self.reminderDateTime:
                reminder_date_phrase = None

                if self.reminderDateTime.date() == self.dueDateTime:
                    reminder_date_phrase = 'On due date'
                else:
                    reminder_date_phrase = short_relative_formatted_date(self.reminderDateTime)

                subtitle.append(f"{SYMBOLS['reminder']} {reminder_date_phrase} at \
{format_time(self.reminderDateTime, 'short')}")

        subtitle.append(self.title)

        return '   '.join(subtitle)

    def _sync_children(self):
        pass
        #@TODO sort out child syncing
        # from mstodo.models.hashtag import Hashtag
        # Hashtag.sync()

    def __str__(self):
        title = self.title if len(self.title) <= 20 else self.title[:20].rstrip() + '…'
        task_subid = self.id[-32:]
        return f"<{type(self).__name__} ...{task_subid} {title}>"

    class Meta():
        """
        Custom metadata for the Task object
        """
        order_by = ('lastModifiedDateTime', 'id')
        expect_revisions = True
