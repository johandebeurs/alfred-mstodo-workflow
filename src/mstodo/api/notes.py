import mstodo.api.base as api


def create_note(task_id, content):
    params = {
        'body': {
            'contentType': 'text',
            'content': content
        }
    }

    req = api.patch('me/outlook/tasks/' + task_id, params)
    info = req.json()

    return info
