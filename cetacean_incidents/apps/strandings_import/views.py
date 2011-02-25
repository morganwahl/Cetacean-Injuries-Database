from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from reversion import revision

from cetacean_incidents.decorators import permission_required

from forms import ImportCSVForm
from csv_import import parse_csv, process_results
    
# TODO perms
@login_required
@transaction.commit_on_success
@revision.create_on_success
def import_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            
            results = parse_csv(form.cleaned_data['csv_file'])
    
            if not form.cleaned_data['test_run']:
                process_results(results, form.cleaned_data['csv_file'].name, request.user)
                return redirect('home')
            
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
    
