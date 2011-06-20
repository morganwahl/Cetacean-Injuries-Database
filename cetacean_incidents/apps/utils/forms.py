from django.forms.widgets import (
    RadioFieldRenderer,
)
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

class InlineRadioFieldRenderer(RadioFieldRenderer):
    def render(self):
        """Outputs a <span> for this set of radio fields."""
        return mark_safe(
            u'<span>\n%s\n</span>' % u'\n'.join(
                [u'<span>%s</span>' % force_unicode(w) for w in self]
            )
        )

