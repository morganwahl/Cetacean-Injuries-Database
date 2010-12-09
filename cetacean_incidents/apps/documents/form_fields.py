import os
import re

from django.forms.fields import ChoiceField

# based on Django's FilePathField
class DirectoryPathField(ChoiceField):
    def __init__(self, path, match=None, recursive=False, required=True,
                 widget=None, label=None, initial=None, help_text=None,
                 *args, **kwargs):
        self.path, self.match, self.recursive = path, match, recursive
        super(DirectoryPathField, self).__init__(choices=(), required=required,
            widget=widget, label=label, initial=initial, help_text=help_text,
            *args, **kwargs)

        if self.required:
            self.choices = []
        else:
            self.choices = [("", "---------")]

        if self.match is not None:
            self.match_re = re.compile(self.match)

        if recursive:
            for root, dirs, files in os.walk(self.path):
                for d in dirs:
                    if self.match is None or self.match_re.search(d):
                        d = os.path.join(root, d)
                        self.choices.append((d, d.replace(path, "", 1)))
        else:
            try:
                for d in os.listdir(self.path):
                    full_path = os.path.join(self.path, d)
                    if os.path.isdir(full_path) and (self.match is None or self.match_re.search(d)):
                        self.choices.append((full_path, d))
            except OSError:
                pass

        self.widget.choices = self.choices

