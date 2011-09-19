from itertools import chain

from django.core import validators
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    RadioFieldRenderer,
    MultiWidget,
    DateInput,
)
from django.forms.fields import (
    MultipleChoiceField,
    MultiValueField,
    DateField,
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

# based on Django's SplitDateTimeWidget
class DateRangeWidget(MultiWidget):
    '''\
    A Widget that has two date input boxes, for a range of dates.
    '''
    date_format = DateInput.format

    def __init__(self, attrs=None, date_format=None, date_widget=DateInput):
        widgets = (
            date_widget(attrs=attrs, format=date_format),
            date_widget(attrs=attrs, format=date_format),
        )
        super(DateRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value[0], value[1]]
        return [None, None]

class HiddenDateRangeWidget(DateRangeWidget):
    
    is_hidden = True
    
    def __init__(self, attrs=None, date_format=None):
        super(HiddenDateRangeWidget, self).__init__(attrs, date_format)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True

# based heavliy on Django's SplitDateTimeField
class DateRangeField(MultiValueField):
    widget = DateRangeWidget
    hidden_widget = DateRangeWidget
    default_error_messages = {
        'invalid_start': u'Enter a valid start date.',
        'invalid_end': u'Enter a valid end date.',
    }
    
    def __init__(self, date_widget=None, input_date_formats=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        subfield_kwargs = {
            'input_formats': input_date_formats,
        }
        fields = (
            DateField(
                error_messages= {'invalid': errors['invalid_start']},
                **subfield_kwargs
            ),
            DateField(
                error_messages= {'invalid': errors['invalid_end']},
                **subfield_kwargs
            ),
        )
        if not date_widget is None:
            widget = self.widget(date_widget=date_widget)
        super(DateRangeField, self).__init__(fields, widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        if data_list:
            # Raise a validation error if either date is empty
            # (possible if DateRangeField has required=False).
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_start'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_end'])
            return (data_list[0], data_list[1])
        return None

