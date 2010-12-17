from django.core.files import File
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms import Media
from django.conf import settings

import os
from os import path

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required

from forms import DocumentModelForm, DocumentForm, UploadedFileForm, RepositoryFileForm

from models import Documentable, Document, UploadedFile, RepositoryFile

@login_required
def view_document(request, d):
    if not isinstance(d, Document):
        d = Document.objects.get(id=d)
    d = d.specific_instance()
    
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
                document.attached_to = obj
                if submitted_name == 'uploaded_file':
                    document.uploader = request.user
                document.save()
                forms[submitted_name].save_m2m()
                
                return redirect(obj)
                
    else: # request.method != 'POST'
        for name in form_classes.keys():
            forms[name] = form_classes[name](**form_kwargs[name])
    
    # the default template uses the radiohider script with forms['models']
    # select widget. TODO currently no way to pass in a custom Media to go with 
    # a custom template.
    template_media = Media(
        js= (settings.JQUERY_FILE, 'radiohider.js'),
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

