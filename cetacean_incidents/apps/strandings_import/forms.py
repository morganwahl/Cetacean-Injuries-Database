from django import forms

class ImportCSVForm(forms.Form):
    
    csv_file = forms.FileField(
        required= True,
        label= "CSV file",
    )
    
