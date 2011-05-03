from django.forms.models import (
    ModelChoiceIterator,
    ModelMultipleChoiceField,
)

from models import get_roots
from widgets import HierarchicalCheckboxSelectMultiple

class DAGModelChoiceIterator(ModelChoiceIterator):

    def _qs_to_choices(self, qs):
        choices = []
        for root in get_roots(qs.all()):
            children = root.subtypes
            if children.count():
                choices.append((
                    self.choice(root),
                    self._qs_to_choices(children.all()),
                ))
            else:
                choices.append(self.choice(root))
        
        return tuple(choices)

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)
        if self.field.cache_choices:
            if self.field.choice_cache is None:
                self.field.choice_cache = self._qs_to_choices(self.queryset)
            for choice in self.field.choice_cache:
                yield choice
        else:
            for choice in self._qs_to_choices(self.queryset):
                yield choice

class DAGField(ModelMultipleChoiceField):
    """A MultipleChoiceField whose choices are a DAGNode QuerySet."""
    
    widget = HierarchicalCheckboxSelectMultiple
    
    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices

        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh QuerySetIterator that has not
        # been consumed. Note that we're instantiating a new QuerySetIterator 
        # *each* time _get_choices() is called (and, thus, each time 
        # self.choices is accessed) so that we can ensure the QuerySet has not 
        # been consumed. This construct might look complicated but it allows
        # for lazy evaluation of the queryset.
        return DAGModelChoiceIterator(self)

    choices = property(_get_choices, ModelMultipleChoiceField._set_choices)

