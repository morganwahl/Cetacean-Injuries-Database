from copy import copy

from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext

from models import (
    Manual,
    manual_storage,
)

from forms import ManualForm

def view_manuals(request):
    '''\
    Returns a page show a list of all manuals. Has a form to upload a new copy
    of the manual. Accepts POST requests from that form.
    '''
    
    if request.method == 'POST':
        new_manual_form = ManualForm(data=request.POST, files=request.FILES)
        if new_manual_form.is_valid():
            manual = new_manual_form.save(commit=False)
            manual.uploader = request.user
            manual.save()
            new_manual_form.save_m2m()
            return redirect('view_manuals')
    else:
        new_manual_form = ManualForm()
    
    manuals = Manual.objects.all()
    
    return render_to_response(
        'manual/view_manuals.html',
        {
            'manuals': manuals,
            'new_manual_form': new_manual_form,
            'media': new_manual_form.media,
        },
        context_instance= RequestContext(request),
    )

def download_manual(request, manual_id=None):
    '''\
    Returns a manual. If an ID is given, that's the one returned. Otherwise,
    the most recent one is.
    '''
    
    if manual_id is None:
        manual = Manual.objects.all().order_by('-date_uploaded')[0]
    else:
        manual = Manual.objects.get(pk=manual_id)
    
    return redirect(manual_storage.url(manual.manual_file.name))

