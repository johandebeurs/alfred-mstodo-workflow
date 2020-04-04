import mstodo.api.base as api


def user():
    req = api.get('me')
    user = req.json()

    return user
