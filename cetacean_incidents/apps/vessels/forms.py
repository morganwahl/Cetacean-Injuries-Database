from django import forms
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from models import VesselInfo
from cetacean_incidents.apps.countries.models import Country
from django.conf import settings

class FlagSelect(forms.Select):
    '''\
    Extension of a Select widget that inserts a little flag image for the 
    currently selected country.
    '''
    
    class Media:
        js = ('jquery/jquery-1.3.2.min.js',)
    
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''

        # insert a nice bit of javascript to show the flag of the country
        # selected
        # TODO check that attrs['id'] is set?
        output = [ '''\
        <script type="text/javascript">
            jQuery(function(){
                var select = $("#%(id)s > select");
                select.change(function(event){
                    // remove the old flag first
                    $("#%(id)s > img.flag").remove()
                    if ( select.val() == '' )
                        return;
                    var icon_url = "%(media)sflags/" + select.val().toLowerCase()  + ".png";
                    // set the margin to 1/4 the image size
                    $("#%(id)s").prepend("<img style=\\"margin: 4px;\\" class=\\"flag\\" src=\\"" + icon_url + "\\">");
                });
                // trigger the event to load the flag for the initial value.
                select.change();
            });
        </script>
        ''' % {
            'id': attrs ['id'],
            'media': settings.MEDIA_URL,
        }]

        span_attrs = self.build_attrs(attrs)
        select_attrs = self.build_attrs(name=name)
        output.append(u'<span%s><select%s>' % (flatatt(span_attrs), flatatt(select_attrs)))
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select></span>')
        return mark_safe(u'\n'.join(output))

class FlagField(forms.ModelChoiceField):
    '''\
    A ModelChoiceField that uses FlagSelect as a widget, and Country.objects.all()
    as a default queryset.
    '''
    
    widget = FlagSelect
    
    def __init__(self, queryset=None, *args, **kwargs):
        if queryset is None:
            queryset = Country.objects.all()
        return super(FlagField, self).__init__(queryset=queryset, *args, **kwargs)

class VesselAdminForm(forms.ModelForm):
    
    # note that we need to set things like required and help_text manually; it
    # won't be based on the Vessel.flag's attributes.
    flag = FlagField(required= False)
    
    class Meta:
        model = VesselInfo

VesselInfoForm = VesselAdminForm

