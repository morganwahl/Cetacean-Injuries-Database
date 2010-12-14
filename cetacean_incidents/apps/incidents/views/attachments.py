from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.forms import Media
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.documents.views import _get_documentforms, _save_documentforms

from ..models import Case, CaseDocument, Observation, ObservationDocument

@login_required
@permission_required('documents.add_document')
def add_casedocument(request, case_id):
    
    c = Case.objects.get(id=case_id)
    
    forms = _get_documentforms(request)
    
    if request.method == 'POST':
        doc = _save_documentforms(request, forms)
        if doc:
            case_doc = CaseDocument.objects.create(
                document= doc,
                attached_to= c,
            )
            return redirect(c)
    
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )
    media = reduce( lambda m, f: m + f.media, forms.values(), template_media)
    
    return render_to_response(
        'incidents/add_casedocument.html',
        {
            'case': c,
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('documents.add_document')
def add_observationdocument(request, observation_id):
    
    o = Observation.objects.get(id=observation_id)
    
    forms = _get_documentforms(request)
    
    if request.method == 'POST':
        doc = _save_documentforms(request, forms)
        if doc:
            obs_doc = ObservationDocument.objects.create(
                document= doc,
                attached_to= o,
            )
            return redirect(o)
    
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )
    media = reduce( lambda m, f: m + f.media, forms.values(), template_media)
    
    return render_to_response(
        'incidents/add_observationdocument.html',
        {
            'observation': o,
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

