from django import forms
from models import DateTime

class DateTimeForm(forms.ModelForm):
    
    class Meta:
        model = DateTime

