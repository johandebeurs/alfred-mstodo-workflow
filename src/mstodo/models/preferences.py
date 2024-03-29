from datetime import time, timedelta

from workflow import Workflow

DEFAULT_TASKFOLDER_MOST_RECENT = 'most_recent'

AUTOMATIC_REMINDERS_KEY = 'automatic_reminders'
DEFAULT_TASKFOLDER_ID_KEY = 'default_taskfolder_id'
DUE_ORDER_KEY = 'due_order'
EXPLICIT_KEYWORDS_KEY = 'explicit_keywords'
HOIST_SKIPPED_TASKS_KEY = 'hoist_skipped_tasks'
ICON_THEME_KEY = 'icon_theme'
LAST_TASKFOLDER_ID_KEY = 'last_taskfolder_id'
PRERELEASES_KEY = '__workflow_prereleases'
REMINDER_TIME_KEY = 'reminder_time'
REMINDER_TODAY_OFFSET_KEY = 'reminder_today_offset'
SHOW_COMPLETED_TASKS_KEY = 'show_completed_tasks'
UPCOMING_DURATION_KEY = 'upcoming_duration'
COMPLETED_DURATION_KEY = 'completed_duration'
DATE_LOCALE_KEY = 'date_locale'

# Using a new object to avoid cyclic imports between mstodo.util and this file
wf = Workflow()

class Preferences():
    """
    Holds and modifies preferences for the MS ToDo alfred workflow
    """

    _current_prefs = None

    @classmethod
    def current_prefs(cls):
        if not cls._current_prefs:
            cls._current_prefs = Preferences(wf.stored_data('prefs'))
        if not cls._current_prefs:
            cls._current_prefs = Preferences({})
        return cls._current_prefs

    def __init__(self, data):
        self._data = data or {}

        # Clean up old prerelease preference
        if 'prerelease_channel' in self._data:
            # Migrate to the alfred-workflow preference
            self.prerelease_channel = self._data['prerelease_channel']
            del self._data['prerelease_channel']

            wf.store_data('prefs', self._data)

    def _set(self, key, value):
        if value is None and key in self._data:
            del self._data[key]
        elif self._data.get(key) != value:
            self._data[key] = value
        else:
            return

        wf.store_data('prefs', self._data)

    def _get(self, key, default=None):
        value = self._data.get(key)

        if value is None and default is not None:
            value = default

        return value

    @property
    def reminder_time(self):
        return self._get(REMINDER_TIME_KEY) or time(9, 0, 0)

    @reminder_time.setter
    def reminder_time(self, reminder_time):
        self._set(REMINDER_TIME_KEY, reminder_time)

    @property
    def reminder_today_offset(self):
        return self._get(REMINDER_TODAY_OFFSET_KEY, None)

    @reminder_today_offset.setter
    def reminder_today_offset(self, reminder_today_offset):
        self._set(REMINDER_TODAY_OFFSET_KEY, reminder_today_offset)

    @property
    def reminder_today_offset_timedelta(self):
        reminder_today_offset = self.reminder_today_offset

        return timedelta(hours=reminder_today_offset.hour, minutes=reminder_today_offset.minute)

    @property
    def icon_theme(self):
        return self._get(ICON_THEME_KEY)

    @icon_theme.setter
    def icon_theme(self, reminder_time):
        self._set(ICON_THEME_KEY, reminder_time)

    @property
    def explicit_keywords(self):
        return self._get(EXPLICIT_KEYWORDS_KEY, False)

    @explicit_keywords.setter
    def explicit_keywords(self, explicit_keywords):
        self._set(EXPLICIT_KEYWORDS_KEY, explicit_keywords)

    @property
    def automatic_reminders(self):
        return self._get(AUTOMATIC_REMINDERS_KEY, False)

    @automatic_reminders.setter
    def automatic_reminders(self, automatic_reminders):
        self._set(AUTOMATIC_REMINDERS_KEY, automatic_reminders)

    @property
    def prerelease_channel(self):
        return wf.settings.get(PRERELEASES_KEY, False)

    @prerelease_channel.setter
    def prerelease_channel(self, prerelease_channel):
        wf.settings[PRERELEASES_KEY] = prerelease_channel

    @property
    def last_taskfolder_id(self):
        return self._get(LAST_TASKFOLDER_ID_KEY, None)

    @last_taskfolder_id.setter
    def last_taskfolder_id(self, last_taskfolder_id):
        self._set(LAST_TASKFOLDER_ID_KEY, last_taskfolder_id)

    @property
    def due_order(self):
        return self._get(DUE_ORDER_KEY, ['order', 'due_date', 'taskfolder.order'])

    @due_order.setter
    def due_order(self, due_order):
        self._set(DUE_ORDER_KEY, due_order)

    @property
    def hoist_skipped_tasks(self):
        return self._get(HOIST_SKIPPED_TASKS_KEY, True)

    @hoist_skipped_tasks.setter
    def hoist_skipped_tasks(self, hoist_skipped_tasks):
        self._set(HOIST_SKIPPED_TASKS_KEY, hoist_skipped_tasks)

    @property
    def show_completed_tasks(self):
        return self._get(SHOW_COMPLETED_TASKS_KEY, False)

    @show_completed_tasks.setter
    def show_completed_tasks(self, show_completed_tasks):
        self._set(SHOW_COMPLETED_TASKS_KEY, show_completed_tasks)

    @property
    def upcoming_duration(self):
        return self._get(UPCOMING_DURATION_KEY, 7)

    @upcoming_duration.setter
    def upcoming_duration(self, upcoming_duration):
        self._set(UPCOMING_DURATION_KEY, upcoming_duration)

    @property
    def completed_duration(self):
        return self._get(COMPLETED_DURATION_KEY, 1)

    @completed_duration.setter
    def completed_duration(self, completed_duration):
        self._set(COMPLETED_DURATION_KEY, completed_duration)

    @property
    def default_taskfolder_id(self):
        return self._get(DEFAULT_TASKFOLDER_ID_KEY, None)

    @default_taskfolder_id.setter
    def default_taskfolder_id(self, default_taskfolder_id):
        self._set(DEFAULT_TASKFOLDER_ID_KEY, default_taskfolder_id)

    @property
    def date_locale(self):
        return self._get(DATE_LOCALE_KEY, None)

    @date_locale.setter
    def date_locale(self, date_locale):
        self._set(DATE_LOCALE_KEY, date_locale)
