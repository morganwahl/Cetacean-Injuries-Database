from django.forms.widgets import MediaDefiningClass
from django.conf import settings
from django.template import Context
from django.template.loader import render_to_string

class Tab(object):
    '''\
    A Tab has a html_name, a display name, a template and a context.
    '''
    
    def __init__(self, html_id, template, context=Context(), html_display=None, error_func=None):
        '''\
        If display_name is none is defaults to the html_name with '_'s replaced
        by spaces and titlecased.
        '''

        self.html_id = html_id
        if html_display is None:
            html_display = html_id
            html_display = html_display.replace('_', ' ')
            html_display = html_display.title()
        self.html_display = html_display

        self.template = template
        self.context = context
        self.errors = property(error_func)
        
    def render_js(self):
        return render_to_string("tab_js.js", {'tab': self})

    def render_tab(self):
        return render_to_string("tab_li.html", {'tab': self})

    def render_body(self):
        return self.template.render(self.context)

class Tabs(object):
    '''\
    A class that organizes rendering using jQuery UI. It takes an iterable of
    Tab instances, and has a render() function that returns HTML.
    '''
    
    __metaclass__ = MediaDefiningClass
    
    class Media:
        css = {'all': (settings.JQUERYUI_CSS_FILE,)}
        js = (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE)
    
    def __init__(self, tabs=tuple()):
        # TODO check that tabs is an iterable of Tab instances
        # TODO check that all the html_names differ
        self.tabs = tabs
    
    def render(self):
        '''\
        Returns the HTML for the tabs.
        '''
        return render_to_string("tabs.html", {'tabs': self.tabs})

