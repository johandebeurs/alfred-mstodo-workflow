import logging
import time

from peewee import TextField, CharField

from mstodo.models.base import BaseModel

log = logging.getLogger(__name__)

class User(BaseModel):
    """
    Extends the Base class and refines it for the User data structure 
    """
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
    def sync(cls):
        from mstodo.api import user

        start = time.time()
        instance = None
        user_data = user.user()
        log.debug(f"Retrieved User in {round(time.time() - start, 3)}")

        try:
            instance = cls.get()
        except User.DoesNotExist:
            pass

        return cls._perform_updates([instance], [user_data])
