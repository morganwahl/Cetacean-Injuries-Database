from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from cetacean_incidents.decorators import permission_required

from forms import ImportCSVForm
from csv_import import parse_csv

# TODO perms
@login_required
def import_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            results = parse_csv(form.cleaned_data['csv_file'])
    else:
        form = ImportCSVForm()

    return render_to_response(
        'strandings_import/import.html',
        {
            'form': form,
            'media': form.media,
            'results': results,
        },
        context_instance= RequestContext(request),
    )
    
