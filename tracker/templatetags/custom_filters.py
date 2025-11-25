import sys
from django import template

print("Loading custom_filters.py...", file=sys.stderr)

register = template.Library()

@register.filter(name='split')
def split(value, delimiter=','):
    """Split a string by the given delimiter."""
    if not value:
        return []
    return value.split(delimiter)

@register.filter(name='trim')
def trim(value):
    """Remove leading and trailing whitespace from a string."""
    if not value:
        return ''
    return str(value).strip()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if not dictionary:
        return None
    try:
        return dictionary.get(key)
    except AttributeError:
        return None

print("Custom filters registered:", file=sys.stderr)
print("- split filter registered", file=sys.stderr)
print("- trim filter registered", file=sys.stderr)
print("- get_item filter registered", file=sys.stderr)
