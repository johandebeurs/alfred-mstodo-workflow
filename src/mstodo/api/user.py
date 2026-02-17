from typing import Dict, Any
import mstodo.api.base as api


def user() -> Dict[str, Any]:
    """Get the current user's information from Microsoft Graph API.

    Returns:
        Dict[str, Any]: User information dictionary from the API.
    """
    req = api.get('me')
    return api.safe_json_decode(req, "user info")
