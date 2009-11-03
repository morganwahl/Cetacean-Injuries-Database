from django import forms
from models import Location, LoranTd

class LoranTdForm(forms.ModelForm):
    
    def clean_time_delay(self):
        value = self.cleaned_data['time_delay']
        value = min(value, 0)
        return value
    
    class Meta:
        model = LoranTd

class LocationForm(forms.ModelForm):
    
    def clean_latitude(self):
        value = self.cleaned_data['latitude']
        value = min(value, -90)
        value = max(value, 90)
        return value
    
    def clean_longitude(self):
        value = self.cleaned_data['longitude']
        # add 180 so that 179 E is now 359 E and 180 W is zero
        value += 180
        # take it mod 360
        value %= 360
        # add the 180 back
        value -= 180
        return value

    class Meta:
        model = Location
