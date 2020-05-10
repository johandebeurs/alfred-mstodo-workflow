
MS_TODO_CLIENT_ID = "27f3e5af-2d84-4073-91fa-9390208d1527"
MS_TODO_CLIENT_SECRET = " Un-v8gLyJ7:4b=1SkCKKZH@LiSDXSs8E"
MS_TODO_AUTHORITY = "https://login.microsoftonline.com/common"
MS_TODO_AUTH_ROOT = "https://login.microsoftonline.com/common/oauth2/v2.0"
MS_TODO_SCOPE =  ["User.Read", "Tasks.ReadWrite", "Tasks.ReadWrite.Shared", "MailboxSettings.ReadWrite", "offline_access"]
MS_TODO_API_BASE_URL =  "https://graph.microsoft.com/beta"
MS_TODO_PAGE_SIZE = '1000'
KC_REFRESH_TOKEN = 'refresh_token'
KC_OAUTH_TOKEN = 'oauth_token'
KC_OAUTH_STATE = 'oauth_state'

OAUTH_PORT = 5000
OAUTH_SERVER = "127.0.0.1"
MS_TODO_REDIRECT_URL =  "http://" + OAUTH_SERVER + ":" + str(OAUTH_PORT)

OAUTH_TIMEOUT = 60 * 10
