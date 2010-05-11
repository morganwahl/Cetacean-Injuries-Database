from django import forms
from django.forms.fields import EMPTY_VALUES
from models import DateTime

class DateTimeForm(forms.ModelForm):
    
    def clean_hour(self):
        hour = self.cleaned_data['hour']
        if not hour in EMPTY_VALUES:
            if hour < 0:
                raise forms.ValidationError('gave negative hours!')
            if hour > 23:
                raise forms.ValidationError('gave too many hours!')
        return hour
        
    def clean_minute(self):
        minute = self.cleaned_data['minute']
        if not minute in EMPTY_VALUES:
            if minute < 0:
                raise forms.ValidationError('gave negative minutes!')
            if minute > 59:
                raise forms.ValidationError('gave too many minutes!')
        return minute
            
    def clean_second(self):
        second = self.cleaned_data['second']
        if not second in EMPTY_VALUES:
            if second < 0:
                raise forms.ValidationError('gave negative seconds!')
            # FYI python datetime doesn't like leap-seconds
            if second > 59:
                raise forms.ValidationError('gave too many seconds!')
        return second

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

class NiceDateTimeForm(DateTimeForm):

    # TODO fill in time from an instance
    
    # note that we can't use a TimeField since datetime.time doesn't have a way
    # to indicate unknown hours minutes and seconds
    time = forms.CharField(
        required=False,
    )
    
    def clean_time(self):
        timestring = self.cleaned_data['time']
        parts = timestring.split(':') + [None, None]
        (hour, minute, second) = parts[0:3]

        if not hour in EMPTY_VALUES:
            hour = int(hour)
        else:
            hour = None
        self.cleaned_data['hour'] = hour
        self.cleaned_data['hour'] = self.clean_hour()

        if not minute in EMPTY_VALUES:
            minute = int(minute)
        else:
            minute = None
        self.cleaned_data['minute'] = minute
        self.cleaned_data['minute'] = self.clean_minute()

        if not second in EMPTY_VALUES:
            second = float(second)
        else:
            second = None
        self.cleaned_data['second'] = second
        self.cleaned_data['second'] = self.clean_second()

        return {
            'hour': hour,
            'minute': minute,
            'second': second,
        }
    
    def save(self, commit=True):
        instance = super(NiceDateTimeForm, self).save(commit)
        # because they were excluded we need to save these manually
        instance.hour = self.cleaned_data['time']['hour']
        instance.minute = self.cleaned_data['time']['minute']
        instance.second = self.cleaned_data['time']['second']
        if commit:
            instance.save()
        return instance
    
    class Meta(DateTimeForm.Meta):
        exclude = ('hour', 'minute', 'second')

