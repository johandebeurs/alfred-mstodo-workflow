import logging
import time

from peewee import IntegerField, PrimaryKeyField, TextField

from mstodo.models.fields import DateTimeUTCField
from mstodo.models.base import BaseModel
from mstodo.util import NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())


class User(BaseModel):
    id = PrimaryKeyField()
    name = TextField()
    revision = IntegerField()
    created_at = DateTimeUTCField()

    @classmethod
    def sync(cls):
        from mstodo.api import user

        start = time.time()
        instance = None
        user_data = user.user()
        log.info('Retrieved User in %s', time.time() - start)

        try:
            instance = cls.get()
        except User.DoesNotExist:
            pass

        return cls._perform_updates([instance], [user_data])
