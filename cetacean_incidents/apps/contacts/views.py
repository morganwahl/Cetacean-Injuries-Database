from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms.formsets import formset_factory
from django.forms import Media

from cetacean_incidents.forms import merge_source_form_factory
from cetacean_incidents.decorators import permission_required

from models import Contact
from forms import ContactForm, OrganizationForm, ContactMergeForm

@login_required
def contact_detail(request, contact_id):
    
    contact = Contact.objects.get(id=contact_id)
    
    template_media = Media(
        js= (settings.JQUERY_FILE,),
    )
    
    context = {
        'contact': contact,
        'media': template_media,
    }

    if request.user.has_perms(('contacts.change_contact', 'contacts.delete_contact')):
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
        contact = Contact.objects.get(id=contact_id)
        template = 'contacts/edit_contact.html'
    else:
        # we're creating a new contact
        contact = None # the default for ContactForm(instance=)
        template = 'contacts/create_contact.html'
    
    add_org = request.user.has_perm('contacts.add_organization')
        
    # the exisintg affiliations will be in the widget in ContactForm. This is
    # only for adding new Organizations from within the same page
    if add_org:
        AffiliationsFormset = formset_factory(OrganizationForm, extra=2)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if add_org:
            new_affiliations_formset = AffiliationsFormset(request.POST)
        if form.is_valid() and (not add_org or new_affiliations_formset.is_valid()):
            contact = form.save()
            if add_org:
                # add the affiliations from the new_affs_formset
                for org_form in new_affiliations_formset.forms:
                    # don't save orgs with blank names.
                    if not 'name' in org_form.cleaned_data:
                        continue
                    org = org_form.save()
                    contact.affiliations.add(org)
            return redirect('contact_detail', contact.id)
    else:
        form = ContactForm(instance=contact)
        if add_org:
            new_affiliations_formset = AffiliationsFormset()
    
    media = form.media
    if add_org:
        media += new_affiliations_formset.media
    
    context = {
        'contact': contact,
        'form': form,
        'media': media,
    }
    if add_org:
        context['new_affiliations'] = new_affiliations_formset
    
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
    
    destination = Contact.objects.get(id=destination_id)

    if source_id is None:
        merge_form = merge_source_form_factory(Contact, destination)(request.GET)

        if not merge_form.is_valid():
            return redirect('contact_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Contact.objects.get(id=source_id)
    
    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = ContactMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect('contact_detail', destination.id)
    else:
        form = ContactMergeForm(**form_kwargs)
    
    return render_to_response(
        'contacts/merge_contact.html',
        {
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
            'destination_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_fk_refs
            ),
            'source_fk_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_fk_refs
            ),
            'destination_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.destination_m2m_refs
            ),
            'source_m2m_refs': map(
                lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[2]),
                form.source_m2m_refs
            ),
        },
        context_instance= RequestContext(request),
    )

