import re

from django import forms
from models import Location

class LocationForm(forms.ModelForm):
    
    def clean_coordinates(self):
        value = self.cleaned_data['coordinates']
        if not value:
            return ''
        
        (lat, lng) = re.search("(-?[\d\.]+)\s*,\s*(-?[\d\.]+)", value).group(1, 2)
        
        lat = float(lat)
        lat = max(lat, -90)
        lat = min(lat, 90)
        
        lng = float(lng)
        # add 180 so that 179 E is now 359 E and 180 W is zero
        lng += 180
        # take it mod 360
        lng %= 360
        # and subtract the 180 back off
        lng -= 180
        
        return "%.16f,%.16f" % (lat,lng)

    class Meta:
        model = Location
