from mstodo.models.preferences import Preferences
from mstodo.util import wf_wrapper

_ICON_THEME = None

def alfred_is_dark() -> bool:
    """Determine if Alfred is using a dark theme.

    Returns:
        bool: True if Alfred's theme background is dark, False otherwise.
    """
    # Formatted rgba(255,255,255,0.90)
    background_rgba = wf_wrapper().alfred_env['theme_background']
    if background_rgba:
        rgb = [int(x) for x in background_rgba[5:-6].split(',')]
        return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255 < 0.5
    return False


def icon_theme() -> str:
    """Get the icon theme to use based on preferences or Alfred theme.

    Returns:
        str: Either 'light' or 'dark' depending on preferences or Alfred theme.
    """
    global _ICON_THEME
    if not _ICON_THEME:
        prefs = Preferences.current_prefs()

        if prefs.icon_theme:
            _ICON_THEME = prefs.icon_theme
        else:
            _ICON_THEME = 'light' if alfred_is_dark() else 'dark'

    return _ICON_THEME

_ICON_PATH = f"icons/{icon_theme()}/"

ACCOUNT = _ICON_PATH + 'account.png'
BACK = _ICON_PATH + 'back.png'
CALENDAR = _ICON_PATH + 'calendar.png'
CANCEL = _ICON_PATH + 'cancel.png'
CHECKBOX = _ICON_PATH + 'task.png'
CHECKBOX_SELECTED = _ICON_PATH + 'task_completed.png'
CHECKMARK = _ICON_PATH + 'checkmark.png'
DISCUSS = _ICON_PATH + 'discuss.png'
DOWNLOAD = _ICON_PATH + 'download.png'
HASHTAG = _ICON_PATH + 'hashtag.png'
HELP = _ICON_PATH + 'help.png'
HIDDEN = _ICON_PATH + 'hidden.png'
INBOX = _ICON_PATH + 'inbox.png'
INFO = _ICON_PATH + 'info.png'
LINK = _ICON_PATH + 'link.png'
LIST = _ICON_PATH + 'list.png'
LIST_NEW = _ICON_PATH + 'list_new.png'
NEXT_WEEK = _ICON_PATH + 'next_week.png'
OPEN = _ICON_PATH + 'open.png'
PAINTBRUSH = _ICON_PATH + 'paintbrush.png'
PREFERENCES = _ICON_PATH + 'preferences.png'
RADIO = _ICON_PATH + 'radio.png'
RADIO_SELECTED = _ICON_PATH + 'radio_selected.png'
RECURRENCE = _ICON_PATH + 'recurrence.png'
REMINDER = _ICON_PATH + 'reminder.png'
SEARCH = _ICON_PATH + 'search.png'
SORT = _ICON_PATH + 'sort.png'
STAR = _ICON_PATH + 'star.png'
STAR_REMOVE = _ICON_PATH + 'star_remove.png'
SYNC = _ICON_PATH + 'sync.png'
TASK = _ICON_PATH + 'task.png'
TASK_COMPLETED = _ICON_PATH + 'task_completed.png'
TODAY = _ICON_PATH + 'today.png'
TOMORROW = _ICON_PATH + 'tomorrow.png'
TRASH = _ICON_PATH + 'trash.png'
UPCOMING = _ICON_PATH + 'upcoming.png'
VISIBLE = _ICON_PATH + 'visible.png'
YESTERDAY = _ICON_PATH + 'yesterday.png'
