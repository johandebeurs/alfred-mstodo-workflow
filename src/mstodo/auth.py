import logging
import atexit
import msal
from workflow import PasswordNotFound
from mstodo import config, __version__, __title__
from mstodo.util import wf_wrapper

#@TODO Check if we should use msal logger
# https://learn.microsoft.com/en-gb/azure/active-directory/develop/msal-logging-python#configure-msal-logging-level
log = logging.getLogger(__name__)
wf = wf_wrapper()

# Set up MSAL cache and config to write any changed data on program exit
cache = msal.SerializableTokenCache()
atexit.register(
    lambda: wf.save_password('msal', cache.serialize()) \
    if cache.has_state_changed else None
)

# Set up msal application for this session
app = msal.PublicClientApplication(
    client_id=config.MS_AZURE_CLIENT_ID,
    token_cache=cache,
    timeout=config.OAUTH_TIMEOUT,
    app_name=__title__,
    app_version=__version__
)

def is_authorised():
    try:
        # Attempt to load cached credentials from keychain
        cache.deserialize(wf.get_password('msal'))
        log.debug("Stored data retrieved from keychain")
        return True
    except PasswordNotFound:
        # This is the first run or the workflow has been deauthorized
        return False

def authorise():
    result = None
    accounts = app.get_accounts()

    if accounts:
        #@TODO if logged out but previously was logged in, display these
        # to the end user in the workflow UI and allow selection?
        print("You have used the following accounts. We'll choose the first one:")
        for acct in accounts:
            print(acct["username"])
        chosen = accounts[0]
        # Try to find cached token, or if it has expired, use refresh token to silently re-obtain
        result = app.acquire_token_silent(scopes=config.MS_TODO_SCOPE, account=chosen)

    if not result:
        # So no suitable token exists in cache. Let's get a new one from AAD.
        result = app.acquire_token_interactive(scopes=config.MS_TODO_SCOPE)
    if "access_token" in result:
        log.debug("Obtained access token")
        cache.add(result)
        wf.cache_data('query_event', True)
        return True

    wf.store_data('auth', 'Error: ')
    log.debug(result.get("error"))
    log.debug(result.get("error_description"))
    log.debug(result.get("correlation_id"))  # You may need this when reporting a bug
    return False

def deauthorise():
    try:
        log.debug('Deauthorising')
        wf.delete_password('msal')
    except PasswordNotFound:
        pass

def oauth_token():
    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=config.MS_TODO_SCOPE, account=accounts[0])
        if "access_token" in result:
            return result['access_token']
    else:
        return None
