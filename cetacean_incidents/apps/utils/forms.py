from itertools import chain

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core import validators
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    RadioFieldRenderer,
    MultiWidget,
    DateInput,
)
from django.forms.forms import (
    BoundField,
)
from django.forms.fields import (
    MultipleChoiceField,
    MultiValueField,
    DateField,
)
from django.forms.models import ModelForm
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
        else:
            widget = kwargs.get('widget', None)
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

class RestModelForm(ModelForm):

    # allow reStructuredText in help_text
    # TODO is this kosher to override?
    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row, rest_help_text=True, hide_help_text=True):
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []

        for name, field in self.fields.items():
            html_class_attr = ''
            bf = BoundField(self, field, name)
            bf_errors = self.error_class([conditional_escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend([u'(Hidden field %s) %s' % (name, force_unicode(e)) for e in bf_errors])
                hidden_fields.append(unicode(bf))
            else:
                # Create a 'class="..."' atribute if the row should have any
                # CSS classes applied.
                css_classes = bf.css_classes()
                if css_classes:
                    html_class_attr = ' class="%s"' % css_classes

                if errors_on_separate_row and bf_errors:
                    output.append(error_row % force_unicode(bf_errors))

                if bf.label:
                    label = conditional_escape(force_unicode(bf.label))
                    # Only add the suffix if the label does not end in
                    # punctuation.
                    if self.label_suffix:
                        if label[-1] not in ':?.!':
                            label += self.label_suffix
                    label = bf.label_tag(label) or ''
                else:
                    label = ''

                if field.help_text:
                    help_text = force_unicode(field.help_text)
                    if rest_help_text:
                        try:
                            from django.contrib.markup.templatetags.markup import restructuredtext
                            help_text = restructuredtext(help_text)
                        except ImportError:
                            pass
                    if hide_help_text:
                        # put the help text in a div that the
                        # help_text_hider.js script can find
                        help_text = u"""
                            <div class="help_text">
                              %s
                            </div>
                        """ % help_text
                    help_text = help_text_html % help_text
                else:
                    help_text = u''

                output.append(normal_row % {
                    'errors': force_unicode(bf_errors),
                    'label': force_unicode(label),
                    'field': unicode(bf),
                    'help_text': help_text,
                    'html_class_attr': html_class_attr
                })

        if top_errors:
            output.insert(0, error_row % force_unicode(top_errors))

        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = u''.join(hidden_fields)
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and
                # insert the hidden fields.
                if not last_row.endswith(row_ender):
                    # This can happen in the as_p() case (and possibly others
                    # that users write): if there are only top errors, we may
                    # not be able to conscript the last row for our purposes,
                    # so insert a new, empty row.
                    last_row = (normal_row % {'errors': '', 'label': '',
                                              'field': '', 'help_text':'',
                                              'html_class_attr': html_class_attr})
                    output.append(last_row)
                output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
            else:
                # If there aren't any rows in the output, just append the
                # hidden fields.
                output.append(str_hidden)
        return mark_safe(u'\n'.join(output))

    class Media:
        css = {'all': ('helptext_hider.css',)}
        js = (settings.JQUERY_FILE, 'helptext_hider.js')
    
    
