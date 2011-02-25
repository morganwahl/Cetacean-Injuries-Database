from django import forms

class ImportCSVForm(forms.Form):
    
    csv_file = forms.FileField(
        required= True,
        label= "CSV file",
    )
    
    test_run = forms.BooleanField(
        initial= True,
        required= False,
    )
    
