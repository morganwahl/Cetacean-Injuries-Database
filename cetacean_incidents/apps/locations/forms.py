from decimal import Decimal
import re

from django import forms
from django.db.models import Q
from django.template.loader import render_to_string

from cetacean_incidents.apps.merge_form.forms import MergeForm

from cetacean_incidents.apps.search_forms.forms import SearchForm
from cetacean_incidents.apps.search_forms.fields import (
    MatchOption,
    MatchOptions,
    QueryField,
)

from models import Location
from utils import dms_to_dec
from widgets import CountryWidget

class LocationForm(forms.ModelForm):
    
    class Meta:
        model = Location

class LocationMergeForm(MergeForm):
    
    def as_table(self):
        return render_to_string(
            'location_merge_form_as_table.html',
            {
                'object_name': Location._meta.verbose_name,
                'object_name_plural': Location._meta.verbose_name_plural,
                'destination': self.destination,
                'source': self.source,
                'form': self,
            }
        )
    
    class Meta:
        model = Location

Location.merge_form_class = LocationMergeForm

class NiceLocationForm(LocationForm):
    
    def __init__(self, *args, **kwargs):
        super(NiceLocationForm, self).__init__(*args, **kwargs)
        if self.instance.coordinates:
            (lat,lng) = self.instance.coords_pair
            self.initial['coordinates_lat_input'] = lat
            self.initial['coordinates_lng_input'] = lng
            
    # TODO surely there's a library to take care of this; perferably with
    # localization...
    _DMS_RE = re.compile(
        # don't forget to double-escape unicode strings
        u'^[^NSEW\\d\\-\u2212\\.]*'
        + r'(?P<pre_dir>[NSEW])?' # match a direction
        + u'[^\\-\u2212\\d]*'
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
        + u'[^\\d\\-\u2212\\.]*$',
        re.IGNORECASE
    )
    
    @staticmethod
    def _clean_coordinate(value, is_lat):
        parsed = NiceLocationForm._DMS_RE.search(value)
        if not parsed:
            raise forms.ValidationError(u"can't figure out format of coordinate")
        
        def clean_direction(direction):
            for d in 'NSEW':
                if re.match('%s' % d, direction, re.IGNORECASE):
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
            neg = (
                pre_dir == 'S'
                or pre_dir == 'W'
                or post_dir == 'S'
                or post_dir == 'W'
            )
        
        def not_none(x,y):
            if x is None:
                return y
            return x

        degrees = reduce(not_none, parsed.group('dms_degrees', 'dm_degrees', 'd_degrees'))
        if degrees:
            degrees = Decimal(degrees) # we don't need to check for exceptions, 
                                     # since any string that matched the 
                                     # pattern will parse as a float
        else:
            degrees = Decimal(0)
        
        minutes = reduce(not_none, parsed.group('dms_minutes', 'dm_minutes'))
        if minutes:
            minutes = Decimal(minutes)
        else:
            minutes = Decimal(0)
        
        seconds = parsed.group('dms_seconds')
        if seconds:
            seconds = Decimal(seconds)
        else:
            seconds = Decimal(0)

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
        return self._clean_coordinate(value, is_lat=True)

    coordinates_lng_input = forms.CharField(
        required= False,
        label= "Longitude",
        help_text= u"the longitude as \u201c71.5 W\u201d or \u201c-71.5\u201d or \u201c71 30' 00.0\" W\u201d, etc"
    )

    def clean_coordinates_lng_input(self):
        value = self.cleaned_data['coordinates_lng_input']
        if not re.search('\S', value, re.UNICODE):
            return None
        return self._clean_coordinate(value, is_lat=False)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        
        # note that cleaned_data may not have keys for everything if there were
        # validation errors
        if not 'coordinates_lat_input' in cleaned_data:
            cleaned_data['coordinates_lat_input'] = tuple()
        if not 'coordinates_lng_input' in cleaned_data:
            cleaned_data['coordinates_lng_input'] = tuple()
        
        # error if longitude was given, but lat wasn't.
        if bool(cleaned_data['coordinates_lat_input']) ^ bool(cleaned_data['coordinates_lng_input']):
            raise forms.ValidationError('either give both latitude and longitude, or neither')
        
        if bool(cleaned_data['coordinates_lat_input']) and bool(cleaned_data['coordinates_lng_input']):
            # act like the coordinates field wasn't hidden, then call super's 
            # clean
            self.cleaned_data['coordinates'] = "%s,%s" % (
                dms_to_dec(self.cleaned_data['coordinates_lat_input']),
                dms_to_dec(self.cleaned_data['coordinates_lng_input']),
            )
        else:
            self.cleaned_data['coordinates'] = ''

        return super(NiceLocationForm, self).clean()
    
    # don't forget Meta classes aren't inherited
    class Meta:
        model = Location
        exclude = ('roughness',)
        widgets = {
            'coordinates': forms.HiddenInput,
            'country': CountryWidget,
        }

from cetacean_incidents.apps.countries.models import Country
    
class CountryQueryField(QueryField):
    
    default_match_options = MatchOptions([
        MatchOption('or', 'one of',
            forms.ModelMultipleChoiceField(
                queryset= Country.objects.filter(iso__in=['US', 'CA']),
                widget= forms.CheckboxSelectMultiple,
            ),
        ),
    ])
    
    blank_option = True
    
    def query(self, value, prefix=None):
        if not value is None:
            lookup_type, lookup_value = value
            lookup_fieldname = self.model_field.name
            if not prefix is None:
                lookup_fieldname = prefix + '__' + lookup_fieldname
            
            if lookup_type == 'or':
                # lookup_value is a list of Countries
                if len(lookup_value) == 0:
                    return Q()
                
                q = Q(**{lookup_fieldname + '__in': lookup_value})
                
                return q

        return super(CountryQueryField, self).query(value, prefix)

class LocationSearchForm(SearchForm):
    
    _f = Location._meta.get_field('country')
    country = CountryQueryField(
        model_field= _f,
        label= _f.verbose_name.capitalize(),
        required= False,
        help_text= _f.help_text,
    )
    
    class Meta:
        model = Location
        exclude = ('id', 'import_notes', 'roughness', 'coordinates')

