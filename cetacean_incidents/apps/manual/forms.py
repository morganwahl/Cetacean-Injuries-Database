from django import forms

from models import Manual

class ManualForm(forms.ModelForm):
    class Meta:
        model = Manual

