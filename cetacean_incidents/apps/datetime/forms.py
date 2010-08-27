from django import forms
from django.forms.fields import EMPTY_VALUES
from models import DateTime

class DateTimeForm(forms.ModelForm):
            
    def clean(self):
        # note that if a clean_field func raised an exception, data may not 
        # have the corresponding key
    
        data = self.cleaned_data
        # make sure all the fields are there
        if data['day']:
            if not data['month']:
                raise forms.ValidationError('day given without month')
            # check if the day makes sense
            df = forms.DateField(required=False)
            df.clean('%i-%02i-%02i' % (data['year'], data['month'], data['day']))
        
        # don't forget, hour, minute, and second can be zero, so we can't just
        # test if they're True
        if 'second' in data and not data['second'] in EMPTY_VALUES:
            if 'minute' not in data or data['minute'] in EMPTY_VALUES:
                raise forms.ValidationError('second given without minute')
        if 'minute' in data and not data['minute'] in EMPTY_VALUES:
            if 'hour' not in data or data['hour'] in EMPTY_VALUES:
                raise forms.ValidationError('minute given without hour')
        
        # note that giving only a year and a hour is OK, so you can indicate
        # time-of-day without knowing what day it was exactly

        return data
    
    class Meta:
        model = DateTime
        widgets = {
            'year': forms.TextInput(attrs={'size':'4'}),
            'day': forms.TextInput(attrs={'size':'2'}),
        }

class NiceDateTimeForm(DateTimeForm):

    def __init__(self, *args, **kwargs):
        super(NiceDateTimeForm, self).__init__(*args, **kwargs)
        # if an initial value wasn't given for 'time', get one from the
        # instance. note that a new instance was already created if one wasn't
        # passed in
        if not 'time' in self.initial:
            time_data = forms.models.model_to_dict(self.instance, ('hour', 'minute', 'second'))
            time = ''
            if time_data['hour'] not in EMPTY_VALUES:
                time = u'%02i' % time_data['hour']
            if time_data['minute'] not in EMPTY_VALUES:
                time += ':' + u'%02i' % time_data['minute']
            if time_data['second'] not in EMPTY_VALUES:
                time += ':' + u'%02i' % time_data['second']
            self.initial['time'] = time
    
    # note that we can't use a TimeField since datetime.time doesn't have a way
    # to indicate unknown hours minutes and seconds
    time = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={'size':'8'}),
    )
    
    def clean_time(self):
        timestring = self.cleaned_data['time']
        parts = timestring.split(':') + [None, None]
        (hour, minute, second) = parts[0:3]

        # note that DateTime's clean() will handle most validation

        if not hour in EMPTY_VALUES:
            hour = int(hour)
        else:
            hour = None

        if not minute in EMPTY_VALUES:
            minute = int(minute)
        else:
            minute = None

        if not second in EMPTY_VALUES:
            second = float(second)
        else:
            second = None

        return {
            'hour': hour,
            'minute': minute,
            'second': second,
        }
    
    def clean(self):
        # act like these fields weren't hidden, then call super's clean
        self.cleaned_data['hour'] = self.cleaned_data['time']['hour']
        self.cleaned_data['minute'] = self.cleaned_data['time']['minute']
        self.cleaned_data['second'] = self.cleaned_data['time']['second']
        return super(NiceDateTimeForm, self).clean()
    
    class Meta(DateTimeForm.Meta):
        widgets = DateTimeForm.Meta.widgets
        widgets.update({
            'hour': forms.HiddenInput,
            'minute': forms.HiddenInput,
            'second': forms.HiddenInput,
        })

