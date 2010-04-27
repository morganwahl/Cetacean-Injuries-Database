import re

from django import forms
from models import Location
from utils import MILE_IN_METERS

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

class NiceLocationForm(LocationForm):
    
    # TODO surely there's a library to take care of this; perferably with
    # localization...
    _dms_re = re.compile(
        u'^[^NSEW\\d\\-\u2212\\.]*'
        + r'(?P<pre_dir>[NSEW])?' # match a direction
        + r'\D*'
        # don't forget to double-escape, since it's a unicode string
        + u'(?P<sign>[\\-\u2212])?' # match a minus sign
        + r'[^\d\.]*' 
        + r'('
        + r'(?P<d_degrees>\d*\.?\d+)'
        + r'|'
        + r'(?P<dm_degrees>\d+)[^\d\.]+(?P<dm_minutes>\d*\.?\d+)'
        + r'|'
        + r'(?P<dms_degrees>\d+)[^\d\.]+(?P<dms_minutes>\d+)[^\d\.]+(?P<dms_seconds>\d*\.?\d+)'
        + r')'
        + r'[^\dNSEW]*'
        + r'(?P<post_dir>[NSEW])?' # match a direction
        + u'[^NSEW\\d\\-\u2212\\.]*$',
        re.IGNORECASE
    )
    
    def _clean_coordinate(self, value, is_lat):
        import pdb; pdb.set_trace()
        parsed = self._dms_re.search(value)
        if not parsed:
            raise forms.ValidationError(u"can't figure out format of coordinate")
        
        def clean_direction(direction):
            for d in 'NSEW':
                if re.match('(?i%s)' % d, direction):
                    direction = unicode(d)
                    break
            if is_lat and direction not in ('N', 'S'):
                raise forms.ValidationError(u"%s given for latitude" % direction)
            elif (not is_lat) and direction not in ('E', 'W'):
                raise forms.ValidationError(u"%s given for longitude" % direction)
            return direction

        # note that these groups may be empty string or None, doesn't matter.

        if parsed.group('pre_dir'):
            pre_dir = clean_direction(parsed.group('pre_dir'))
        else:
            pre_dir = None
            
        if parsed.group('post_dir'):
            post_dir = clean_direction(parsed.group('post_dir'))
            if pre_dir and (pre_dir != post_dir):
                raise forms.ValidationError(u"can't figure out format of coordinate: two different directions (%s and %s)" % (pre_dir, post_dir))
        else:
            post_dir = None
        
        if parsed.group('sign'):
            neg = True
            if neg and (pre_dir or post_dir):
                raise forms.ValidationError(u"can't figure out format of coordinate: both minus sign and direction")
        else:
            neg = False
        
        def not_none(x,y):
            if x is None:
                return y
            return x

        degrees = reduce(not_none, parsed.group('dms_degrees', 'dm_degrees', 'd_degrees'))
        if degrees:
            degrees = float(degrees) # we don't need to check for exceptions, 
                                     # since any string that matched the pattern 
                                     # will parse as a float
        else:
            degrees = 0.0
        
        minutes = reduce(not_none, parsed.group('dms_minutes', 'dm_minutes'))
        if minutes:
            minutes = float(minutes)
        else:
            degrees = 0.0
        
        seconds = parsed.group('dms_seconds')
        if seconds:
            seconds = float(seconds)
        else:
            seconds = 0.0

        return (neg, degrees, minutes, seconds)
                
    # replace 'coordinates' with a couple of free-form text-inputs.
    coordinates_lat_input = forms.CharField(
        required= False,
        label= "Latitude",
        help_text= u"the latitude as \u201c42.323342 S\u201d or \u201c-42.323342\u201d or \u201c42 19' 24.04\" S\u201d, etc"
    )

    def clean_coordinates_lat_input(self):
        value = self.cleaned_data['coordinates_lat_input']
        if not re.search('\S', value, re.UNICODE):
            return None
        return self._clean_coordinate(value, True)

    coordinates_lng_input = forms.CharField(
        required= False,
        label= "Longitude",
        help_text= u"the longitude as \u201c71.5 W\u201d or \u201c-71.5\u201d or \u201c71 30' 00.0\" W\u201d, etc"
    )

    def clean_coordinates_lng_input(self):
        value = self.cleaned_data['coordinates_lng_input']
        if not re.search('\S', value, re.UNICODE):
            return None
        return self._clean_coordinate(value, False)
    
    _roughness_field = Location._meta.get_field('roughness')
    _roughnesses = (
            ('', '<unknown>'),
            ('10', "good GPS fix"),
            ('50', "not so good GPS fix"),
            (unicode(15 * MILE_IN_METERS), "general area (e.g. Mass Bay)"), # Cap Cod Bay is roughly 30mi across
            (unicode(325 * MILE_IN_METERS), "region (e.g. the Northeast)"), # 650mi from the Chesapeake to Nova Scotia
    )
    _initial_roughness = ''
    if _roughness_field.default:
        _initial_roughness = _roughness_field.default
        if not _roughness_field.blank:
            _roughnesses = _roughnesses[1:]
        
    roughness = forms.ChoiceField(
        choices= _roughnesses,
        initial= _initial_roughness,
        # TODO onion distance?
        required= _roughness_field.blank != True,
        label= _roughness_field.verbose_name.capitalize(),
        help_text= u'''\
            A guess as to the distance these coordinates are off by, at most.
        ''',
    )
    
    def clean_roughness(self):
        if self.cleaned_data['roughness'] == '':
            return None
        return float(self.cleaned_data['roughness'])
    
    def clean(self):
        cleaned_data = self.cleaned_data
    
        # error if longitude was given, but lat wasn't.
        if bool(self.cleaned_data['coordinates_lat_input']) ^ bool(self.cleaned_data['coordinates_lng_input']):
            raise forms.ValidationError('either give both latitude and longitude, or neither')

        return cleaned_data
    
    def save(self, commit=True, *args, **kwargs):
        # have the superclass instantiate a Location
        location = super(NiceLocationForm, self).save(commit=False, *args, **kwargs)
        
        location.dms_coords_pair = (self.cleaned_data['coordinates_lat_input'], self.cleaned_data['coordinates_lng_input'])
        
        if commit:
            location.save()
            location.save_m2m()
        
        return location

    # don't forget Meta classes aren't inherited
    class Meta:
        model = Location
        exclude = ('coordinates')
    
