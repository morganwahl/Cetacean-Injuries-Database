from itertools import chain

from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.html import escape, conditional_escape

from django import forms
from django.forms.widgets import CheckboxSelectMultiple, CheckboxInput
from django.forms.models import ModelChoiceIterator, ModelMultipleChoiceField

from models import get_roots

class HierarchicalCheckboxSelectMultiple(CheckboxSelectMultiple):
    '''\
    Takes a choices arg similiar to the Select widget, except optgroup labels
    are interpreted as choices (i.e. a pair (<value>, <label>)) and the options
    in the optgroup are sub-choices of that choice.
    '''
    
    _example_select_choices = (
        ('value1', 'label1'),
        ('value2', 'label2'),
        (
            'optgroup1-label', 
            (
                ('value3', 'label3'),
                ('value4', 'label4'),
            ),
        ),
        ('value5', 'label5'),
    )
    
    _example_heirarchical_choices = (
        ('value1', 'label1'),
        ('value2', 'label2'),
        (
            ('value3', 'label3'),
            (
                ('value3-subvalue1', 'label3-sublabel1'),
                ('value2-subvalue1', 'label3-sublabel2'),
            ),
        ),
        ('value4', 'label4'),
    )
    
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])

        final_attrs = self.build_attrs(attrs, name=name)
        
        return mark_safe(self._render_ul(chain(self.choices, choices), final_attrs, str_values))

    def _render_ul(self, choices, final_attrs, str_values):
        ul = [u'<ul>']
        for i, (option_value, option_label) in enumerate(choices):
            if isinstance(option_value, tuple):
                subchoices = option_label
                (option_value, option_label) = option_value
                ul.append(self._render_li(option_value, option_label, final_attrs, unicode(i), str_values, subchoices))
            else:
                ul.append(self._render_li(option_value, option_label, final_attrs, unicode(i), str_values))
        ul.append(u'</ul>')
        return u'\n'.join(ul)

    def _render_li(self, option_value, option_label, final_attrs, suffix, str_values, subchoices=()):
        li = [u'<li>']
        # If an ID attribute was given, add the suffix,
        # so that the checkboxes don't all have the same ID attribute.
        has_id = 'id' in final_attrs
        if has_id:
            sub_attrs = dict(final_attrs, id= '%s_%s' % (final_attrs['id'], suffix))
            label_for = u' for="%s"' % sub_attrs['id']
        else:
            sub_attrs = final_attrs
            label_for = ''

        cb = CheckboxInput(sub_attrs, check_test=lambda value: value in str_values)
        option_value = force_unicode(option_value)
        rendered_cb = cb.render(sub_attrs['name'], option_value)
        option_label = conditional_escape(force_unicode(option_label))
        li.append(u'<label%s>%s %s</label>' % (label_for, rendered_cb, option_label))
        if subchoices:
            li.append(self._render_ul(subchoices, sub_attrs, str_values))
        li.append(u'</li>')
        return u'\n'.join(li)
        
class DAGModelChoiceIterator(ModelChoiceIterator):

    def _qs_to_choices(self, qs):
        choices = []
        for root in get_roots(qs.all()):
            children = root.subtypes
            if children.count():
                choices.append((
                    self.choice(root),
                    self._qs_to_choices(children.all())
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
        # choices dynamically. Return a fresh QuerySetIterator that has not been
        # consumed. Note that we're instantiating a new QuerySetIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        return DAGModelChoiceIterator(self)

    choices = property(_get_choices, ModelMultipleChoiceField._set_choices)
    
