from django import template

register = template.Library()


@register.filter
def zip_lists(a, b):
    """Zip two lists together for templates"""
    return zip(a, b)
