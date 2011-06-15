from django import forms
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

class InlineRadioFieldRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(
            u'<span>\n%s\n</span>' % u'\n'.join(
                [u'<span>%s</span>' % force_unicode(w) for w in self]
            )
        )

