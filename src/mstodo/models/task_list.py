import logging
import time

from peewee import (BooleanField, CharField, PeeweeException)

from mstodo.models.base import BaseModel
from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

class TaskList(BaseModel):
    """
    Extends the Base class and refines it for the List data structure
    """
    id = CharField(primary_key=True)
    title = CharField(index=True)
    isOwner = BooleanField()
    isShared = BooleanField()
    wellknownListName = CharField(index=True)

    @classmethod
    def sync(cls):
        from mstodo.api import task_lists
        start = time.time()

        task_lists_data = task_lists.task_lists()
        instances = []

        log.info(f"Retrieved all {len(task_lists_data)} task_lists in {round(time.time() - start, 3)} seconds")
        start = time.time()

        # Hacky translation of mstodo data model to wunderlist data model
        # to avoid changing naming in rest of the files
        for task_list in task_lists_data:
            for (key,value) in task_list.copy().items():
                if key == "displayName":
                    task_list['title'] = value

        wf_wrapper().store_data('task_lists', task_lists_data)

        try:
            instances = cls.select(cls.id, cls.title)
        except PeeweeException:
            pass

        log.info(f"Loaded all {len(instances)} task_lists from \
the database in {round(time.time() - start, 3)} seconds")

        return cls._perform_updates(instances, task_lists_data)

    @classmethod
    def _populate_api_extras(cls, info):
        from mstodo.api.task_lists import update_task_list_with_tasks_count

        update_task_list_with_tasks_count(info)

        return info

    def __str__(self):
        return f"<{type(self).__name__} {self.id} {self.title}>"

    def _sync_children(self):
        pass
        #@TODO figure out how to sync tasks for each list separately
        # from mstodo.models.task import Task
        # Task.sync_tasks_in_task_list(self)

    class Meta:
        """
        Custom metadata for the TaskList object
        """
        order_by = ('id',)
        has_children = False
