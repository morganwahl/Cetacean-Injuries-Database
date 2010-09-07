from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode

class Datepicker(forms.widgets.DateInput):
    '''\
    The Django DateInput widget plus the jQuery-UI Datepicker.
    '''
    
    def render(self, name, value, attrs=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        
        # assumes the the 
        # django.template.loaders.app_directories.load_template_source is being 
        # used, which is the default.
        return render_to_string('date_widget.html', {
            'input_id': final_attrs['id'],
            'final_attrs': forms.util.flatatt(final_attrs),
        })
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE,)}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE)

