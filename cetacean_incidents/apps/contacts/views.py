from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.forms.formsets import formset_factory

from models import Contact
from forms import ContactForm, OrganizationForm

@login_required
def _create_or_edit_contact(request, contact_id=None):
    if not contact_id is None:
        # we're editing an existing contact
        contact = Contact.objects.get(id=contact_id)
        template = 'contacts/edit_contact.html'
    else:
        # we're creating a new contact
        contact = None # the default for ContactForm(instance=)
        template = 'contacts/create_contact.html'
    # the exisintg affiliations will be in the widget in ContactForm. This is
    # only for adding new Organizations from within the same page
    AffiliationsFormset = formset_factory(OrganizationForm, extra=2)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        new_affiliations_formset = AffiliationsFormset(request.POST)
        if form.is_valid() and new_affiliations_formset.is_valid():
            contact = form.save()
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
        new_affiliations_formset = AffiliationsFormset()
    return render_to_response(
        template,
        {
            'contact': contact,
            'form': form,
            'new_affiliations': new_affiliations_formset,
        },
        context_instance= RequestContext(request),
    )

@login_required
def create_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)

@login_required
def edit_contact(*args, **kwargs):
    return _create_or_edit_contact(*args, **kwargs)

