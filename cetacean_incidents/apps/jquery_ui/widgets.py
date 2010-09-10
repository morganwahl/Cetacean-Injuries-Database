from django import forms
from django.forms import widgets
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode

class Datepicker(widgets.DateInput):
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
        return render_to_string('datepicker.html', {
            'input_id': final_attrs['id'],
            'final_attrs': forms.util.flatatt(final_attrs),
        })
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE,)}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE)

class Autocomplete(widgets.Input):
    
    input_type = 'text'
    
    def __init__(self, attrs=None, source=None, options={}):
        super(Autocomplete, self).__init__(attrs)
        # TODO source is required
        self.source = source
        self.options = options
    
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        input_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            input_attrs['value'] = force_unicode(value)
        
        return render_to_string('autocomplete.html', {
            'input_attrs': input_attrs,
            'flat_input_attrs': forms.util.flatatt(input_attrs),
            'source': self.source,
            'options': self.options,
        })
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE,)}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE)

class ModelAutocomplete(Autocomplete):

    @property
    def model(self):
        raise NotImplementedError("ModelAutocomplete must have a model class")
    
    def id_to_display(self, id):
        return self.model.objects.get(id=id).__unicode__()
    
    def render(self, name, value, attrs=None, custom_html= None, extra_js= None):
        attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        
        # split the attributes into ones for the visible autocomplete-field
        # and ones for the hidden value-field
        value_attrs = {'type': 'hidden'}
        value_attrs['id'] = attrs.pop('id')
        value_attrs['name'] = attrs.pop('name')

        autocomplete_attrs = attrs
        autocomplete_attrs['id'] = value_attrs['id'] + '-display_name'

        # treat non-integers as no value
        try:
            value = int(value)
            autocomplete_attrs['value'] = self.id_to_display(value)
            value_attrs['value'] = force_unicode(value)
        except ValueError:
            pass

        options = self.options.copy()

        # javascript doesn't like hyphenminuses
        import re
        func_prefix = re.sub('-', '_', name)
        
        # we provide overrideable defaults for some of the function options
        func_options = {}

        for funcname in ('focus', 'select'):
            c = 'custom_' + funcname
            n = funcname + '_name'
            func_options[c] = True
            if not funcname in options:
                func_options[c] = False
                func_options[n] = func_prefix + '_' + funcname
                options[funcname] = func_options[n]

        return render_to_string('model_autocomplete.html', {
            'autocomplete_attrs': autocomplete_attrs,
            'flat_autocomplete_attrs': forms.util.flatatt(autocomplete_attrs),
            'value_attrs': value_attrs,
            'flat_value_attrs': forms.util.flatatt(value_attrs),
            'source': self.source,
            'options': options,
            'func_options': func_options,
            'custom_html': custom_html,
            'extra_js': extra_js,
        })
    
