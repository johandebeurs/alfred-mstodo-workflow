from datetime import date, datetime, timedelta
import logging
from typing import Optional, Union

from parsedatetime import Constants, Calendar
from workflow import Workflow



_workflow = None

SYMBOLS = {
    'star': '★',
    'recurrence': '↻',
    'reminder': '⏰',
    'note': '✏️',
    'overdue_1x': '⚠️',
    'overdue_2x': '❗️'
}

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(module)s : %(lineno)d - %(message)s'


def wf_wrapper() -> Workflow:
    """Get or create the singleton Workflow instance.

    Returns:
        Workflow: The configured Alfred-PyWorkflow Workflow instance.
    """
    global _workflow

    if _workflow is None:
        _workflow = Workflow(
            capture_args=False,
            update_settings={
                # GitHub slug and version are read from info.plist
                'frequency': 1, # Check for updates daily
            }
        )

        logger = _workflow.logger

        for h in logger.handlers:
            if isinstance(h,logging.handlers.RotatingFileHandler):
                logger.removeHandler(h)

        if any(['background' in x for x in _workflow.args]):
            destination = _workflow.cachefile(f"{_workflow.bundleid}-background.log")
        else:
            destination = _workflow.logfile

        handler = logging.handlers.TimedRotatingFileHandler(
            destination,
            when='D',
            interval=1,
            backupCount=7
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.addFilter(lambda record: record.name.split('.')[0] not in ('msal', 'urllib3'))
        logger.addHandler(handler)

        _workflow.logger = logger

        # Set GitHub slug from info.plist webaddress
        url = _workflow.info.get('webaddress', '')
        if url:
            _workflow._update_settings['github_slug'] = url.replace('https://github.com/', '')

        # Set prerelease flag based on version from info.plist
        if _workflow.version:
            _workflow._update_settings['prerelease'] = '-' in str(_workflow.version)

    return _workflow

def parsedatetime_calendar() -> Calendar:
    """Create a parsedatetime Calendar instance with user's locale settings.

    Returns:
        Calendar: Configured parsedatetime Calendar instance.
    """
    from parsedatetime import VERSION_CONTEXT_STYLE

    return Calendar(parsedatetime_constants(), version=VERSION_CONTEXT_STYLE)

def parsedatetime_constants() -> Constants:
    """Create parsedatetime Constants with user's locale preferences.

    Returns:
        Constants: parsedatetime Constants configured with user's locale.
    """
    from mstodo.models.preferences import Preferences

    loc = Preferences.current_prefs().date_locale or user_locale()

    return Constants(loc)

def user_locale() -> str:
    """Get the user's locale setting.

    Returns:
        str: The user's locale identifier (e.g., 'en_US'), defaults to 'en_US' if not found.
    """
    import locale
    import os

    loc = locale.getlocale(locale.LC_TIME)[0]

    if not loc:
        # Fall back to environment variables, stripping encoding suffix
        for env_var in ('LC_ALL', 'LC_CTYPE', 'LANG'):
            env_val = os.environ.get(env_var)
            if env_val:
                loc = env_val.split('.')[0]
                break

    return loc or 'en_US'

def format_time(time: datetime, fmt: str) -> str:
    """Format a time using locale-specific formatting.

    Args:
        time: The datetime object to format.
        fmt: The format identifier from parsedatetime locale timeFormats.

    Returns:
        str: The formatted time string with leading zeros stripped.
    """
    cnst = parsedatetime_constants()

    expr = cnst.locale.timeFormats[fmt]
    expr = (expr
            .replace('HH', '%H')
            .replace('h', '%I')
            .replace('mm', '%M')
            .replace('ss', '%S')
            .replace('a', '%p')
            .replace('z', '%Z')
            .replace('v', '%z'))

    return time.strftime(expr).lstrip('0')

def short_relative_formatted_date(dt: Union[date, datetime]) -> str:
    """Format a date as a short relative string.

    Args:
        dt: The date or datetime to format.

    Returns:
        str: A relative date string like 'today', 'tomorrow', 'yesterday',
             or a formatted date string like 'Wed, Mar 3' or 'Mar 3, 2016'.
    """
    dt_date = dt.date() if isinstance(dt, datetime) else dt
    today = date.today()
    # Mar 3, 2016. Note this is a naive date in local TZ
    date_format = '%b %d, %Y'

    if dt_date == today:
        return 'today'
    if dt_date == today + timedelta(days=1):
        return 'tomorrow'
    if dt_date == today - timedelta(days=1):
        return 'yesterday'
    if dt_date.year == today.year:
        # Wed, Mar 3
        date_format = '%a, %b %d'

    return dt.strftime(date_format)

def relaunch_alfred(command: str = 'td') -> None:
    """Relaunch Alfred with a specific command.

    Args:
        command: The Alfred command to execute (default: 'td').

    Side effects:
        Launches Alfred via AppleScript/JavaScript automation.
    """
    import subprocess

    alfred_major_version = wf_wrapper().alfred_version.tuple[0]

    subprocess.call([
        '/usr/bin/env', 'osascript', '-l', 'JavaScript',
        'bin/launch_alfred.scpt', command, str(alfred_major_version)
    ])

def utc_to_local(utc_dt: datetime) -> datetime:
    """Convert a UTC datetime to local timezone.

    Args:
        utc_dt: A datetime in UTC timezone.

    Returns:
        datetime: A naive datetime in local timezone with microseconds preserved.
    """
    import calendar

    # get integer timestamp to avoid precision lost. Returns naive local datetime
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def get_delta_token(resource_key: str) -> Optional[str]:
    """Get stored delta token for a resource.

    Args:
        resource_key: The resource identifier (e.g., 'lists', 'tasks_{list_id}').

    Returns:
        Optional[str]: The delta token if stored, None otherwise.
    """
    return wf_wrapper().cached_data(f'delta_token_{resource_key}', max_age=0)

def set_delta_token(resource_key: str, token: Optional[str]) -> None:
    """Store delta token for a resource.

    Args:
        resource_key: The resource identifier (e.g., 'lists', 'tasks_{list_id}').
        token: The delta token to store, or None to clear it.
    """
    if token is None:
        # Clear the token
        wf_wrapper().cache_data(f'delta_token_{resource_key}', None)
    else:
        wf_wrapper().cache_data(f'delta_token_{resource_key}', token)
