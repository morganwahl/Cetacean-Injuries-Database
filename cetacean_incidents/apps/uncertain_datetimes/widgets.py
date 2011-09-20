from copy import deepcopy

from django.forms.widgets import (
    MultiWidget,
    Widget,
)
from django.template.loader import render_to_string
from django.utils import copycompat as copy
from django.utils.safestring import mark_safe

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

class UncertainDateTimeRangeWidget(MultiWidget):
    def __init__(self, fields, attrs=None):
        widgets = tuple(map(lambda field: field.widget, fields))
        super(UncertainDateTimeRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value[0], value[1]]
        return [None, None]

