import logging

from datetime import date, datetime, timedelta
from workflow import Workflow
from mstodo import __githubslug__, __version__

_workflow = None

SYMBOLS = {
    'star': '★',
    'recurrence': '↻',
    'reminder': '⏰',
    'note': '✏️',
    'overdue_1x': '⚠️',
    'overdue_2x': '❗️'
}

def wf_wrapper():
    global _workflow

    if _workflow is None:
        _workflow = Workflow(
            capture_args=False,
            update_settings={
                'github_slug': __githubslug__,
                'version':__version__,
                # Check for updates daily
                #@TODO: check less frequently as the workflow becomes more
                # stable
                'frequency': 1,
                'prerelease': '-' in __version__
            }
        )

        # Override Alfred PyWorkflow logger output configuration
        _workflow.logger = logging.getLogger('workflow')

    return _workflow

def parsedatetime_calendar():
    from parsedatetime import Calendar, VERSION_CONTEXT_STYLE

    return Calendar(parsedatetime_constants(), version=VERSION_CONTEXT_STYLE)

def parsedatetime_constants():
    from parsedatetime import Constants
    from mstodo.models.preferences import Preferences

    loc = Preferences.current_prefs().date_locale or user_locale()

    return Constants(loc)

def user_locale():
    import locale

    loc = locale.getlocale(locale.LC_TIME)[0]

    if not loc:
        # In case the LC_* environment variables are misconfigured, catch
        # an exception that may be thrown
        try:
            loc = locale.getdefaultlocale()[0]
        except IndexError:
            loc = 'en_US'

    return loc

def format_time(time, fmt):
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

def short_relative_formatted_date(dt):
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

def relaunch_alfred(command='td'):
    import subprocess

    alfred_major_version = wf_wrapper().alfred_version.tuple[0]

    subprocess.call([
        '/usr/bin/env', 'osascript', '-l', 'JavaScript',
        'bin/launch_alfred.scpt', command, str(alfred_major_version)
    ])

def utc_to_local(utc_dt):
    import calendar

    # get integer timestamp to avoid precision lost. Returns naive local datetime
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    return local_dt.replace(microsecond=utc_dt.microsecond)
