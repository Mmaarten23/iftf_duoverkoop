"""
Custom template tags for the IF Theater Festival application.
"""
from django import template
from typing import List, Set

register = template.Library()


@register.simple_tag
def unique_performance_names(performances: List) -> List[str]:
    """
    Extract unique performance names from a list of performance objects.

    Args:
        performances: List of performance objects with a 'name' attribute

    Returns:
        List of unique performance names, sorted alphabetically
    """
    names: Set[str] = set()
    for performance in performances:
        names.add(performance.name)

    return sorted(list(names))

