import logging
import time

from peewee import TextField, CharField

from mstodo.models.fields import DateTimeUTCField
from mstodo.models.base import BaseModel
from mstodo.util import NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())


class User(BaseModel):
    id = CharField(primary_key=True)
    name = TextField(null=True)
    displayName = TextField(null=True)
    givenName = TextField(null=True)
    surname = TextField(null=True)
    userPrincipalName = TextField(null=True)
    mail = TextField(null=True)
    mobilePhone = TextField(null=True)
    jobTitle = TextField(null=True)
    officeLocation = TextField(null=True)
    preferredLanguage = TextField(null=True)
    # businessPhones": [],

    @classmethod
    def sync(cls, background=False):
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
