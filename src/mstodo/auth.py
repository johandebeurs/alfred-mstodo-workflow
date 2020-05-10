from workflow import PasswordNotFound
import json
import logging
import requests
# from urllib import parse # this is a Py3 function
from urllib import quote_plus
from urlparse import urlparse, parse_qs

from mstodo import config
from mstodo.util import relaunch_alfred, workflow

log = logging.getLogger('mstodo')

def authorise():
    from multiprocessing import Process
    import webbrowser
    workflow().store_data('auth', 'started')

    # construct auth request url. Replace quote_plus with parse.quote for Py3
    state = new_oauth_state()
    auth_url = (config.MS_TODO_AUTH_ROOT + "/authorize"
        "?client_id=" + config.MS_TODO_CLIENT_ID +
        "&response_type=code&response_mode=query" +
        "&redirect_uri=" + quote_plus(config.MS_TODO_REDIRECT_URL) +
        "&scope=" + quote_plus((' '.join(config.MS_TODO_SCOPE)).lower()) +
        "&state=" + state
    )
    log.debug(auth_url)
    # start server to handle response
    server = Process(target=await_token)
    server.start()
    # open browser to auth
    webbrowser.open(auth_url)
    # Py3 ----
    # if __name__ == '__main__':
    #     # freeze_support()
    #     server = Process(target=await_token)
    #     server.start()
    #     # open browser to auth
    #     webbrowser.open(auth_url)

def deauthorise():
    try:
        workflow().delete_password(config.KC_OAUTH_TOKEN)
        workflow().delete_password(config.KC_REFRESH_TOKEN)
        log.debug('Deauthorising')
    except PasswordNotFound:
        pass

def is_authorised():
    if oauth_token() is None:
        log.debug('Not authorised')
        return False
    else:
        if workflow().cached_data('query_event', max_age=3600) is None:
            log.debug('No auth in last 3600s, refreshing token')
            return resolve_oauth_token(refresh_token=workflow().get_password(config.KC_REFRESH_TOKEN))
        else: 
            log.debug('Using cached OAuth token')
            return True

def handle_authorisation_url(url):
    # Parse query data & params to find out what was passed
    # parsed_url = parse.urlparse(url)
    # params = parse.parse_qs(parsed_url.query)
    params = parse_qs(urlparse(url).query)
    if 'code' in params and validate_oauth_state(params['state'][0]):
        log.debug('Valid OAuth response and state matches')
        # Request a token based on the code
        resolve_oauth_token(code=params['code'][0])
        workflow().store_data('auth', None)
        workflow().delete_password(config.KC_OAUTH_STATE)
        print('You are now logged in')
        return True
    elif 'error' in params:
        workflow().store_data('auth', 'Error: %s' % params['error'])
        print('Please try again later')
        return params['error']

    # Not a valid URL
    return False    

def oauth_token():
    try:
        return workflow().get_password(config.KC_OAUTH_TOKEN)
    except:
        return None

def client_id():
    return config.MS_TODO_CLIENT_ID

def oauth_state():
    try:
        return workflow().get_password(config.KC_OAUTH_STATE)
    except PasswordNotFound:
        return None

def new_oauth_state():
    log.debug('Creating new OAuth state')
    import random
    import string
    state_length = 20
    state = ''.join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(state_length))
    workflow().save_password(config.KC_OAUTH_STATE, state)
    return state

def validate_oauth_state(state):
    return state == oauth_state()

def resolve_oauth_token(code=None,refresh_token=None):
    token_url = config.MS_TODO_AUTH_ROOT + "/token"
    scope = config.MS_TODO_SCOPE
    data = {
        "client_id": config.MS_TODO_CLIENT_ID,
        "redirect_uri": config.MS_TODO_REDIRECT_URL,
        "scope": ' '.join(scope)
    }

    if code is not None:
        log.debug('first grant')
        data['grant_type'] = "authorization_code"
        data['code'] = code
    elif refresh_token is not None:
        log.debug('refeshing token')
        data['grant_type'] = "refresh_token"
        data['refresh_token'] = refresh_token
    
    if 'grant_type' in data:
        log.debug('Getting token from: ' + token_url)
        result = requests.post(token_url, data=data)
        log.debug('Auth response status: ' + str(result.status_code))
        if 'access_token' in result.text:
            log.debug('Saving access token in keychain')
            workflow().save_password(config.KC_OAUTH_TOKEN, result.json()['access_token'])
            workflow().save_password(config.KC_REFRESH_TOKEN, result.json()['refresh_token'])
            workflow().cache_data('query_event', True)
            return True
    
    return False

def await_token():
    import SimpleHTTPServer
    import SocketServer

    class OAuthTokenResponseHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def do_GET(self):
            auth_status = handle_authorisation_url(self.path)
            if not auth_status:
                self.path = 'www/' + self.path
            elif auth_status is True:
                self.path = 'www/authorise.html'
            else:
                self.path = 'www/decline.html'
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            relaunch_alfred()
    log.debug('Awating token on ' + config.MS_TODO_REDIRECT_URL)
    server = SocketServer.TCPServer(("", config.OAUTH_PORT), OAuthTokenResponseHandler)
    server.timeout = config.OAUTH_TIMEOUT
    server.handle_request() # waits for a single call to this URL