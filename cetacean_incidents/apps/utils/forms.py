from itertools import chain

from django.core import validators
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    RadioFieldRenderer,
)
from django.forms.fields import (
    MultipleChoiceField,
)
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

class InlineRadioFieldRenderer(RadioFieldRenderer):
    def render(self):
        """Outputs a <span> for this set of radio fields."""
        return mark_safe(
            u'<span>\n%s\n</span>' % u'\n'.join(
                [u'<span>%s</span>' % force_unicode(w) for w in self]
            )
        )

class InlineCheckboxSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        # based entirely on CheckboxSelectMultiple.render, except doesn't use a
        # <ul>
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<span>']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<span><label%s>%s %s</label></span>' % (label_for, rendered_cb, option_label))
        output.append(u'</span>')
        return mark_safe(u'\n'.join(output))

class TypedMultipleChoiceField(MultipleChoiceField):
    # based on TypedChoiceField
    def __init__(self, *args, **kwargs):
        self.coerce = kwargs.pop('coerce', lambda val: val)
        self.empty_value = kwargs.pop('empty_value', '')
        super(TypedMultipleChoiceField, self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        '''\
        Validate that each value is in self.choices and can be coerced to the
        right type.
        '''
        
        value = super(TypedMultipleChoiceField, self).to_python(value)
        super(TypedMultipleChoiceField, self).validate(value)
        
        for i, v in enumerate(value):
            if v == self.empty_value or v in validators.EMPTY_VALUES:
                value[i] = self.empty_value
            try:
                v = self.coerce(v)
            except (ValueError, TypeError, ValidationError):
                raise ValidationError(self.error_messages['invalid_choice'] % {'value': v})
            value[i] = v
        
        return value
    
    def validate(self, value):
        pass

