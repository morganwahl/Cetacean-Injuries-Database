from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.forms import Media
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.documents.forms import (
    DocumentModelForm,
    DocumentForm,
    UploadedFileForm,
    RepositoryFileForm,
)

from ..models import Case, CaseDocument, Observation, ObservationDocument

def _add_attachment(attachment_class, obj, template='incidents/add_attachment.html', obj_name = 'object'):
    
    form_classes = {
        'model': DocumentModelForm,
        'document': DocumentForm,
        'uploaded_file': UploadedFileForm,
        'repository_file': RepositoryFileForm,
    }

    form_kwargs = {}
    for name in form_classes.keys():
        form_kwargs[name] = {
            'prefix': name,
        }
    
    forms = {}
    
    if request.method == 'POST':
        # we have to instantiate the 'model' form in order to know which other
        # forms to bind
        form_kwargs['model']['data'] = request.POST
        forms['model'] = form_classes['model'](**form_kwargs['model'])
        # we only want to bind the forms the user acutally filled in
        if forms['model'].is_valid():
            st = forms['model'].cleaned_data['storage_type']
            if st == 'Document':
                submitted_name = 'document'
            if st == 'UploadedFile':
                submitted_name = 'uploaded_file'
                form_kwargs['uploaded_file']['files'] = request.FILES
            if st == 'RepositoryFile':
                submitted_name = 'repository_file'
            form_kwargs[submitted_name]['data'] = request.POST
            
            # instantiate all the forms in case there's an error in the one that
            # was submitted
            for name in ('document', 'uploaded_file', 'repository_file'):
                forms[name] = form_classes[name](**form_kwargs[name])
                
            # now check the submitted one 
            if forms[submitted_name].is_valid():
                document = forms[submitted_name].save(commit=False)
                if submitted_name == 'uploaded_file':
                    document.uploader = request.user
                document.save()
                forms[submitted_name].save_m2m()
                
                attachment = attachment_class.objects.create(
                    document= document,
                    attached_to= obj,
                )
                return redirect(obj)
                
    else: # request.method != 'POST'
        for name in forms_classes.keys():
            forms[name] = form_classes[name](**form_kwargs[name])
    
    # the default template uses the radiohider script with forms['models']
    # select widget. TODO currently no way to pass in a custom Media to go with 
    # a custom template.
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
    )
    media = reduce( lambda m, f: m + f.media, forms.values(), template_media)

    return render_to_response(
        template,
        {
            obj_name: obj,
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('documents.add_document')
def add_casedocument(request, case_id):
    
    c = Case.objects.get(id=case_id)
    
    return _add_attachment(CaseDocument, c)
    
@login_required
@permission_required('documents.add_document')
def add_observationdocument(request, observation_id):
    
    o = Observation.objects.get(id=observation_id)
    
    return _add_attachment(ObservationDocument, o)

