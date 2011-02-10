from django.forms.widgets import MediaDefiningClass
from django.conf import settings
from django.template import Context
from django.template.loader import render_to_string
from django.template.loader import get_template

class Tab(object):
    '''\
    A Tab has a html_name, a display name, a template and a context.
    '''
    
    default_html_display = None

    @property
    def default_template(self):
        raise NotImplementedError

    required_context_keys = tuple()
    
    def __init__(self, context={}, html_id=None, html_display=None, template=None):
        '''\
        If context isn't given, it must be set before any render functions are
        called.
        
        If html_id is None it defaults to the name of the class with 'Tab'
        removed from the end, lowercased.
        
        If html_display is None it defaults to the html_id with '_'s replaced
        by spaces and titlecased.
        
        template can be passed to override the default template.
        '''
        
        if html_id is None:
            # TODO are there things in Python identifiers that can't be in
            # HTML ids?
            html_id = self.__class__.__name__
            if html_id.endswith('Tab'):
                html_id = html_id[:-len('Tab')]
            html_id = html_id.lower()
        self.html_id = html_id

        if html_display is None:
            html_display = self.default_html_display
        if html_display is None:
            html_display = html_id
            html_display = html_display.replace('_', ' ')
            html_display = html_display.title()
        self.html_display = html_display
        
        if template is None:
            template = self.default_template
        self.template = template
        
        self.context = context
    
    def check_context(self):
        # check that all the required keys are there
        for k in self.required_context_keys:
            if not k in self.context:
                raise ValueError("%s was initiated with a context without a required key: %s" % (self.__class__.__name__, k))
    
    def render_js(self):
        self.check_context()
        return render_to_string("tab_js.js", {'tab': self})

    def li_error(self):
        return False    
    
    def render_li(self):
        self.check_context()
        return render_to_string("tab_li.html", {'tab': self, 'error': self.li_error()})

    def render_body(self):
        self.check_context()
        return get_template(self.template).render(self.context)

class Tabs(object):
    '''\
    A class that organizes rendering using jQuery UI. It takes an iterable of
    Tab instances, and has a render() function that returns HTML.
    '''
    
    __metaclass__ = MediaDefiningClass
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE,)}
        js = (settings.JQUERY_FILE, settings.JQUERY_PLUGIN_COOKIE, settings.JQUERYUI_JS_FILE)
    
    def __init__(self, tabs, html_id='tabs'):
        # TODO check that tabs is an iterable of Tab instances
        # TODO check that all the html_names differ
        
        self.html_id = html_id

        self.tab_data = []
        # add the prev and next IDs
        prev = None
        for i in range(len(tabs)):
            data = {
                'tab': tabs[i],
            }
            
            if prev:
                prev['next_id'] = data['tab'].html_id
                data['prev_id'] = prev['tab'].html_id

            prev = data
            self.tab_data.append(data)
    
    def render(self):
        '''\
        Returns the HTML for the tabs.
        '''
        
        for data in self.tab_data:
            data['li'] = data['tab'].render_li()
            data['body'] = data['tab'].render_body()
        
        return render_to_string("tabs.html", {'tabs': self})

