from django.conf import settings
from django.forms import Media
from django.shortcuts import (
    redirect,
    render_to_response,
)
from django.template import RequestContext

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import permission_required
from cetacean_incidents.forms import merge_source_form_factory

from forms import (
    ContactForm,
    ContactMergeForm,
    ContactSearchForm,
)
from models import Contact

@login_required
def contact_detail(request, contact_id):
    
    contact = Contact.objects.get(pk=contact_id)
    
    template_media = Media(js=(settings.JQUERY_FILE,))
    
    context = {
        'contact': contact,
        'media': template_media,
    }

    if request.user.has_perms((
        'contacts.change_contact',
        'contacts.delete_contact',
    )):
        merge_form = merge_source_form_factory(Contact, contact)()
        context['media'] += merge_form.media
        context['merge_form'] = merge_form
    
    return render_to_response(
        'contacts/contact_detail.html',
        context,
        context_instance= RequestContext(request),
    )

@login_required
def _create_or_edit_contact(request, contact_id=None):
    # assme user has contacts.add_contact and contacts.change_contact
    if not contact_id is None:
        # we're editing an existing contact
        contact = Contact.objects.get(pk=contact_id)
        template = 'contacts/edit_contact.html'
    else:
        # we're creating a new contact
        contact = None # the default for ContactForm(instance=)
        template = 'contacts/create_contact.html'
    
        
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            return redirect('contact_detail', contact.pk)
    else:
        form = ContactForm(instance=contact)
    
    media = form.media
    
    context = {
        'contact': contact,
        'form': form,
        'media': media,
    }
    
    return render_to_response(
        template,
        context,
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('contacts.add_contact')
def create_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)

@login_required
@permission_required('contacts.change_contact')
def edit_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)

@login_required
@permission_required('contacts.change_contact')
@permission_required('contacts.delete_contact')
def merge_contact(request, destination_id, source_id=None):
    # the "source" contact will be deleted and references to it will be changed
    # to the "destination" contact
    
    destination = Contact.objects.get(pk=destination_id)

    if source_id is None:
        merge_form = merge_source_form_factory(Contact, destination)(request.GET)

        if not merge_form.is_valid():
            return redirect('contact_detail', destination.pk)
        source = merge_form.cleaned_data['source']
    else:
        source = Contact.objects.get(pk=source_id)
    
    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = ContactMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('contact_detail', destination.pk)
    else:
        form = ContactMergeForm(**form_kwargs)
    
    return render_to_response(
        'contacts/merge_contact.html',
        {
            'object_name': 'contact',
            'object_name_plural': 'contacts',
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

@login_required
def contact_search(request):
    # prefix should be the same as the on used on the homepage
    prefix = 'contact_search'
    form_kwargs = {
        'prefix': 'contact_search',
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    form = ContactSearchForm(**form_kwargs)
    
    contact_list = tuple()
    
    if form.is_valid():
        # FIXME do the actual filtering
        contact_list = form.results()
        
        #contact_order_args = ('id',)
        #contacts = Contact.objects.all().distinct().order_by(*contact_order_args)
        # TODO Oracle doesn't support distinct() on models with TextFields
        #contacts = Contact.objects.all().order_by(*contact_order_args)
        
        #if form.cleaned_data['taxon']:
        #    t = form.cleaned_data['taxon']
        #    descendants = Taxon.objects.with_descendants(t)
        #    contacts = contacts.filter(Q(determined_taxon__in=descendants) | Q(case__observation__taxon__in=descendants))
        
        # empty string for name is same as None
        #if form.cleaned_data['name']:
        #    name = form.cleaned_data['name']
        #    name_q = Q(name__icontains=name)
        #    field_number_q = Q(field_number__icontains=name)
        #    contacts = contacts.filter(name_q | field_number_q)

        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        #seen = set()
        #contact_list = list()
        #for c in contacts:
        #    if not c in seen:
        #        seen.add(c)
        #        contact_list.append(c)

    return render_to_response(
        "contacts/contact_search.html",
        {
            'form': form,
            'media': form.media,
            'contact_list': contact_list,
            'contact_count': len(contact_list),
        },
        context_instance= RequestContext(request),
    )

