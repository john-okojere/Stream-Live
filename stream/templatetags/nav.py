# stream/templatetags/nav.py
from django import template
register = template.Library()

@register.filter
def inlist(value, csv):
    return value in [s.strip() for s in (csv or "").split(",")]
