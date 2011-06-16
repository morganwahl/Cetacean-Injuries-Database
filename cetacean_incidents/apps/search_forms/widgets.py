from collections import Sequence

from django.conf import settings
from django.forms.widgets import MultiWidget

class MatchWidget(MultiWidget):
    '''\
    A multiwidget that has a select widget for picking a match type, and a set
    of other widgets that each correspond to a type, which are only display when
    that type is selected.
    '''
    
    def __init__(self, lookup_widget, value_widgets, attrs=None):
        #from pprint import pprint
        #pprint(('MatchField.__init__', lookup_widget, value_widgets, attrs))
        widgets = [
            lookup_widget,
        ] + [value_widgets[choice[0]] for choice in lookup_widget.choices]
        #pprint(('MatchWidget.__init__', widgets, attrs))
        super(MatchWidget, self).__init__(widgets, attrs)
    
    @property
    def lookup_to_value_map(self):
        lookup_widget = self.widgets[0]
        value_widgets = self.widgets[1:]
        result = {}
        for i, choice in enumerate(lookup_widget.choices):
            lookup = choice[0]
            result[lookup] = value_widgets[i]
        return result
    
    def decompress(self, value):
        if value is None:
            return []
        
        if isinstance(value, Sequence):
            if len(value) != 2:
                raise ValueError("can't decompress a sequence with %d items" % len(value))
            lookup = value[0]
            lookup_choices = self.widgets[0].choices
            out = [lookup]
            for choice in lookup_choices:
                if choice[0] == lookup:
                    out.append(value[1])
                else:
                    out.append(None)
            
            return out
        
        from pprint import pprint
        pprint(('decompress', value))
        
        raise NotImplementedError
    
    def format_output(self, rendered_widgets):
        #from pprint import pprint
        #pprint(('format_output', rendered_widgets))
        
        # enclose each widget in a span so we can select them in JS
        lookup_widget = u'<span class="lookup">%s</span>' % rendered_widgets[0]
        value_widgets = []
        for i, w in enumerate(rendered_widgets[1:]):
            lookup_choice = self.widgets[0].choices[i][0]
            html_classes = 'value', lookup_choice + '_value'
            value_widget = u'<span class="%s">%s</span>' % (
                ' '.join(html_classes),
                w,
            )
            value_widgets.append(value_widget)
        
        # enclose the whole thing in a span to facilitate selection in JS        
        return u'<span class="match_widget">\n\t%s\n</span>' % u'\n\t'.join([lookup_widget] + value_widgets)
    
    class Media:
        js = (settings.JQUERY_FILE, 'match_widget.js')

class HiddenMatchWidget(MatchWidget):
    is_hidden = True

