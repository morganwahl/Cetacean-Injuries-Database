"""
Has the 'pretty' tag which removes all newlines followed by optional whitespace
from its contents.
"""

from django import template

register = template.Library()


class PrettyNode(template.Node):
    """Implements the actions of the pretty tag."""
    
    def __init__(self, nodelist):
        self.nodelist = nodelist
    
    def render(self, context):
        output = self.nodelist.render(context)
        return output.replace('\n', '')

@register.tag
def pretty(parser, token):
    """
    Removes newlines from contents. Useful for formatting templates without a
    bunch of newlines ending up in their output.
    """
    
    nodelist = parser.parse(('endpretty',))
    parser.delete_first_token()
    return PrettyNode(nodelist)

