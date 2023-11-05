import logging
import time

from peewee import (BooleanField, CharField, PeeweeException)

from mstodo.models.base import BaseModel
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

class TaskFolder(BaseModel):
    """
    Extends the Base class and refines it for the Taskfolder data structure 
    """
    id = CharField(primary_key=True)
    changeKey = CharField()
    title = CharField(index=True)
    isDefaultFolder = BooleanField()
    parentGroupKey = CharField()

    @classmethod
    def sync(cls):
        from mstodo.api import taskfolders
        start = time.time()

        taskfolders_data = taskfolders.taskfolders()
        instances = []

        log.debug(f"Retrieved all {len(taskfolders_data)} taskfolders in {round(time.time() - start, 3)} seconds")
        start = time.time()

        # Hacky translation of mstodo data model to wunderlist data model
        # to avoid changing naming in rest of the files
        for taskfolder in taskfolders_data:
            for (key,value) in taskfolder.copy().items():
                if key == "name":
                    taskfolder['title'] = value

        wf_wrapper().store_data('taskfolders', taskfolders_data)

        try:
            instances = cls.select(cls.id, cls.changeKey, cls.title)
        except PeeweeException:
            pass

        log.debug(f"Loaded all {len(instances)} taskfolders from \
the database in {round(time.time() - start, 3)} seconds")

        return cls._perform_updates(instances, taskfolders_data)

    @classmethod
    def _populate_api_extras(cls, info):
        from mstodo.api.taskfolders import update_taskfolder_with_tasks_count

        update_taskfolder_with_tasks_count(info)

        return info

    def __str__(self):
        return f"<{type(self).__name__} {self.id} {self.title}>"

    def _sync_children(self):
        pass
        #@TODO figure out how to sync tasks for each folder separately
        # from mstodo.models.task import Task
        # Task.sync_tasks_in_taskfolder(self)

    class Meta:
        """
        Custom metadata for the Taskfolder object
        """
        order_by = ('changeKey', 'id')
        has_children = False
        expect_revisions = True
