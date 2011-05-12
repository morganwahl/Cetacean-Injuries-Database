from django.db.models import Q
from django import template

register = template.Library()

@register.filter
def visible_to(docs, user):
    if user.is_superuser:
        return docs
    
    # value should be a queryset of Documents
    q = Q(visible_to__pk=user.pk)
    q |= Q(visible_to__pk__isnull=True)
    
    return docs.filter(q)
    
