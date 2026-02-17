import logging
import atexit
from typing import Optional

import msal
from workflow import PasswordNotFound
from mstodo import config
from mstodo.util import wf_wrapper

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
    app_name="Alfred-MSToDo",
    app_version=str(wf.version)
)

def is_authorised() -> bool:
    """Check if the user is currently authorized with Microsoft ToDo.

    Returns:
        bool: True if cached credentials exist in keychain, False otherwise.
    """
    try:
        # Attempt to load cached credentials from keychain
        cache.deserialize(wf.get_password('msal'))
        return True
    except PasswordNotFound:
        # This is the first run or the workflow has been deauthorized
        return False

def authorise() -> bool:
    """Authorize the user with Microsoft ToDo using OAuth interactive flow.

    Attempts to use cached tokens first, falling back to interactive authentication
    if no suitable token exists.

    Returns:
        bool: True if authorization was successful, False otherwise.

    Side effects:
        - Caches the obtained token in the workflow keychain
        - Sets 'query_event' cache data to True on success
        - Stores error information in workflow data on failure
    """
    result = None
    accounts = app.get_accounts()

    if accounts:
        #@TODO if logged out but previously was logged in, display these
        # to the end user in the workflow UI and allow selection?
        log.debug("You have used the following accounts. We'll choose the first one:")
        for acct in accounts:
            log.debug(acct["username"])
        chosen = accounts[0]
        # Try to find cached token, or if it has expired, use refresh token to silently re-obtain
        log.debug("Silently obtaining MSAL access token")
        result = app.acquire_token_silent(scopes=config.MS_TODO_SCOPE, account=chosen)

    if not result:
        # So no suitable token exists in cache. Let's get a new one from AAD.
        log.debug("No/Expired token found. Refreshing MSAL access token")
        result = app.acquire_token_interactive(scopes=config.MS_TODO_SCOPE)
    if "access_token" in result:
        log.debug("Obtained access token")
        cache.add(result)
        wf.cache_data('query_event', True)
        return True

    log.error(result.get("error"))
    log.error(result.get("error_description"))
    log.error(result.get("correlation_id"))  # You may need this when reporting a bug
    return False

def deauthorise() -> None:
    """Remove stored authorization credentials from the workflow keychain.

    Silently succeeds if no credentials were found.
    """
    try:
        log.info('Deauthorising and deleting MacOS Keychain entry')
        wf.delete_password('msal')
    except PasswordNotFound:
        pass

def oauth_token() -> Optional[str]:
    """Get OAuth access token for Microsoft ToDo API.

    Returns:
        Optional[str]: Access token if available, None otherwise.

    Side effects:
        Calls deauthorise() if token refresh fails due to invalid credentials.
    """
    accounts = app.get_accounts()
    if not accounts:
        return None

    result = app.acquire_token_silent_with_error(
        scopes=config.MS_TODO_SCOPE,
        account=accounts[0]
    )

    if result is None:
        # Cache is empty but no error occurred
        return None

    if 'error' in result:
        error = result.get('error')
        error_description = result.get('error_description', 'No description')
        log.warning(f"Token refresh failed: {error} - {error_description}")

        # Check if this is an error that requires re-authentication
        if error in ['invalid_grant', 'interaction_required', 'invalid_client',
                     'unauthorized_client', 'consent_required']:
            log.info(f"Deauthorizing due to unrecoverable error: {error}")
            deauthorise()

        return None

    return result.get('access_token')
