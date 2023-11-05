import mstodo.api.base as api


def user():
    req = api.get('me')
    return req.json()
