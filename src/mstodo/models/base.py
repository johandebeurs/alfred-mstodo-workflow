from copy import copy
import logging
import time
from typing import Dict, Any, List

from dateutil import parser
from peewee import (DateField, DateTimeField, ForeignKeyField, Model,
                    SqliteDatabase, TimeField)

from mstodo.util import wf_wrapper

log = logging.getLogger(__name__)

db = SqliteDatabase(wf_wrapper().datadir + '/mstodo.db')
# This writes a SQLiteDB to ~/Library/Application Support/Alfred/Workflow Data/<workflow bundle id>

def _balance_keys_for_insert(values: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Balance dictionary keys across all items for batch insert operations.

    Ensures all dictionaries have the same keys, filling missing keys with None.

    Args:
        values: List of dictionaries with potentially different keys.

    Returns:
        List[Dict[str, Any]]: List of dictionaries with balanced keys.
    """
    all_keys = set()
    for v in values:
        all_keys.update(v)

    balanced_values = []
    for v in values:
        balanced = {}
        for k in all_keys:
            balanced[k] = v.get(k)
        balanced_values.append(balanced)

    return balanced_values

class BaseModel(Model):
    """
    Extends the Peewee model class and refines it for MS ToDo API structures.
    Holds methods to unpack APIs to database models, update data and perform
    actions on child items for an entity
    """
    @classmethod
    def _api2model(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API response data to model-compatible dictionary.

        Args:
            data: Dictionary from Microsoft ToDo API response.

        Returns:
            Dict[str, Any]: Dictionary suitable for model instance creation/update.
        """
        fields = copy(cls._meta.fields)
        model_data = {}

        # Map relationships, e.g. from user_id to user's
        for (field_name, field) in cls._meta.fields.items():
            if field_name.endswith('_id'):
                fields[field_name[:-3]] = field
            elif isinstance(field, ForeignKeyField):
                fields[field_name + '_id'] = field

            # The Microsoft ToDo API does not include some falsy values. For
            # example, if a task is completed then marked incomplete the
            # updated data will not include a completed key, so we have to set
            # the defaults for everything that is not specified
            if field.default:
                model_data[field_name] = field.default
            elif field.null:
                model_data[field_name] = None

        # Map each data property to the correct field
        for (k, v) in data.items():
            if k in fields:
                if isinstance(fields[k], (DateTimeField, DateField, TimeField)) and v is not None:
                    model_data[fields[k].name] = parser.parse(v)
                else:
                    model_data[fields[k].name] = v

        return model_data

    @classmethod
    def sync(cls) -> None:
        """Synchronize model data with Microsoft ToDo API.

        To be implemented by subclasses.
        """

    @classmethod
    def _perform_updates(cls, model_instances: List, update_items: List[Dict[str, Any]]) -> List:
        """Perform batch updates from delta query results.

        Args:
            model_instances: List of existing model instances from database.
            update_items: List of dictionaries from delta query (may include @removed items).

        Returns:
            List: List of all affected model instances (updated and newly created).
        """
        start = time.time()
        instances_by_id = dict((instance.id, instance) for instance in model_instances if instance)

        # Separate removed items from updates/additions
        removed_items = [item for item in update_items if '@removed' in item]
        changed_items = [item for item in update_items if '@removed' not in item]

        # Convert changed items to model format
        changed_items_by_id = dict((item['id'], cls._api2model(item)) for item in changed_items)
        removed_ids = set(item['id'] for item in removed_items)

        all_instances = []
        log.info(f"Processing {len(changed_items)} changes and {len(removed_items)} deletions for {cls.__name__}")

        with db.atomic():
            # Handle deletions
            for removed_id in removed_ids:
                if removed_id in instances_by_id:
                    instances_by_id[removed_id].delete_instance()
                    log.debug(f"Deleted {cls.__name__} {removed_id}")
                    del instances_by_id[removed_id]

            # Handle updates
            for item_id, instance in instances_by_id.items():
                if not instance:
                    continue
                if item_id in changed_items_by_id:
                    changed_item = changed_items_by_id[item_id]
                    all_instances.append(instance)

                    if cls._meta.has_children:
                        log.debug(f"Syncing children of {instance}")
                        instance._sync_children()

                    cls.update(**changed_item).where(cls.id == item_id).execute()
                    log.debug(f"Updated {instance} in db")
                    del changed_items_by_id[item_id]

        # Handle insertions (new items not in DB)
        new_values = list(changed_items_by_id.values())

        for i in range(0, len(new_values), 1000):
            inserted_chunk = _balance_keys_for_insert(new_values[i:i + 1000])

            with db.atomic():
                cls.insert_many(inserted_chunk).execute()  # pylint: disable=no-value-for-parameter
                log.debug(f"Created {len(inserted_chunk)} new {cls.__name__} in db")

                inserted_ids = [item['id'] for item in inserted_chunk]
                inserted_instances = cls.select().where(cls.id.in_(inserted_ids))

                for instance in inserted_instances:
                    if type(instance)._meta.has_children:
                        log.debug(f"Syncing children of {instance}")
                        instance._sync_children()

                all_instances += list(inserted_instances)

        log.info(f"Completed database updates in {round(time.time() - start, 3)} seconds")
        return all_instances

    @classmethod
    def _populate_api_extras(cls, info: Dict[str, Any]) -> Dict[str, Any]:
        """Populate additional API-specific fields.

        To be overridden by subclasses if needed.

        Args:
            info: Dictionary with API data.

        Returns:
            Dict[str, Any]: Dictionary with populated extras.
        """
        return info

    def __str__(self) -> str:
        """String representation of model instance.

        Returns:
            str: String in format '<ModelName id>'.
        """
        return f"<{type(self).__name__} {self.id}>"

    def _sync_children(self) -> None:
        """Synchronize child entities for this model instance.

        To be implemented by subclasses with child entities.
        """

    class Meta():
        """
        Default metadata for the base model object
        """
        database = db
        has_children = False
