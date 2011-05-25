from copy import copy
import csv
import datetime
from decimal import Decimal
import os
import pytz

from django import forms
from django.utils.html import conditional_escape as esc

from cetacean_incidents.apps.contacts.models import Contact

from cetacean_incidents.apps.entanglements.models import EntanglementObservation

from cetacean_incidents.apps.incidents.models import Observation

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.tags.models import Tag

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

from . import CURRENT_IMPORT_TAG

from forms import ImportCSVForm

class ImportObservationsCSVForm(ImportCSVForm):
    
    original_observation = forms.ModelChoiceField(
        # only observations with entanglement data
        queryset = Observation.objects.exclude(
            entanglements_entanglementobservation__isnull= True,
        ).order_by('pk'),
        required= True,
    )

FIELDNAMES = (
     'SightingEGNo', # observation.animal.name; ignored.
     'SightingYear', # observation.datetime_observed.year
                     # observation.datetime_reported.year
    'SightingMonth', # observation.datetime_observed.month
      'SightingDay', # observation.datetime_observed.day
     'SightingTime', # observation.datetime_observed.hour
                     # observation.datetime_observed.minute
        'Age Class', # observation.age_class
         'Latitude', # observation.location.coordinates
        'Longitude', # observation.location.coordinates
     'ObserverCode', # observation.observer.name
)

def parse_csv(csv_file, original_observation):
    '''\
    Given a file-like object with CSV data, return a tuple with one item for
    each row. The items are a dictionary like so:
    {
        'animals': (<animal>,),
        'cases': (<case>,),
        etc...
    }
    Where <animal>, <case> etc. are dictionaries with model fieldnames as keys.
    
    May also throw an exception if the CSV data isn't understood.
    '''
    
    # TODO merge with strandings_parse.parse_csv
    
    data = csv.DictReader(csv_file, dialect='excel')
    
    row_results = []
    
    for i, row in enumerate(data):
        # normalize cell values and check for unhandled fieldnames
        empty_row = True
        for k in row.keys():
            if row[k] is None:
                row[k] = ''
            row[k] = row[k].strip()
            if row[k] != '':
                empty_row = False
                if k not in FIELDNAMES:
                    #raise UnrecognizedFieldError("%s:%s" % (k, row[k]))
                    print u"""Warning: unrecognized field "%s": "%s\"""" % (k, row[k])
        if empty_row:
            continue
        
        new = {}
        
        o = parse_observation(row, original_observation)
        new['observation'] = o
        l = parse_location(row, o)
        new['location'] = l
        new['observer'] = {
            'name': row['ObserverCode'],
            'person': False,
        }
        
        row_results.append({'row_num': i, 'row': row, 'data': new})
        
    return tuple(row_results)

def parse_observation(row, orig):
    
    o = {
        'import_notes': {},
    }
    
    # animal
    o['animal'] = orig.animal
    
    # cases
    o['cases'] = orig.cases.all()
    
    # initial defaults to False

    # exam defaults to False

    # narrative defaults to ''
    
    # observer is handled elsewhere

    # datetime_observed
    o['datetime_observed'] = UncertainDateTime(
        year= int(row['SightingYear']),
        month= int(row['SightingMonth']),
        day= int(row['SightingDay']),
        hour= int(row['SightingTime'][-4:-2]), # index from the end in case 
        minute= int(row['SightingTime'][-2:]), # there's no leading zero on the
                                               # hour
    )
    
    # location handled elsewhere
    
    # observer_vessel defaults to None

    # reporter defaults to None

    # datetime_reported
    o['datetime_reported'] = UncertainDateTime(year=int(row['SightingYear']))
    
    # taxon
    o['taxon'] = orig.taxon

    # animal_length defaults to None
    # animal_length_sigdigs defaults to None

    # age_class
    o['age_class'] = {
        'J': 'ju',
        'A': 'ad',
    }[row['Age Class']]
    
    # gender
    o['gender'] = orig.gender
    
    # animal_description defaults to ''
    
    # ashore
    o['ashore'] = orig.ashore

    # condition
    #        (0, 'unknown'),
    #        (1, 'alive'),
    #        (6, 'dead, carcass condition unknown'),
    #        (2, 'fresh dead'),
    #        (3, 'moderate decomposition'),
    #        (4, 'advanced decomposition'),
    #        (5, 'skeletal'),
    o['condition'] = orig.condition
    
    # wounded defaults to None
    o['wounded'] = orig.wounded
    
    # wound_description defaults to ''
    
    # documentation
    o['documentation'] = orig.documentation

    # tagged deafults to None
    o['tagged'] = orig.tagged

    # biopsy defaults to None
    o['biopsy'] = orig.biopsy
    
    # genetic_sample
    o['genetic_sample'] = orig.genetic_sample
    
    # indication_entanglement
    o['indication_entanglement'] = orig.indication_entanglement
    
    # indication_shipstrike
    o['indication_shipstrike'] = orig.indication_shipstrike
    
    ### ObservationExtensions
    o['observation_extensions'] = {}
    
    ## EntanglementObservation
    eo = {}
    orig_eo = orig.entanglements_entanglementobservation
    
    # anchored
    eo['anchored'] = orig_eo.anchored
    
    # gear_description defaults to ''
    
    # gear_body_location defaults to []
    
    # entanglement_details
    
    # gear_retrieved
    eo['gear_retrieved'] = orig_eo.gear_retrieved
    
    # gear_retriever defaults to None
    
    # gear_given_data defaults to None
    
    # gear_giver defaults to None
    
    # disentanglement_attempted defaults to None
    
    # disentanglement_outcome
    eo['disentanglement_outcome'] = orig_eo.disentanglement_outcome
    
    o['observation_extensions']['entanglement_observation'] = eo

    return o

def parse_location(row, observation_data):

    l = {}
    
    # description defaults to ''
    
    # country defaults to None

    # waters defaults to None

    # state defaults to None
    
    # coordinates
    lat = Decimal(row['Latitude'])
    lon = - Decimal(row['Longitude'])
    l['coordinates'] = "%s,%s" % (lat, lon)
    
    return l

def _process_import_notes(notes, row, filename):
    if 'TZ' in os.environ:
        timezone = pytz.timezone(os.environ['TZ'])
    else:
        timezone = pytz.utc
    header = u"""<p>Imported on <span class="date">%s</span> from <span class="filename">%s</span>.</p>\n""" % (
        esc(datetime.datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %z')),
        esc(filename),
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
    
    result = u"""<table class=layout><tr><td class="layout left_side">\n""" + header + u"""\n</td><td class="layout right_side">""" + orig + u"</td></tr></table>\n"
    
    return result

def _make_tag(thing, user):
    tag = Tag(entry=thing, user=user, tag_text=CURRENT_IMPORT_TAG)
    tag.clean()
    tag.save()

def _save_row(r, filename, user):

    ### the location
    l = r['data']['location']
    l_kwargs = copy(l)
    loc = Location(**l_kwargs)
    loc.clean()
    loc.save()
    
    ### the observer contact
    c = r['data']['observer']
    c_kwargs = copy(c)
    if Contact.objects.filter(**c_kwargs).exists():
        obs_con = Contact.objects.get(**c_kwargs)
    else:
        obs_con = Contact(**c_kwargs)
        obs_con.clean()
        obs_con.save()
        _make_tag(obs_con, user)

    ### the observation
    o = r['data']['observation']
    o_kwargs = copy(o)
    o_kwargs['location'] = loc
    o_kwargs['observer'] = obs_con
    o_kwargs['import_notes'] = _process_import_notes(o['import_notes'], r['row'], filename)
    # the 'cases' field has to be handled after saving
    del o_kwargs['cases']
    # the entanglementobservation is handled seperately
    del o_kwargs['observation_extensions']
    obs = Observation(**o_kwargs)
    obs.clean()
    obs.save()
    obs.cases = o['cases']
    _make_tag(obs, user)

    ### the entanglementobservation
    if 'entanglement_observation' in o['observation_extensions']:
        eo_kwargs = copy(o['observation_extensions']['entanglement_observation'])
        eo_kwargs['observation_ptr'] = obs
        eo = EntanglementObservation(**eo_kwargs)
        eo.clean()
        eo.save()

def process_results(results, filename, user):
    '''\
    Create all the new models described in results in a single transaction and
    a single revision.
    '''
    # process the results
    for r in results:
        print r['row_num']
        _save_row(r, filename, user)

