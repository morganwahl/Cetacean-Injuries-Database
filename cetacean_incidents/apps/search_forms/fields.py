from django import forms
from django.db import models
from django.db.models import Q

from widgets import (
    MatchWidget,
    HiddenMatchWidget,
)

class MatchField(forms.MultiValueField):
    '''\
    A form field class with multiple subfields. One field is the match type and
    each type has another field to supply arguments. Values are 2-tuples of the
    lookup choice and the arg for that choice.
    '''
    
    widget = MatchWidget
    hidden_widget = HiddenMatchWidget
    
    def __init__(self, lookup_choices, value_fields, *args, **kwargs):
        '''\
        Lookup_choices is Django choice tuple whose values are lookup types.
        value_fields is a dictionary of fields keyed to lookup types. The query
        value will be the value field that corresponds to the chosen lookup
        type.
        '''
        #from pprint import pprint
        pprint(('MatchField.__init__', lookup_choices, value_fields, args, kwargs))

        #defaults = {
        #    'required': True,
        #    'widget': None,
        #    'label': None,
        #    'initial': None,
        #    'help_text': None,
        #    'error_messages': None,
        #    'show_hidden_initial': False,
        #    'validators': [],
        #    'localize': False,
        #}
        args_dict = dict(zip((
            'required',
            'widget',
            'label',
            'initial',
            'help_text',
            'error_messages',
            'show_hidden_initial',
            'validators',
            'localize',
        ), args))
        given = {}
        #given.update(defaults)
        given.update(args_dict)
        given.update(kwargs)
        
        passed = dict(given)
        
        lookup_field = forms.ChoiceField(choices=lookup_choices)

        # TODO seperate out the args and kwargs, and pass some to value_fields,
        # some to super
        
        fields = [
            lookup_field,
        ] + [value_fields[choice[0]] for choice in lookup_choices]
        if not 'widget' in given:
            lookup_widget = lookup_field.widget
            arg_widgets = dict(
                [(lookup, field.widget) for lookup, field in value_fields.items()]
            )
            passed['widget'] = self.widget(lookup_widget, arg_widgets)
        
        pprint(('MultiValueField.__init__', fields, passed))
        super(MatchField, self).__init__(fields, **passed)
    
    @property
    def lookup_field(self):
        return self.fields[0]
    
    def clean(self, value):
        # set all the value fields that don't correspond to lookup type to None
        # This ensures their validation always succeeds, since QueryFields are
        # never required.
        
        # note that value could be just about anything, and value[0] may not
        # be a string, much less a lookup type.
        try:
            lookup = value[0]
        except TypeError: # value isn't subscriptable
            lookup = None
        except IndexError: # there is no value[0]
            lookup = None
        
        # note that this may set all the other values to None if value[0] wasn't
        # one of the lookup_choices. that's OK, since value[0] will then fail
        # to validate.
        if not lookup is None:
            lookup_choices = self.lookup_field.choices
            for i, choice in enumerate(lookup_choices, start=1):
                if choice[0] != lookup:
                    value[i] = None
        
        return super(QueryField, self).clean(value)
    
    def compress(self, data_list):
        from pprint import pprint
        pprint(('compress', data_list))
        
        if data_list == []:
            return None
        
        if data_list[0] == '':
            return None
        
        lookup = data_list[0]
        lookup_choices = self.lookup_field.choices
        for i, choice in enumerate(lookup_choices, start=1):
            if choice[0] == lookup:
                return (lookup, data_list[i])
        
        raise NotImplementedError

class QueryField(MatchField):
    '''\
    A form field class based on a model field class whose values are Q-objects
    that filter on the model field class.
    '''
    
    def __init__(self, lookup_choices, value_fields, *args, **kwargs):
        '''\
        Lookup_choices is Django choice tuple whose values are lookup types.
        value_fields is a dictionary of fields keyed to lookup types. The query
        value will be the value field that corresponds to the chosen lookup
        type.
        '''
        from pprint import pprint
        pprint(('QueryField.__init__', lookup_choices, value_fields, args, kwargs))
        
        super(QueryField, self).__init__(lookup_choices, value_fields, *args, **kwargs)
    
    def query(self, fieldname, value):
        if value is None:
            return Q()
        lookup_type, lookup_value = value
        q = Q(**{fieldname + '__' + lookup_type: lookup_value})
        from pprint import pprint
        pprint(('QueryField.query', unicode(q)))
        return q
