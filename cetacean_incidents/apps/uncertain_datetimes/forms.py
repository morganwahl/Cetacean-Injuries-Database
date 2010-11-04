from django import forms
from django.forms.util import ErrorList
from django.utils.safestring import mark_safe

from . import UncertainDateTime

# based on Django's SplitDateTimeWidget
class UncertainDateTimeWidget(forms.MultiWidget):
    """
    A Widget that splits an UncertainDateTime input into 7 <input type="text"> inputs.
    """
    
    def __init__(self, attrs=None):

        year_attrs = {'size': '4'}
        month_attrs = {'size': '2'}
        day_attrs = {'size': '2'}

        hour_attrs = {'size': '2'}
        minute_attrs = {'size': '2'}
        second_attrs = {'size': '2'}
        microsecond_attrs = {'size': '6'}

        if not attrs is None:
            year_attrs.update(attrs)
            month_attrs.update(attrs)
            day_attrs.update(attrs)
            hour_attrs.update(attrs)
            minute_attrs.update(attrs)
            second_attrs.update(attrs)
            microsecond_attrs.update(attrs)

        widgets = (
            forms.TextInput(attrs=year_attrs), # year
            forms.TextInput(attrs=month_attrs), # month
            forms.TextInput(attrs=day_attrs), # day

            forms.TextInput(attrs=hour_attrs), # hour
            forms.TextInput(attrs=minute_attrs), # minute
            forms.TextInput(attrs=second_attrs), # second
            forms.TextInput(attrs=microsecond_attrs), # microsecond
        )
        super(UncertainDateTimeWidget, self).__init__(widgets, attrs)

    def format_output(self, rendered_widgets):
        return '%s-%s-%s %s:%s:%s.%s' % tuple(rendered_widgets)

    def decompress(self, value):
        if value is None:
            return [None] * 7
        return [value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond]

# based on Django's SplitHiddenDateTimeWidget
class UncertainHiddenDateTimeWidget(UncertainDateTimeWidget):
    """
    A Widget that splits an UncertainDateTime input into 7 <input type="hidden"> inputs.
    """
    is_hidden = True

    def __init__(self, attrs=None):
        super(UncertainHiddenDateTimeWidget, self).__init__(attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True

class UncertainDateTimeField(forms.MultiValueField):
    widget = UncertainDateTimeWidget
    hidden_widget = UncertainHiddenDateTimeWidget
    default_error_messages = {
        'invalid_date': u'Enter a valid date.',
        'invalid_year': u'Enter a valid year.',
        'invalid_month': u'Enter a valid month.',
        'invalid_day': u'Enter a valid day.',
        'invalid_hour': u'Enter a valid hour.',
        'invalid_minute': u'Enter a valid minute.',
        'invalid_second': u'Enter a valid second.',
        'invalid_microsecond': u'Enter a valid microsecond.',
    }

    # intended to be overriden in subclasses
    required_fields = set()

    def __init__(self, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        fields = (
            forms.IntegerField(
                required= 'year' in self.required_fields,
                min_value= UncertainDateTime.MINYEAR, 
                max_value= UncertainDateTime.MAXYEAR,
                error_messages= {'invalid': errors['invalid_year']},
            ),
            forms.IntegerField(
                required= 'month' in self.required_fields,
                min_value=UncertainDateTime.MINMONTH, 
                max_value=UncertainDateTime.MAXMONTH,
                error_messages= {'invalid': errors['invalid_month']},
            ),
            forms.IntegerField(
                required= 'day' in self.required_fields,
                min_value=UncertainDateTime.MINDAY, 
                max_value=UncertainDateTime.maxday(),
                error_messages= {'invalid': errors['invalid_day']},
            ),

            forms.IntegerField(
                required= 'hour' in self.required_fields,
                min_value=UncertainDateTime.MINHOUR, 
                max_value=UncertainDateTime.MAXHOUR,
                error_messages= {'invalid': errors['invalid_hour']},
            ),
            forms.IntegerField(
                required= 'minute' in self.required_fields,
                min_value=UncertainDateTime.MINMINUTE, 
                max_value=UncertainDateTime.MAXMINUTE,
                error_messages= {'invalid': errors['invalid_minute']},
            ),
            forms.IntegerField(
                required= 'second' in self.required_fields,
                min_value=UncertainDateTime.MINSECOND, 
                max_value=UncertainDateTime.MAXSECOND,
                error_messages= {'invalid': errors['invalid_second']},
            ),
            forms.IntegerField(
                required= 'microsecond' in self.required_fields,
                min_value=UncertainDateTime.MINMICROSECOND, 
                max_value=UncertainDateTime.MAXMICROSECOND,
                error_messages= {'invalid': errors['invalid_microsecond']},
            ),
        )
        super(UncertainDateTimeField, self).__init__(fields, *args, **kwargs)

    def clean(self, value):
        # based on MultiValueField's clean()
        
        clean_data = []
        errors = ErrorList()
        
        if value and not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages['invalid'])
        
        if not value:
            if self.required_fields:
                raise ValidationError(self.error_messages['required_%s' % self.required_fields[0]])
            else:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                return self.compress([])

        for i, field in enumerate(self.fields):
            try:
                field_value = value[i]
            except IndexError:
                field_value = None
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError, e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        return out
    
    def compress(self, data_list):
        return UncertainDateTime(*data_list)

