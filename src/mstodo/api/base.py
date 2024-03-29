import json
import requests

from mstodo import config
from mstodo.auth import oauth_token

def _request_headers():
    _oauth_token = oauth_token()

    if _oauth_token:
        return {
            'Authorization': f"Bearer {_oauth_token}"
        }
    return None

def _report_errors(fn):
    def report_errors(*args, **kwargs):
        response = fn(*args, **kwargs)
        if response.status_code > 500:
            response.raise_for_status()
        return response
    return report_errors

def get(path, params=None):
    headers = _request_headers()
    return requests.get(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        params=params,
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def post(path, data=None):
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.post(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def put(path, data=None):
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.put(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def patch(path, data=None):
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.patch(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def delete(path, data=None):
    headers = _request_headers()
    return requests.delete(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        params=data,
        timeout=config.REQUEST_TIMEOUT
    )
