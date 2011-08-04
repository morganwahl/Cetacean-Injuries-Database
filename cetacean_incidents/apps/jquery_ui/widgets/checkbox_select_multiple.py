from django.conf import settings

from django.forms.widgets import CheckboxSelectMultiple as DjangoCheckboxSelectMultiple

class CheckboxSelectMultiple(DjangoCheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        result = super(CheckboxSelectMultiple, self).render(name, value, attrs, choices)
        from pprint import pprint
        pprint((name, value, attrs, choices))
        script = u"""
            <a href="" id="%(name)s-all">check all</a>
            <a href="" id="%(name)s-none">uncheck all</a>
            <script type="text/javascript">
                $().ready(function(){
                    var all_boxes = $('input[name="%(name)s"]');
                    $('#%(name)s-all').click(function(){
                        all_boxes.attr('checked', 'checked');
                        return false;
                    });
                    $('#%(name)s-none').click(function(){
                        all_boxes.removeAttr('checked');
                        return false;
                    });
                });
            </script>
        """ % {
            'name': name,
        }
        return result + script

    class Media:
        js = (settings.JQUERY_FILE,)
