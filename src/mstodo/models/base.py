from copy import copy
import logging
import time

from dateutil import parser
from peewee import (DateField, DateTimeField, ForeignKeyField, Model,
                    SqliteDatabase, TimeField)

from mstodo.util import workflow, NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

db = SqliteDatabase(workflow().datadir + '/mstodo.db')
# This writes a SQLiteDB to ~/Library/Application Support/Alfred/Workflow Data/<this workflow> 

def _balance_keys_for_insert(values):
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
    @classmethod
    def _api2model(cls, data):
        fields = copy(cls._meta.fields)
        model_data = {}

        # Map relationships, e.g. from user_id to user's
        for (field_name, field) in cls._meta.fields.iteritems():
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
        for (k, v) in data.iteritems():
            if k in fields:
                if isinstance(fields[k], (DateTimeField, DateField, TimeField)) and v is not None:
                    model_data[fields[k].name] = parser.parse(v)
                else:
                    model_data[fields[k].name] = v

        return model_data

    @classmethod
    def sync(cls):
        pass

    @classmethod
    def _perform_updates(cls, model_instances, update_items):
        start = time.time()
        # This creates a dict of all records within the database, indexable by id
        instances_by_id = dict((instance.id, instance) for instance in model_instances if instance)

        # Remove all update metadata and instances that have the same revision
        # before any additional processing on the metadata
        def revised(item):
            id = item['id']
            logger = log.debug
            # if api task is in database, has a changeKey and is unchanged
            if id in instances_by_id and 'changeKey' in item and instances_by_id[id].changeKey == item['changeKey']:
                instance = instances_by_id[id] # read the single value from the database
                del instances_by_id[id] # remove it from our database list
                if type(instance)._meta.expect_revisions:
                    logger = log.info
                
                logger('Revision %s of %s is still the latest', instance.changeKey, instance)
                
                return False
            logger('Item %s needs to be updated', id)
            return True

        # changed items is the list of API data if it is updated based on the logic above
        changed_items = [item for item in update_items if revised(item)]

        # Map of id to the normalized item
        changed_items = dict((item['id'], cls._api2model(item)) for item in changed_items)
        all_instances = []
        log.info('Prepared %d of %d updated items in %s', len(changed_items), len(update_items), time.time() - start)

        # Update all the changed metadata and remove instances that no longer exist
        with db.atomic():
            # For each item in the database that is either deleted or changed
            for id, instance in instances_by_id.iteritems():
                if not instance:
                    continue
                if id in changed_items:
                    changed_item = changed_items[id]
                    # Create temp list with all changed items
                    all_instances.append(instance)

                    if cls._meta.has_children:
                        log.info('Syncing children of %s', instance)
                        instance._sync_children()
                    cls.update(**changed_item).where(cls.id == id).execute()
                    log.info('Updated %s in db to revision %s', instance, changed_item['changeKey'] if 'changeKey' in changed_item else 'N/A')
                    log.debug('with data %s', changed_item)
                    # remove changed items from list to leave only new items
                    del changed_items[id]
                # The model does not exist anymore
                else:
                    instance.delete_instance()
                    log.info('Deleted %s from db', instance)

        # Bulk insert and retrieve
        new_values = changed_items.values()

        # Insert new items in batches
        for i in xrange(0, len(new_values), 500):
            inserted_chunk = _balance_keys_for_insert(new_values[i:i + 500])

            with db.atomic():
                cls.insert_many(inserted_chunk).execute()

                log.info('Created %d of model %s in db', len(inserted_chunk), cls.__name__)

                inserted_ids = [i['id'] for i in inserted_chunk]
                inserted_instances = cls.select().where(cls.id.in_(inserted_ids)) # read from db again

                for instance in inserted_instances:
                    if type(instance)._meta.has_children:
                        log.info('Syncing children of %s', instance)
                        instance._sync_children()

                all_instances += inserted_instances

        return all_instances

    @classmethod
    def _populate_api_extras(cls, info):
        return info

    def __str__(self):
        return '<%s %s>' % (type(self).__name__, self.id)

    def _sync_children(self):
        pass

    class Meta(object):
        database = db
        expect_revisions = False
        has_children = False
