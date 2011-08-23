from django import forms

from tinymce.widgets import TinyMCE

from models import (
    FileReport,
    StringReport,
)

class NewReportForm(forms.Form):
    
    report_type = forms.ChoiceField(
        widget= forms.RadioSelect,
        choices= (
            ('file', 'upload a file'),
            ('text', 'write in text'),
        ),
        initial= 'file',
        label= 'template type',
    )

class FileReportForm(forms.ModelForm):
    
    class Meta:
        model = FileReport

class StringReportForm(forms.ModelForm):

    class Meta:
        model = StringReport
        widgets = {
            'template_text': TinyMCE(attrs={'cols': 80, 'rows': 40}),
        }

