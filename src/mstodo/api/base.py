import json
import logging
from typing import Optional, Dict, Any, Callable
import requests

from mstodo import config
from mstodo.auth import oauth_token

log = logging.getLogger(__name__)

def _request_headers() -> Optional[Dict[str, str]]:
    """Get HTTP headers with OAuth authorization token.

    Returns:
        Optional[Dict[str, str]]: Dictionary with Authorization header if token exists,
                                  None otherwise.
    """
    _oauth_token = oauth_token()

    if _oauth_token:
        return {
            'Authorization': f"Bearer {_oauth_token}"
        }
    return None

def safe_json_decode(response: requests.Response, context: str = "") -> Dict[str, Any]:
    """Safely decode JSON response with robust error handling.

    This function handles malformed JSON that may occur due to special characters
    in task body content or other fields. It uses multiple fallback strategies.

    Args:
        response: The HTTP response object to decode.
        context: Optional context string for logging (e.g., "tasks delta query").

    Returns:
        Dict[str, Any]: Parsed JSON data, or a safe fallback structure.

    Raises:
        ValueError: If all decoding strategies fail and response is critical.
    """
    try:
        # First attempt: standard JSON decoding
        return response.json()
    except json.JSONDecodeError as e:
        log.warning(f"JSON decode error in {context}: {e}")

        try:
            # Second attempt: Use strict=False to be more lenient with escape sequences
            return json.loads(response.text, strict=False)
        except json.JSONDecodeError as e2:
            log.warning(f"Lenient JSON decode also failed in {context}: {e2}")

            try:
                # Third attempt: Try to repair common JSON issues
                # Replace problematic escape sequences and control characters
                text = response.text

                # Remove or escape common problematic characters
                import re
                # Remove control characters except newline, tab, and carriage return
                text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

                return json.loads(text)
            except json.JSONDecodeError as e3:
                log.error(f"All JSON decode strategies failed in {context}: {e3}")
                log.error(f"Request URL: {response.url}")
                log.error(f"Response status: {response.status_code}")
                log.error(f"Response headers: {response.headers}")

                # If this is an empty or error response, return safe structure
                if response.status_code == 204 or response.status_code >= 400:
                    return {}

                # For data responses, try to return a minimal valid structure
                if '@odata' in response.text[:1000]:
                    # This looks like an OData response, return minimal structure
                    log.warning(f"Returning minimal OData structure for {context}")
                    return {'value': [], '@odata.context': 'error'}

                # Last resort: raise with helpful context
                raise ValueError(f"Unable to parse JSON response for {context}. "
                               f"Status: {response.status_code}, "
                               f"Error at char {e.pos}: {e.msg}") from e

def _report_errors(fn: Callable) -> Callable:
    """Decorator that raises HTTP errors for server errors (5xx status codes).

    Args:
        fn: The function to wrap.

    Returns:
        Callable: Wrapped function that raises for server errors.
    """
    def report_errors(*args, **kwargs):
        response = fn(*args, **kwargs)
        if response.status_code > 500:
            response.raise_for_status()
        return response
    return report_errors

def get(path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Send a GET request to the Microsoft ToDo API.

    Args:
        path: API endpoint path (relative to base URL).
        params: Optional query parameters.

    Returns:
        requests.Response: The HTTP response.
    """
    headers = _request_headers()
    return requests.get(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        params=params,
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def post(path: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Send a POST request to the Microsoft ToDo API.

    Args:
        path: API endpoint path (relative to base URL).
        data: Optional JSON data to send in request body.

    Returns:
        requests.Response: The HTTP response.
    """
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.post(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def put(path: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Send a PUT request to the Microsoft ToDo API.

    Args:
        path: API endpoint path (relative to base URL).
        data: Optional JSON data to send in request body.

    Returns:
        requests.Response: The HTTP response.
    """
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.put(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def patch(path: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Send a PATCH request to the Microsoft ToDo API.

    Args:
        path: API endpoint path (relative to base URL).
        data: Optional JSON data to send in request body.

    Returns:
        requests.Response: The HTTP response.
    """
    headers = _request_headers()
    headers['Content-Type'] = 'application/json'
    return requests.patch(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        data=json.dumps(data),
        timeout=config.REQUEST_TIMEOUT
    )

@_report_errors
def delete(path: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
    """Send a DELETE request to the Microsoft ToDo API.

    Args:
        path: API endpoint path (relative to base URL).
        data: Optional query parameters.

    Returns:
        requests.Response: The HTTP response.
    """
    headers = _request_headers()
    return requests.delete(
        config.MS_TODO_API_BASE_URL + '/' + path,
        headers=headers,
        params=data,
        timeout=config.REQUEST_TIMEOUT
    )
