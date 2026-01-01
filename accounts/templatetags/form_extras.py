from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """Append CSS classes to a form field widget."""
    attrs = field.field.widget.attrs.copy()
    existing = attrs.get("class", "")
    attrs["class"] = (existing + " " + css).strip()
    return field.as_widget(attrs=attrs)
