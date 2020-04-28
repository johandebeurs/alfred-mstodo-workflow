import logging
import time

from peewee import (BooleanField, CharField, IntegerField, PeeweeException,
                    PrimaryKeyField, TextField)

from mstodo.models.fields import DateTimeUTCField
from mstodo.models.base import BaseModel
from mstodo.util import workflow, NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())


class TaskFolder(BaseModel):
    id = CharField(primary_key=True)
    changeKey = CharField()
    title = CharField(index=True)
    isDefaultFolder = BooleanField()
    parentGroupKey = CharField()

    @classmethod
    def sync(cls, background=False):
        from mstodo.api import taskfolders
        start = time.time()

        taskfolders_data = taskfolders.taskFolders()
        instances = []

        log.info('Retrieved all %d task folders in %s', len(taskfolders_data), time.time() - start)
        start = time.time()

        # Hacky translation of mstodo data model to wunderlist data model to avoid changing naming in rest of the files
        for taskfolder in taskfolders_data:
            for (k,v) in taskfolder.copy().iteritems():
                if k == "name":
                    taskfolder['title'] = v

        workflow().store_data('taskfolders', taskfolders_data)

        try:
            instances = cls.select(cls.id, cls.changeKey, cls.title)
        except PeeweeException:
            pass

        log.info('Loaded all %d task folders from the database in %s', len(instances), time.time() - start)

        return cls._perform_updates(instances, taskfolders_data)

    @classmethod
    def _populate_api_extras(cls, info):
        from mstodo.api.taskfolders import update_taskfolder_with_tasks_count

        update_taskfolder_with_tasks_count(info)

        return info

    def __str__(self):
        return u'<%s %s %s>' % (type(self).__name__, self.id, self.title)

    def _sync_children(self):
        from mstodo.models.task import Task

        Task.sync_tasks_in_taskfolder(self)

    class Meta:
        order_by = ('changeKey', 'id')
        has_children = False
