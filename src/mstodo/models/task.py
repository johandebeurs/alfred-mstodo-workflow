# encoding: utf-8

from datetime import date, timedelta, datetime
import logging
import time

from peewee import (BooleanField, CharField, DateField, ForeignKeyField,
                    IntegerField, PeeweeException, PrimaryKeyField, TextField,
                    JOIN)

from mstodo.models.fields import DateTimeUTCField
from mstodo.models.base import BaseModel
from mstodo.models.taskfolder import TaskFolder
from mstodo.models.user import User
from mstodo.util import short_relative_formatted_date, NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

_days_by_recurrence_type = {
    'day': 1,
    'week': 7,
    'month': 30.43,
    'year': 365
}

_star = u'★'
_overdue_1x = u'⚠️'
_overdue_2x = u'❗️'
_recurrence = u'↻'
_reminder = u'⏰'

class Task(BaseModel):
    id = CharField(primary_key=True)
    list = ForeignKeyField(TaskFolder,index=True, related_name='tasks') #@TODO check related name syntax
    createdDateTime = DateTimeUTCField(null=True)
    lastModifiedDateTime = DateTimeUTCField(null=True)
    changeKey = CharField(null=True)
    hasAttachments = BooleanField(null=True)
    importance = CharField(index=True)
    isReminderOn = BooleanField(null=True)
    owner = ForeignKeyField(User, related_name='created_tasks', null=True)
    assignedTo = ForeignKeyField(User, related_name='assigned_tasks', null=True)
    sensitivity = CharField(index=True,null=True)
    status = CharField(index=True,null=True)
    title = TextField(index=True,null=True)
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
            for (k,v) in task.copy().iteritems():
                # log.debug(k + ": " + str(v))
                if k == "subject":
                    task['title'] = v
                elif k == "parentFolderId":
                    task['list'] = v
                if isinstance(v, dict):
                    if k.find("DateTime") > -1:
                        task[k] = v['dateTime']
                    elif k == "body":
                        task['body_contentType'] = v['contentType']
                        task['body_content'] = v['content']
                    elif k == 'recurrence':
                        # WL uses day, week month year, MSTODO uses daily weekly absoluteMonthly relativeMonthly a..Yearly r...Yearly
                        if 'week' in v['pattern']['type'].lower(): window = 'week'
                        elif 'month' in v['pattern']['type'].lower(): window = 'month'
                        elif 'year' in v['pattern']['type'].lower(): window = 'year'
                        elif 'da' in v['pattern']['type'].lower(): window = 'day'
                        else: window = ''
                        task['recurrence_type'] = window 
                        task['recurrence_count'] = v['pattern']['interval']
        return tasks_data

    @classmethod
    def sync_tasks_in_taskfolder(cls, taskfolder, background=False):
        from mstodo.api import tasks
        from concurrent import futures
        start = time.time()
        instances = []
        tasks_data = []
        # position_by_task_id = {}

        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            # positions_job = executor.submit(tasks.task_positions, list.id)
            jobs = (
                executor.submit(tasks.tasks, taskfolder.id, completed=False),
                executor.submit(tasks.tasks, taskfolder.id, completed=True)
            )

            for job in futures.as_completed(jobs):
                tasks_data += job.result()

            # position_by_task_id = dict((id, index) for (id, index) in enumerate(positions_job.result()))

        log.info('Retrieved all %d tasks for %s in %s', len(tasks_data), taskfolder, time.time() - start)
        start = time.time()

        def task_order(task):
            # task['order'] = position_by_task_id.get(task['id'])
            # return task['order'] or 1e99
            return 1e99

        tasks_data.sort(key=task_order)

        try:
            # Include all tasks thought to be in the list, plus any additional
            # tasks referenced in the data (task may have been moved to a different list)
            task_ids = [task['id'] for task in tasks_data]
            instances = cls.select(cls.id, cls.title, cls.changeKey)\
                .where(cls.id.in_(task_ids))
            log.info(instances)
        except PeeweeException:
            pass

        log.info('Loaded all %d tasks for %s from the database in %s', len(instances), taskfolder, time.time() - start)
        start = time.time()
        log.info(tasks_data)

        tasks_data = transform_datamodel(tasks_data)
        cls._perform_updates(instances, tasks_data)

        log.info('Completed updates to tasks in %s in %s', taskfolder, time.time() - start)

        return None
    
    @classmethod
    def sync_all_tasks(cls, background=False):
        from mstodo.api import tasks
        from concurrent import futures
        from mstodo.models.preferences import Preferences
        from mstodo.models.hashtag import Hashtag
        start = time.time()
        instances = []
        tasks_data = []

        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            job = executor.submit(tasks.tasks_all)
            tasks_data = job.result()

        log.info('Retrieved all %d tasks in %s', len(tasks_data), time.time() - start)
        start = time.time()

        try:
            # Pull instances from DB where task ID is in tasksdata returned from API
            task_ids = [task['id'] for task in tasks_data]
            instances = cls.select(cls.id, cls.title, cls.changeKey) #\
                # .where(cls.id.in_(task_ids))
        except PeeweeException:
            pass

        log.info('Loaded all %d tasks from the database in %s', len(instances), time.time() - start)
        start = time.time()

        tasks_data = cls.transform_datamodel(tasks_data)
        cls._perform_updates(instances, tasks_data)

        Hashtag.sync(background=background)

        log.info('Completed updates to tasks in %s', time.time() - start)

        return None

    @classmethod
    def sync_modified_tasks(cls, background=False):
        from mstodo.api import tasks
        from concurrent import futures
        from mstodo.models.preferences import Preferences
        from mstodo.models.hashtag import Hashtag
        start = time.time()
        instances = []
        tasks_data = []

        # Remove 360 seconds to make sure all recent tasks are included
        since_datetime = Preferences.current_prefs().last_sync - timedelta(seconds=360)

        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            job = executor.submit(tasks.tasks_all, since_datetime=since_datetime)
            tasks_data = job.result()

        log.info('Retrieved all %d tasks modified since %s in %s', len(tasks_data), since_datetime, time.time() - start)
        start = time.time()

        try:
            # Pull instances from DB where task ID is in tasksdata returned from API
            #@TODO pull all task IDs from API and delete items from DB where not in list
            task_ids = [task['id'] for task in tasks_data]
            instances = cls.select(cls.id, cls.title, cls.changeKey)\
                .where(cls.id.in_(task_ids))
        except PeeweeException:
            pass

        log.info('Loaded all %d tasks modified since %s from the database in %s', len(instances), since_datetime, time.time() - start)
        start = time.time()

        tasks_data = cls.transform_datamodel(tasks_data)
        cls._perform_updates(instances, tasks_data)

        Hashtag.sync(background=background)

        log.info('Completed updates to tasks in %s', time.time() - start)

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
            subtitle.append(_star)

        # Task is completed
        if self.status == 'completed':
            subtitle.append('Completed %s' % short_relative_formatted_date(self.completedDateTime))
        # Task is not yet completed
        elif self.dueDateTime:
            subtitle.append('Due %s' % short_relative_formatted_date(self.dueDateTime))

        if self.recurrence_type:
            if self.recurrence_count > 1:
                subtitle.append('%s Every %d %ss' % (_recurrence, self.recurrence_count, self.recurrence_type))
            # Cannot simply add -ly suffix
            elif self.recurrence_type == 'day':
                subtitle.append('%s Daily' % (_recurrence))
            else:
                subtitle.append('%s %sly' % (_recurrence, self.recurrence_type.title()))

        if not self.status == 'completed':
            overdue_times = self.overdue_times
            if overdue_times > 1:
                subtitle.insert(0, u'%s %dX OVERDUE!' % (_overdue_2x, overdue_times))
            elif overdue_times == 1:
                subtitle.insert(0, u'%s OVERDUE!' % (_overdue_1x))

            if self.reminderDateTime:
                reminder_date_phrase = None

                if self.reminderDateTime.date() == self.dueDateTime:
                    reminder_date_phrase = 'On due date'
                else:
                    reminder_date_phrase = short_relative_formatted_date(self.reminderDateTime)

                subtitle.append('%s %s at %s' % (
                    _reminder,
                    reminder_date_phrase,
                    format_time(self.reminderDateTime, 'short')))

        subtitle.append(self.title)

        return '   '.join(subtitle)

    def __str__(self):
        title = self.title if len(self.title) <= 20 else self.title[:20].rstrip() + u'…'
        return u'<%s %s %s>' % (type(self).__name__, self.id, title)

    class Meta(object):
        order_by = ('lastModifiedDateTime', 'id')
