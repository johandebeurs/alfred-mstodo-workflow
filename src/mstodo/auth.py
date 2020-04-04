# from workflow import PasswordNotFound
from mstodo import config
from mstodo.util import relaunch_alfred, workflow

import json
import logging
import requests
from urllib import parse

def authorize():
    from multiprocessing import Process
    import webbrowser

    # workflow().store_data('auth', 'started')

    # construct auth request url
    state = new_oauth_state()
    auth_url = (config.MS_TODO_AUTH_ROOT + "/authorize"
        "?client_id=" + config.MS_TODO_CLIENT_ID +
        "&response_type=code&response_mode=query" +
        "&redirect_uri=" + parse.quote(config.MS_TODO_REDIRECT_URL) +
        "&scope=" + parse.quote((' '.join(config.MS_TODO_SCOPE)).lower()) +
        "&state=" + state
    )
    # start server to handle response
    if __name__ == '__main__':
        # freeze_support()
        server = Process(target=await_token)
        server.start()
        # open browser to auth
        webbrowser.open(auth_url)

def deauthorize():
    try:
        workflow().delete_password(config.KC_OAUTH_TOKEN)
    except PasswordNotFound:
        pass

def is_authorised():
    return oauth_token() is not None

def handle_authorization_url(url):
    # Parse query data & params to find out what was passed
    parsed_url = parse.urlparse(url)
    params = parse.parse_qs(parsed_url.query)
    if 'code' in params: # and validate_oauth_state(params['state'][0]):
        # Request a token based on the code
        resolve_oauth_token(code=params['code'][0])
        # workflow().store_data('auth', None)

        print('You are now logged in')
        return True
    elif 'error' in params:
        # workflow().store_data('auth', 'Error: %s' % params['error'])
        print('Please try again later')
        return params['error']

    # Not a valid URL
    return False    

def oauth_token():
    try:
        # return workflow().get_password(config.KC_OAUTH_TOKEN)
        return config.OAUTH_TOKEN
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
    import random
    import string
    state_length = 20
    state = ''.join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(state_length))
    # workflow().save_password(config.KC_OAUTH_STATE, state)
    return state

def validate_oauth_state(state):
    return state == oauth_state()

def resolve_oauth_token(code=None,refresh_token=None):
    token_url = config.MS_TODO_AUTH_ROOT + "/token"
    scope = config.MS_TODO_SCOPE
    scope.append('offline_access')
    data = {
        "client_id": config.MS_TODO_CLIENT_ID,
        "redirect_uri": config.MS_TODO_REDIRECT_URL,
        "scope": ' '.join(scope)
    }
    if code is not None:
        data['grant_type'] = "authorization_code"
        data['code'] = code
    elif refresh_token is not None:
        data['grant_type'] = "refresh_token"
        data['code'] = refresh_token
    
    logging.info('Getting token from: ' + token_url)
    logging.info(data)
    result = requests.post(token_url, data=data)
    
    if 'access_token' in result.text:
        access_token = result.json()['access_token']
        refresh_token = result.json()['refresh_token']
        logging.info('Access token: ' + access_token)
        logging.info('Refesh token: ' + refresh_token)
        config.KC_OAUTH_TOKEN = access_token
        config.KC_REFRESH_TOKEN = refresh_token

        # workflow().save_password(config.KC_OAUTH_TOKEN, access_token)
        # workflow().save_password(config.KC_REFRESH_TOKEN, refresh_token)
        # workflow().delete_password(config.KC_OAUTH_STATE)

def await_token():
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class OAuthTokenResponseHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            auth_status = handle_authorization_url(self.path)
            if not auth_status:
                self.path = 'www/' + self.path
            elif auth_status is True:
                self.path = 'www/authorize.html'
            else:
                self.path = 'www/decline.html'
            SimpleHTTPRequestHandler.do_GET(self)
            # relaunch_alfred()

    httpd = HTTPServer((config.OAUTH_SERVER, config.OAUTH_PORT), OAuthTokenResponseHandler)
    # import ssl
    # httpd.socket = ssl.wrap_socket(httpd.socket, certfile='localhost.pem', server_side=True)
    httpd.timeout = config.OAUTH_TIMEOUT
    httpd.handle_request() # waits for a single call to this URL

logging.basicConfig(level=logging.DEBUG)

if not is_authorised():
    logging.info("No suitable token exists in cache. Request user to sign in.")
    authorize()