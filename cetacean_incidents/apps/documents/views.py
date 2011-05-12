import os
from os import path

from django.conf import settings
from django.core.files import File
from django.forms import Media
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

from forms import (
    DocumentForm,
    NewDocumentForm,
    NewUploadedFileForm,
    RepositoryFileForm,
    UploadedFileForm,
)

from models import (
    Document,
    Documentable,
    RepositoryFile,
    UploadedFile,
)

@login_required
def view_document(request, d):
    if not isinstance(d, Document):
        d = Document.objects.get(id=d)
    d = d.specific_instance()
    
    if not d.can_be_seen_by(request.user):
        return redirect(settings.BAD_PERMISSION_URL)
    
    if isinstance(d, UploadedFile):
        return redirect(view_uploadedfile, d.id, permanent=True)
    if isinstance(d, RepositoryFile):
        return redirect(view_repositoryfile, d.id, permanent=True)
    
    return render_to_response(
        'documents/view_document.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_uploadedfile(request, d):
    if not isinstance(d, UploadedFile):
        d = UploadedFile.objects.get(id=d)
    
    if not d.can_be_seen_by(request.user):
        return redirect(settings.BAD_PERMISSION_URL)
    
    return render_to_response(
        'documents/view_uploadedfile.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
def view_repositoryfile(request, d):
    if not isinstance(d, RepositoryFile):
        d = RepositoryFile.objects.get(id=d)
    
    if not d.can_be_seen_by(request.user):
        return redirect(settings.BAD_PERMISSION_URL)
    
    return render_to_response(
        'documents/view_repositoryfile.html',
        {
            'd': d,
            'media': Media(js=(settings.JQUERY_FILE,)),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('documents.add_document')
def add_document(request, documentable_id):
    
    obj = Documentable.objects.get(id=documentable_id).specific_instance()
    
    # even though only one subclass of Document is listed here, this view is
    # written with adding new ones in mind
    form_classes = {
        'document': NewDocumentForm,
        'uploaded_file': NewUploadedFileForm,
    }

    form_kwargs = {}
    for name in form_classes.keys():
        form_kwargs[name] = {
            'prefix': name,
        }
    
    forms = {}
    
    if request.method == 'POST':
        # we have to instantiate the 'document' form in order to know which other
        # forms to bind
        form_kwargs['document']['data'] = request.POST
        forms['document'] = form_classes['document'](**form_kwargs['document'])
        # we only want to bind the forms the user acutally filled in
        if forms['document'].is_valid():
            is_upload = forms['document'].cleaned_data['is_uploadedfile']
            if is_upload:
                form_kwargs['uploaded_file']['data'] = request.POST
                form_kwargs['uploaded_file']['files'] = request.FILES
        
        
        # now instantiate the forms besides the 'document' form
        for name in filter(lambda fn: fn != 'document', form_classes.keys()):
            forms[name] = form_classes[name](**form_kwargs[name])
        
        if forms['document'].is_valid() and (not is_upload or (is_upload and forms['uploaded_file'].is_valid())):

            document = forms['document'].save(commit=False)
            document.attached_to = obj
            document.save()
            forms['document'].save_m2m()

            if is_upload:
                uploaded_file = UploadedFile.transmute_document(document, **forms['uploaded_file'].cleaned_data)
                uploaded_file.uploader = request.user
                uploaded_file.clean()
                uploaded_file.save()
                
            return redirect(obj)
    else: # request.method != 'POST'
        for name in form_classes.keys():
            forms[name] = form_classes[name](**form_kwargs[name])
    
    # the default template uses the radiohider script with forms['models']
    # select widget. TODO currently no way to pass in a custom Media to go with 
    # a custom template.
    template_media = Media(
        js= (settings.JQUERY_FILE, 'checkboxhider.js'),
    )
    media = reduce( lambda m, f: m + f.media, forms.values(), template_media)

    return render_to_response(
        'documents/add_attachment.html',
        {
            'object': obj,
            'forms': forms,
            'media': media,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('documents.change_document')
def edit_document(request, document_id):
    
    d = Document.objects.get(id=document_id).specific_instance()
    
    if not d.can_be_seen_by(request.user):
        return redirect(settings.BAD_PERMISSION_URL)
    
    form_class = {
        Document: DocumentForm,
        UploadedFile: UploadedFileForm,
        RepositoryFile: RepositoryFileForm,
    }[d.__class__]
    
    if request.method == 'POST':
        form = form_class(data=request.POST, instance=d)
        if form.is_valid():
            return redirect(form.save())
    else:
        form = form_class(instance=d)
    
    return render_to_response(
        'documents/edit_document.html',
        {
            'd': d,
            'form': form,
            'media': form.media,
        },
        context_instance = RequestContext(request),
    )
    
@login_required
@permission_required('documents.delete_document')
def delete_document(request, document_id):
    
    d = Document.objects.get(id=document_id)
    
    if not d.can_be_seen_by(request.user):
        return redirect(settings.BAD_PERMISSION_URL)
    
    # requests that alter data must be posts
    if request.method == 'POST':
        # for now, don't delete the uploaded file
        d.delete()
        
        return render_to_response(
            'documents/document_deleted.html',
            {'d': d},
            context_instance= RequestContext(request),
        )

    return redirect(d)

