from django import forms

from models import Report

class ReportForm(forms.ModelForm):
    
    # name isn't required since if it's left blank, that just implies
    # save(commit=True) won't work, which is fine if we don't want to save the
    # new report
    _f = Report._meta.get_field_by_name('name')[0]
    name = forms.CharField(
        max_length= _f.max_length,
        required= False,
    )
    
    class Meta:
        model = Report
