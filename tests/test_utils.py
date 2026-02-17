# encoding: utf-8
"""
Test utilities for the Alfred MS ToDo Workflow test suite.

This module provides helper functions for common test assertions and operations.
"""

from typing import Any, Dict, List, Optional


def assert_item_added(wf_mock, title: Optional[str] = None, subtitle: Optional[str] = None,
                      arg: Optional[str] = None, autocomplete: Optional[str] = None,
                      valid: Optional[bool] = None, icon: Optional[str] = None) -> bool:
    """Assert that wf.add_item was called with expected parameters.

    Args:
        wf_mock: The mocked workflow instance
        title: Expected title (partial match)
        subtitle: Expected subtitle (partial match)
        arg: Expected arg value
        autocomplete: Expected autocomplete value
        valid: Expected valid value
        icon: Expected icon value

    Returns:
        True if a matching item was found

    Raises:
        AssertionError if no matching item was found
    """
    items = get_added_items(wf_mock)

    for item in items:
        if title is not None and title not in str(item.get('title', '')):
            continue
        if subtitle is not None and subtitle not in str(item.get('subtitle', '')):
            continue
        if arg is not None and item.get('arg') != arg:
            continue
        if autocomplete is not None and item.get('autocomplete') != autocomplete:
            continue
        if valid is not None and item.get('valid') != valid:
            continue
        if icon is not None and item.get('icon') != icon:
            continue
        return True

    # Build error message
    criteria = []
    if title: criteria.append(f"title containing '{title}'")
    if subtitle: criteria.append(f"subtitle containing '{subtitle}'")
    if arg: criteria.append(f"arg='{arg}'")
    if autocomplete is not None: criteria.append(f"autocomplete='{autocomplete}'")
    if valid is not None: criteria.append(f"valid={valid}")
    if icon: criteria.append(f"icon='{icon}'")

    actual_items = [f"  - title='{i.get('title')}', arg='{i.get('arg')}', autocomplete='{i.get('autocomplete')}'"
                    for i in items]
    actual_str = '\n'.join(actual_items) if actual_items else '  (no items added)'

    raise AssertionError(
        f"Expected item not found with: {', '.join(criteria)}\n"
        f"Actual items:\n{actual_str}"
    )


def get_added_items(wf_mock) -> List[Dict[str, Any]]:
    """Extract all items added to workflow from mock.

    Args:
        wf_mock: The mocked workflow instance

    Returns:
        List of dictionaries representing added items
    """
    items = []

    # Check if we have tracked items (stored as dicts by conftest track_add_item)
    if hasattr(wf_mock, '_items') and wf_mock._items:
        for item in wf_mock._items:
            # Items are stored as dictionaries in conftest.py
            if isinstance(item, dict):
                items.append(item)
            else:
                # Fallback for object-style items
                item_dict = {
                    'title': getattr(item, 'title', None),
                    'subtitle': getattr(item, 'subtitle', None),
                    'arg': getattr(item, 'arg', None),
                    'autocomplete': getattr(item, 'autocomplete', None),
                    'valid': getattr(item, 'valid', True),
                    'icon': getattr(item, 'icon', None),
                }
                items.append(item_dict)
        return items

    # Fallback to extracting from add_item call args
    for call in wf_mock.add_item.call_args_list:
        args, kwargs = call
        item = {
            'title': args[0] if len(args) > 0 else kwargs.get('title'),
            'subtitle': args[1] if len(args) > 1 else kwargs.get('subtitle'),
            'arg': kwargs.get('arg'),
            'autocomplete': kwargs.get('autocomplete'),
            'valid': kwargs.get('valid', True),
            'icon': kwargs.get('icon'),
        }
        items.append(item)
    return items


def get_item_count(wf_mock) -> int:
    """Get the number of items added to workflow.

    Args:
        wf_mock: The mocked workflow instance

    Returns:
        Number of items added
    """
    return len(get_added_items(wf_mock))


def assert_item_count(wf_mock, expected_count: int):
    """Assert the number of items added to workflow.

    Args:
        wf_mock: The mocked workflow instance
        expected_count: Expected number of items

    Raises:
        AssertionError if count doesn't match
    """
    actual_count = get_item_count(wf_mock)
    if actual_count != expected_count:
        items = get_added_items(wf_mock)
        item_titles = [i.get('title', 'unknown') for i in items]
        raise AssertionError(
            f"Expected {expected_count} items, got {actual_count}\n"
            f"Items: {item_titles}"
        )


def find_item(wf_mock, title: str) -> Optional[Dict[str, Any]]:
    """Find an item by title.

    Args:
        wf_mock: The mocked workflow instance
        title: Title to search for (exact match)

    Returns:
        Item dictionary if found, None otherwise
    """
    for item in get_added_items(wf_mock):
        if item.get('title') == title:
            return item
    return None


def find_items_containing(wf_mock, title_substring: str) -> List[Dict[str, Any]]:
    """Find all items with titles containing a substring.

    Args:
        wf_mock: The mocked workflow instance
        title_substring: Substring to search for in titles

    Returns:
        List of matching items
    """
    return [
        item for item in get_added_items(wf_mock)
        if title_substring in str(item.get('title', ''))
    ]


def assert_no_item_with_title(wf_mock, title: str):
    """Assert that no item with the given title was added.

    Args:
        wf_mock: The mocked workflow instance
        title: Title that should not exist

    Raises:
        AssertionError if an item with the title exists
    """
    item = find_item(wf_mock, title)
    if item:
        raise AssertionError(f"Found unexpected item with title '{title}'")


def assert_first_item(wf_mock, title: Optional[str] = None, **kwargs):
    """Assert properties of the first item added to workflow.

    Args:
        wf_mock: The mocked workflow instance
        title: Expected title
        **kwargs: Other expected properties

    Raises:
        AssertionError if first item doesn't match
    """
    items = get_added_items(wf_mock)
    if not items:
        raise AssertionError("No items were added to workflow")

    first_item = items[0]

    if title is not None and first_item.get('title') != title:
        raise AssertionError(
            f"First item title mismatch. Expected '{title}', got '{first_item.get('title')}'"
        )

    for key, expected_value in kwargs.items():
        actual_value = first_item.get(key)
        if actual_value != expected_value:
            raise AssertionError(
                f"First item {key} mismatch. Expected '{expected_value}', got '{actual_value}'"
            )


def assert_notify_called(mock_notify, title: Optional[str] = None, message: Optional[str] = None):
    """Assert that notify was called with expected parameters.

    Args:
        mock_notify: The mocked notify function
        title: Expected notification title (substring match)
        message: Expected notification message (substring match)

    Raises:
        AssertionError if notify wasn't called with expected params
    """
    if not mock_notify.called:
        raise AssertionError("notify was not called")

    for call in mock_notify.call_args_list:
        _, kwargs = call
        call_title = kwargs.get('title', '')
        call_message = kwargs.get('message', '')

        title_match = title is None or title in call_title
        message_match = message is None or message in call_message

        if title_match and message_match:
            return

    # Build error message
    actual_calls = [f"  - title='{c[1].get('title')}', message='{c[1].get('message')}'"
                    for c in mock_notify.call_args_list]
    actual_str = '\n'.join(actual_calls)

    raise AssertionError(
        f"notify not called with title containing '{title}' and message containing '{message}'\n"
        f"Actual calls:\n{actual_str}"
    )


def reset_workflow_items(wf_mock):
    """Reset the tracked items on a workflow mock.

    Args:
        wf_mock: The mocked workflow instance
    """
    wf_mock._items = []
    wf_mock.add_item.reset_mock()
