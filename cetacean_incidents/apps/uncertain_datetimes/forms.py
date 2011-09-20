from calendar import month_name
from copy import deepcopy
import re

from django.core.exceptions import ValidationError
from django.db.models import Q
from django import forms
from django.forms.util import ErrorList
from django.forms.widgets import (
    MultiWidget,
    Widget,
)
from django.template.loader import render_to_string
from django.utils import copycompat as copy
from django.utils.safestring import mark_safe

from cetacean_incidents.apps.search_forms.fields import (
    MatchOption,
    MatchOptions,
    QueryField,
)

from . import UncertainDateTime

# similiar to Django's MultiWidget, but not really a subclass
class UncertainDateTimeWidget(Widget):
    """
    A Widget that splits an UncertainDateTime input into 7 <input type="text"> inputs.
    """
    
    def __init__(self, subwidgets, attrs=None):
        
        self.subwidgets = subwidgets

        super(UncertainDateTimeWidget, self).__init__(attrs)
    
    def render(self, name, value, attrs=None):
        # value is a dictionary with keys corresponding to self.subwidgets
        if not isinstance(value, dict):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        # TODO move this ordering info into UncertainDateTimeWidget
        # really we should be using lists with key-lookup
        for subname in (
            'year',
            'month',
            'day',
            'time',
            'hour',
            'minute',
            'second',
            'microsecond',
        ):
            subwidget = self.subwidgets[subname]
            
            try:
                widget_value = value[subname]
            except KeyError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, subname))
            
            rendering = subwidget.render(name + '_%s' % subname, widget_value, final_attrs)
            
            output.append({
                'name': subname,
                'widget': subwidget,
                'rendering': rendering,
            })
        
        return mark_safe(render_to_string(
            'uncertain_datetime_widget.html',
            {
                'widget': self,
                'subwidgets': output
            }
        ))
    
    @classmethod
    def id_for_label(self, id_):
        # TODO
        return id_
    
    def value_from_datadict(self, data, files, name):
        value = {}
        for widget_name, widget in self.subwidgets.items():
            value[widget_name] = widget.value_from_datadict(data, files, name + '_%s' % widget_name)
        return value
    
    def _has_changed(self, initial, data):
        if initial.year != data['year']:
            return True
        if initial.month != data['month']:
            return True
        if initial.day != data['day']:
            return True
        if initial.hour != data['hour']:
            return True
        if initial.minute != data['minute']:
            return True
        if initial.second != data['second']:
            return True
        if initial.microsecond != data['microsecond']:
            return True
        return False

    def decompress(self, value):
        if not value:
            return {}
        if value is dict:
            return value
        return {
            'year': value.year,
            'month': value.month,
            'day': value.day,
            'hour': value.hour,
            'time': value.time_unicode(unknown_char=None),
            'minute': value.minute,
            'second': value.second,
            'microsecond': value.microsecond,
        }

    def _get_media(self):
        raise NotImplementedError("UncertainDateTimeWidget._get_media")
        
    def __deepcopy__(self, memo):
        obj = super(UncertainDateTimeWidget, self).__deepcopy__(memo)
        obj.subwidgets = copy.deepcopy(self.subwidgets)
        return obj

class UncertainDateTimeHiddenWidget(UncertainDateTimeWidget):
    """
    A Widget that splits an UncertainDateTime input into 7 <input type="hidden"> inputs.
    """
    is_hidden = True

# similiar to Django's ComboField and MultiValueField, but not really a subclass
# of them
class UncertainDateTimeField(forms.Field):

    default_subfield_classes = {
        'year': forms.IntegerField,
        'month': forms.TypedChoiceField,
        'day': forms.IntegerField,
        'hour': forms.IntegerField,
        'time': forms.CharField,
        'minute': forms.IntegerField,
        'second': forms.IntegerField,
        'microsecond': forms.IntegerField,
    }
    
    default_subfield_kwargs = {
        'year': {
            'widget': forms.TextInput(attrs={'size': 4}),
            'required': False,
            'min_value': UncertainDateTime.MINYEAR,
            'max_value': UncertainDateTime.MAXYEAR,
            'error_messages': {
                'required': 'Year is required.',
                'invalid': 'Year must be a whole number.',
                'min_value': 'Year must be greater than {0}.'.format(UncertainDateTime.MINYEAR - 1),
                'max_value': 'Year must be less than {0}.'.format(UncertainDateTime.MAXYEAR + 1),
            }
        },
        'month': {
            'required': False,
            'choices': (
                ('', '<unknown month>'),
            ) + tuple(enumerate(month_name))[1:],
            'coerce': int,
            'empty_value': None,
            'error_messages': {
                'required': 'Month is required.',
            },
        },
        # TODO UncertainDateTime needs to raise a ValueError when given Feb 31st
        'day': {
            'widget': forms.TextInput(attrs={'size': 2}),
            'required': False,
            'min_value': UncertainDateTime.MINDAY, 
            'max_value': UncertainDateTime.maxday(),
            'error_messages': {
                'required': 'Day is required.',
                'invalid': 'Day must be a whole number.',
                'min_value': 'Day must be greater than or equal to {0}.'.format(UncertainDateTime.MINDAY),
                'max_value': 'Day must be less than or equal to {0}.'.format(UncertainDateTime.maxday()),
            },
        },
        'time': {
            'widget': forms.TextInput(attrs={'size': 15}),
            'required': False,
            'error_messages': {
                'required': 'Time is required.',
            },
        },
        'hour': {
            'widget': forms.TextInput(attrs={'size': 2}),
            'required': False,
            'min_value': UncertainDateTime.MINHOUR, 
            'max_value': UncertainDateTime.MAXHOUR,
            'error_messages': {
                'required': 'Hour is required.',
                'invalid': 'Hour must be a whole number.',
                'min_value': 'Hour must be greater than or equal to {0}.'.format(UncertainDateTime.MINHOUR),
                'max_value': 'Hour must be less than or equal to {0}.'.format(UncertainDateTime.MAXHOUR),
            },
        },
        'minute': {
            'widget': forms.TextInput(attrs={'size': 2}),
            'required': False,
            'min_value': UncertainDateTime.MINMINUTE, 
            'max_value': UncertainDateTime.MAXMINUTE,
            'error_messages': {
                'required': 'Minute is required.',
                'invalid': 'Minute must be a whole number.',
                'min_value': 'Minute must be greater than or equal to {0}.'.format(UncertainDateTime.MINMINUTE),
                'max_value': 'Minute must be less than or equal to {0}.'.format(UncertainDateTime.MAXMINUTE),
            },
        },
        'second': {
            'widget': forms.TextInput(attrs={'size': 2}),
            'required': False,
            'min_value': UncertainDateTime.MINSECOND, 
            'max_value': UncertainDateTime.MAXSECOND,
            'error_messages': {
                'required': 'Second is required.',
                'invalid': 'Second must be a whole number.',
                'min_value': 'Second must be greater than or equal to {0}.'.format(UncertainDateTime.MINSECOND),
                'max_value': 'Second must be less than or equal to {0}.'.format(UncertainDateTime.MAXSECOND),
            },
        },
        'microsecond': {
            'widget': forms.TextInput(attrs={'size': 6}),
            'required': False,
            'min_value': UncertainDateTime.MINMICROSECOND, 
            'max_value': UncertainDateTime.MAXMICROSECOND,
            'error_messages': {
                'required': 'Microsecond is required.',
                'invalid': 'Microsecond must be a whole number.',
                'min_value': 'Microsecond must be greater than or equal to {0}.'.format(UncertainDateTime.MINMICROSECOND),
                'max_value': 'Microsecond must be less than or equal to {0}.'.format(UncertainDateTime.MAXMICROSECOND),
            },
        },
    }
    
    def __init__(self, required_subfields=tuple(), hidden_subfields=tuple(), *args, **kwargs):
        self.subfield_classes = deepcopy(self.default_subfield_classes)

        self.subfield_kwargs = deepcopy(self.default_subfield_kwargs)
        
        for fieldname in required_subfields:
            self.subfield_kwargs[fieldname]['required'] = True
        for fieldname in hidden_subfields:
            self.subfield_kwargs[fieldname]['widget'] = forms.HiddenInput

        subfields = {}
        for fieldname in self.subfield_classes.keys():
            subfields[fieldname] = self.subfield_classes[fieldname](**self.subfield_kwargs[fieldname])
        
        self.subfields = subfields
        
        subfield_widgets = {}
        subfield_hidden_widgets = {}
        for subfield_name, subfield in self.subfields.items():
            subfield_widgets[subfield_name] = subfield.widget
            subfield_hidden_widgets[subfield_name] = subfield.hidden_widget
        self.widget = UncertainDateTimeWidget(subwidgets=subfield_widgets)
        self.hidden_widgets = UncertainDateTimeHiddenWidget(subwidgets=subfield_hidden_widgets)
        
        super(UncertainDateTimeField, self).__init__(*args, **kwargs)
    
    def validate(self, value):
        return value
    
    def clean(self, value):
        '''\
        value is assumed to be a dictionary of values with keys corresponding
        to the ones in self.subfields. Each value is validated against it's 
        corresponding field.
        '''
        clean_data = {}
        errors = ErrorList()
        
        if value is None:
            return value
        
        if not isinstance(value, dict):
            raise ValidationError(self.error_messages['invalid'])
        
        for fieldname, field in self.subfields.items():
            if not fieldname in value.keys():
                if field.required:
                    raise ValidationError(field.error_messages['required'])
                else:
                    continue
            
            try:
                clean_data[fieldname] = field.clean(value[fieldname])
            except ValidationError, e:
                errors.extend(e.messages)
        
        # TODO put this in a proper UncertainTimeField form field
        if 'time' in clean_data.keys():
            if clean_data['time']:
                match = re.search(r'(?P<hour>\d*)(:(?P<minute>\d*))?(:(?P<second>\d*))?(\.(?P<microsecond>\d*))?', clean_data['time'])
                if match:
                    fields = match.groupdict()
                    def int_or_none(i):
                        if i is None or i == '':
                            return None
                        return int(i)
                    clean_data['hour'] = int_or_none(fields['hour'])
                    clean_data['minute'] = int_or_none(fields['minute'])
                    clean_data['second'] = int_or_none(fields['second'])
                    clean_data['microsecond'] = int_or_none(fields['microsecond'])
            del clean_data['time']
        
        try:
            out = self.compress(clean_data)
        except ValueError, e:
            errors.extend([e.message])
        
        if errors:
            raise ValidationError(errors)
        
        self.validate(out)
        return out
        
    def compress(self, data_dict):
        return UncertainDateTime(**data_dict)

class UncertainDateTimeRangeWidget(MultiWidget):
    def __init__(self, required_subfields=tuple(), hidden_subfields=tuple(), attrs=None):
        self.subfield_classes = deepcopy(UncertainDateTimeField.default_subfield_classes)

        self.subfield_kwargs = deepcopy(UncertainDateTimeField.default_subfield_kwargs)
        
        for fieldname in required_subfields:
            self.subfield_kwargs[fieldname]['required'] = True
        for fieldname in hidden_subfields:
            self.subfield_kwargs[fieldname]['widget'] = forms.HiddenInput

        subfields = {}
        for fieldname in self.subfield_classes.keys():
            subfields[fieldname] = self.subfield_classes[fieldname](**self.subfield_kwargs[fieldname])
        
        self.subfields = subfields
        
        subfield_widgets = {}
        subfield_hidden_widgets = {}
        for subfield_name, subfield in self.subfields.items():
            subfield_widgets[subfield_name] = subfield.widget
            subfield_hidden_widgets[subfield_name] = subfield.hidden_widget
        self.widget = UncertainDateTimeWidget(subwidgets=subfield_widgets)
        self.hidden_widgets = UncertainDateTimeHiddenWidget(subwidgets=subfield_hidden_widgets)

        widgets = (
            date_widget(attrs=attrs),
            date_widget(attrs=attrs),
        )
        super(UncertainDateTimeRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value[0], value[1]]
        return [None, None]

class HiddenUncertainDateTimeRangeWidget(UncertainDateTimeRangeWidget):
    
    is_hidden = True
    
    def __init__(self, attrs=None):
        super(HiddenUncertainDateTimeRangeWidget, self).__init__(attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True

# based heavliy on Django's SplitDateTimeField
class UncertainDateTimeRangeField(forms.MultiValueField):
    widget = UncertainDateTimeRangeWidget
    hidden_widget = HiddenUncertainDateTimeRangeWidget
    default_error_messages = {
        'invalid_start': u'Enter a valid start date.',
        'invalid_end': u'Enter a valid end date.',
    }
    
    def __init__(self, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        subfield_kwargs = {
            'required_subfields': ('year',),
            'hidden_subfields': ('microsecond', 'second', 'minute', 'hour'),
        }
        fields = (
            UncertainDateTimeField(
                error_messages= {'invalid': errors['invalid_start']},
                **subfield_kwargs,
            ),
            UncertainDateTimeField(
                error_messages= {'invalid': errors['invalid_end']},
                **subfield_kwargs,
            ),
        )
        super(UncertainDateTimeRangeField, self).__init__(fields, *args, **kwargs)
    
    def compress(self, data_list):
        if data_list:
            # Raise a validation error if either date is empty
            # (possible if UncertainDateTimeRangeField has required=False).
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_start'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_end'])
            return (data_list[0], data_list[1])
        return None

class UncertainDateTimeFieldQuery(QueryField):
    default_match_options = MatchOptions([
        MatchOption('before', 'possibly during or before',
            UncertainDateTimeField(),
        ),
        MatchOption('during', 'during',
            UncertainDateTimeField(),
        ),
        MatchOption('after', 'possibly during or after',
            UncertainDateTimeField(),
        ),
        MatchOption('between', 'possibly on or after and possibly before',
            UncertainDateTimeRangeField(),
        ),
    ])
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.get_attname()
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            from models import UncertainDateTimeField as UncertainDateTimeModelField            
            if lookup_type == 'during':
                return UncertainDateTimeModelField.get_sametime_q(lookup_value, lookup_fieldname)
            elif lookup_type == 'before':
                return UncertainDateTimeModelField.get_before_q(lookup_value, lookup_fieldname)
            elif lookup_type == 'after':
                return UncertainDateTimeModelField.get_after_q(lookup_value, lookup_fieldname)
            elif lookup_type == 'between':
                q = UncertainDateTimeModelField.get_after_q(lookup_value[0], lookup_fieldname)
                q &= UncertainDateTimeModelField.get_before_q(lookup_value[1], lookup_fieldname)
                return q
                
        return Q()

