# encoding: utf-8

from datetime import date, datetime
import logging
import time

from peewee import (BooleanField, CharField, ForeignKeyField, IntegerField,
                    PeeweeException, TextField)

from mstodo.config import MS_TODO_API_WORKERS
from mstodo.models.base import BaseModel
from mstodo.models.fields import DateTimeUTCField
from mstodo.models.task_list import TaskList
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
    'title',  # v1.0 API uses 'title' instead of 'subject'
    'body',
    'importance',
    'hasAttachments'
    # Note: v1.0 API removed: 'sensitivity', 'owner', 'assignedTo', 'parentFolderId'
]

class Task(BaseModel):
    """
    Extends the Base class and refines it for the Task data structure
    """
    id = CharField(primary_key=True)
    list = ForeignKeyField(TaskList, index=True, backref='tasks')
    createdDateTime = DateTimeUTCField()
    lastModifiedDateTime = DateTimeUTCField()
    hasAttachments = BooleanField(null=True)
    importance = CharField(index=True, null=True)
    isReminderOn = BooleanField(null=True)
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
    # Removed fields not in v1.0 API: changeKey, owner, assignedTo, sensitivity
    # "categories": [],

    @staticmethod
    def transform_datamodel(tasks_data):
        """Transform API response data to match database model.

        Args:
            tasks_data: List of task dictionaries from the API.

        Returns:
            List of transformed task dictionaries ready for database insertion.
        """
        for task in tasks_data:
            # Skip transformation for removed items
            if '@removed' in task:
                continue

            for (k, v) in task.copy().items():
                if isinstance(v, dict):
                    if k.find("DateTime") > -1:
                        # Datetimes are dicts with naive datetime + separate timezone field
                        task[k] = v['dateTime']
                    elif k == "body":
                        task['body_contentType'] = v['contentType']
                        task['body_content'] = v['content']
                    elif k == 'recurrence':
                        # Parse recurrence pattern
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
        """Sync all tasks using delta queries for efficient updates.

        Delta queries handle both full and incremental syncs automatically,
        so this method works for both first sync and subsequent syncs.
        """
        from mstodo.api import tasks
        from mstodo.models.task_list import TaskList
        from concurrent import futures

        start = time.time()
        all_lists = TaskList.select()
        tasks_data = []

        # Fetch tasks for each list using delta queries (parallel execution)
        with futures.ThreadPoolExecutor(max_workers=MS_TODO_API_WORKERS) as executor:
            jobs = []
            for task_list in all_lists:
                job = executor.submit(tasks.tasks, task_list.id)
                jobs.append(job)

            for job in futures.as_completed(jobs):
                tasks_data.extend(job.result())

        log.info(f"Retrieved {len(tasks_data)} tasks in {round(time.time() - start, 3)} seconds")

        # Get existing instances
        instances = []
        try:
            instances = list(cls.select(cls.id, cls.title))
        except PeeweeException:
            pass

        # Transform and update
        tasks_data = cls.transform_datamodel(tasks_data)
        cls._perform_updates(instances, tasks_data)
        # cls._sync_children() @TODO check if this is still required given the refactor


    @classmethod
    def due_today(cls):
        return (
            cls.select(cls, TaskList)
            .join(TaskList)
            .where(cls.completedDateTime >> None)
            .where(cls.dueDateTime <= date.today())
            .order_by(cls.dueDateTime.asc())
        )

    @classmethod
    def search(cls, query):
        return (
            cls.select(cls, TaskList)
            .join(TaskList)
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

                if self.reminderDateTime.date() == self.dueDateTime.date():
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
