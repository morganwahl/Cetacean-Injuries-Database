import os
from datetime import datetime
import pytz
from copy import copy

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Q
from django.utils.html import conditional_escape as esc
from django.db import transaction

from reversion import revision

from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.documents.models import Document
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.incidents.models import Animal
from cetacean_incidents.apps.incidents.models import Case
from cetacean_incidents.apps.incidents.models import Observation
from cetacean_incidents.apps.shipstrikes.models import Shipstrike
from cetacean_incidents.apps.entanglements.models import Entanglement

from forms import ImportCSVForm
from csv_import import parse_csv

def _process_import_notes(notes, row, filename):
    if 'TZ' in os.environ:
        timezone = pytz.timezone(os.environ['TZ'])
    else:
        timezone = pytz.utc
    header = u"""<p>Imported on <span class="date">%s</span> from <span class="filename">%s</span>.</p>\n""" % (
        esc(datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %z')),
        esc(filename),
    )
    
    err = u""
    
    if 'mergeable' in notes:
        err += u"""<div class="section">Found these possible duplicates when importing:\n"""
        err += "  <ul>\n"
        for dup in notes['mergeable']:
            err += u"    <li>%06d. %s</li>\n" % (
                dup.pk, 
                esc(unicode(dup)),
            )
        err += "  </ul>\n"
        err += "</div>\n"
    
    def _error_columns(error_message, columns):
        o = u"""<div class="section">%s\n""" % error_message
        o += u"""  <table class="imported_entry">\n"""
        for key in columns:
            value = row[key]
            if value != '':
                o += u"    <tr><th>%s</th><td>%s</td></tr>\n" % (
                    esc(key),
                    esc(value),
                )
        o += u"  </table>\n"
        o += u"</div>"
        return o
    
    if 'ignored_column' in notes:
        err += _error_columns(
            'Some non-blank columns were ignored:',
            sorted(notes['ignored_column']),
        )
    
    if 'unimportable_column' in notes:
        err += _error_columns(
            'Some non-blank columns don\'t correspond to any field in the database:',
            sorted(notes['unimportable_column']),
        )

    if 'unimportable_value' in notes:
        err += _error_columns(
            'Some non-blank columns\' values don\'t correspond to any field in the database:',
            sorted(notes['unimportable_value']),
        )

    if 'unknown_value' in notes:
        err += _error_columns(
            'Some non-blank columns\' values weren\'t understood:',
            sorted(notes['unknown_value']),
        )

    if 'unknown_values' in notes:
        for col_set in notes['unknown_values']:
            err += _error_columns(
                'Some non-blank columns\' combined values weren\'t understood:',
                sorted(col_set),
            )

    if 'odd_value' in notes:
        err += _error_columns(
            'Some non-blank columns\' values were only partly understood:',
            sorted(notes['odd_value']),
        )

    # add a table of the original fields
    orig = u"""<div class="section">Original entry:\n"""
    orig += u"""  <table class="imported_entry">\n"""
    for key in sorted(row.keys()):
        value = row[key]
        if value != '':
            orig += u"    <tr><th>%s</th><td>%s</td></tr>\n" % (
                esc(key),
                esc(value),
            )
    orig += u"  </table>\n"
    orig += u"</div>\n"
    
    result = u"""<table class=layout><tr><td class="layout left_side">\n""" + header + err + u"""\n</td><td class="layout right_side">""" + orig + u"</td></tr></table>\n"
    
    return result

def _save_row(r, filename):
    data = r['data']
    
    ### animal
    a = r['data']['animal']

    # check for existing animals
    animal_query = Q()
    if 'field_number' in a:
        animal_query |= Q(field_number__iexact=a['field_number'])
    if 'name' in a:
        animal_query |= Q(name__icontains=a['name'])
    if animal_query: # bool(Q()) is False
        animal_matches = Animal.objects.filter(animal_query)
        if animal_matches:
            a['import_notes']['mergeable'] = animal_matches

    animal_kwargs = copy(a)
    animal_kwargs['import_notes'] = _process_import_notes(a['import_notes'], r['row'], filename)
    animal = Animal(**animal_kwargs)
    animal.clean()
    animal.save()

    ### case(s)
    c = r['data']['case']

    c['animal'] = animal

    if not isinstance(c['__class__'], set):
        c['__class__'] = set((c['__class__'],))
    cases_classes = set()
    for cls in c['__class__']:
        cases_classes.add({
            'Case': Case,
            'Shipstrike': Shipstrike,
            'Entanglement': Entanglement,
        }[cls])
    
    cases = []
    for cls in cases_classes:
        kwargs = copy(c)
        kwargs['import_notes'] = _process_import_notes(c['import_notes'], r['row'], filename)
        del kwargs['__class__']
        del kwargs['classification']
        if 'entanglement' in c:
            if cls is Entanglement:
                kwargs.update(c['entanglement'])
            del kwargs['entanglement']
        cases.append(cls(**kwargs))
    
    for case in cases:
        case.clean()
        case.save()

    ### observations(s)
    l = r['data']['location']
    o = r['data']['observation']
    
    l_kwargs = copy(l)
    del l_kwargs['lat']
    del l_kwargs['lon']
    
    observations = []
    def _make_observation(kwargs):
        del kwargs['split']
        del kwargs['alive_condition']
        del kwargs['exam_condition']
        del kwargs['initial_condition']
        del kwargs['observation_extensions']

        kwargs['animal'] = animal
        kwargs['location'] = Location.objects.create(**l_kwargs)
        kwargs['import_notes'] = _process_import_notes(o['import_notes'], r['row'], filename)

        observations.append(Observation(**kwargs))
    
    if o['split']:
        # create seperate initial and exam observations
        if o['initial']:
            i_kwargs = copy(o)
            i_kwargs['condition'] = o['initial_condition']
            i_kwargs['exam'] = False
            _make_observation(i_kwargs)
        
        if o['exam']:
            e_kwargs = copy(o)
            e_kwargs['condition'] = o['exam_condition']
            e_kwargs['initial'] = False
            _make_observation(e_kwargs)
    else:
        _make_observation(copy(o))
    
    for obs in observations:
        obs.save()
        obs.cases = cases
        if 'entanglement_observation' in o['observation_extensions']:
            eo_kwargs = copy(o['observation_extensions']['entanglement_observation'])
            eo_kwargs['observation_ptr'] = obs
            eo = EntanglementObservation(**eo_kwargs)
            eo.save()
        if 'shipstrike_observation' in o['observation_extensions']:
            sso_kwargs = copy(o['observation_extensions']['shipstrike_observation'])
            sso_kwargs['observation_ptr'] = obs
            sso = ShipstrikeObservation(**sso_kwargs)
            sso.save()
        
    ### documents
    if 'documents' in r['data']:
        for doc in r['data']['documents']:
            kwargs = copy(doc)
            del kwargs['attach_to']
            if doc['attach_to'] == 'case':
                for c in cases:
                    kwargs['attached_to'] = c
                    d = Document(**kwargs)
                    d.save()
            elif doc['attach_to'] == 'animal':
                kwargs['attached_to'] = animal
                d = Document(**kwargs)
                d.save()

# Revisions should always correspond to transactions!
# Note that the TransactionMiddleware won't help us here, because the
# view doesn't throw an exception if there's an error.
@transaction.commit_on_success
@revision.create_on_success
def _save_results(results, filename):
    for r in results:
        _save_row(r, filename)

# TODO perms
@login_required
def import_csv(request):
    
    results = None
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            results = parse_csv(form.cleaned_data['csv_file'])
            
            if not form.cleaned_data['test_run']:
                # process the results
                _save_results(results, filename=form.cleaned_data['csv_file'].name)
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
    
