import logging
import time

from requests import codes

from mstodo import config
import mstodo.api.base as api
from mstodo.util import NullHandler

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

def taskfolders(order='display', task_counts=False):
    log.info('entered api/taskfolders')
    start = time.time()
    query = f"?$top={config.MS_TODO_PAGE_SIZE}&count=true"
    next_link = f"me/outlook/taskFolders{query}"
    taskfolders = []
    while True:
        req = api.get(next_link)
        taskfolders.extend(req.json()['value'])
        if '@odata.nextLink' in req.json():
            next_link= req.json()['@odata.nextLink'].replace(config.MS_TODO_API_BASE_URL + '/','')
        else:
            log.debug('Retrieved taskFolders in %0.3f seconds' % (time.time() - start))
            break

    if task_counts:
        for taskfolder in taskfolders:
            update_taskfolder_with_tasks_count(taskfolder)

    return taskfolders

def taskfolder(id, task_counts=False):
    req = api.get(f"me/outlook/taskFolders/{id}")
    info = req.json()

    #@TODO: run this request in parallel
    if task_counts:
        update_taskfolder_with_tasks_count(info)

    return info

def taskfolder_tasks_count(id):
    info = {}
    req = api.get(f"taskFolders/{id}/tasks?$count=true&$top=1&$filter=status+ne+'completed'")
    info['uncompleted_count'] = req.json()['@odata.count']
    req = api.get(f"taskFolders/{id}/tasks?$count=true&$top=1&$filter=status+eq+'completed'")
    info['completed_count'] = req.json()['@odata.count']

    return info

def update_taskfolder_with_tasks_count(info):
    counts = taskfolder_tasks_count(info['id'])

    info['completed_count'] = counts['completed_count'] if 'completed_count' in counts else 0
    info['uncompleted_count'] = counts['uncompleted_count'] if 'uncompleted_count' in counts else 0

    return info

def create_taskfolder(title):
    req = api.post('me/outlook/taskFolders', {'name': title})
    info = req.json()

    return req

def delete_taskfolder(id):
    req = api.delete('me/outlook/taskFolders/' + id)

    return req.status_code == codes.no_content
