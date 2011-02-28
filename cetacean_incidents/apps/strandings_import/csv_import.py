import os
from copy import copy
import operator
from itertools import imap, count
from decimal import Decimal
from datetime import datetime
import pytz
import re
import csv

from django.db.models import Q
from django.forms import ValidationError
from django.contrib.localflavor.us.us_states import STATES_NORMALIZED
from django.utils.html import conditional_escape as esc

from cetacean_incidents.apps.countries.models import Country

from cetacean_incidents.apps.documents.models import DocumentType
from cetacean_incidents.apps.documents.models import Document

from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.entanglements.models import EntanglementObservation

from cetacean_incidents.apps.locations.utils import dms_to_dec
from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.incidents.models import Animal
from cetacean_incidents.apps.incidents.models import Case
from cetacean_incidents.apps.incidents.models import Observation

from cetacean_incidents.apps.shipstrikes.models import Shipstrike
from cetacean_incidents.apps.shipstrikes.models import ShipstrikeObservation

from cetacean_incidents.apps.tags.models import Tag

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime


CURRENT_IMPORT_TAG = u"This entry was created by an automated import has not yet been reviewed by a human. See 'Import Notes' for details."

IMPORT_TAGS = set((CURRENT_IMPORT_TAG,))

class UnrecognizedFieldError(ValueError):
    
    # require a column name
    def __init__(self, column_name, *args, **kwargs):
        super(UnrecognizedFieldError, self).__init__(u'"%s"' % column_name, *args, **kwargs)

FIELDNAMES = set((
# ignorable
 'New event ?',
'Strike form?',
   'CCS Forms',

# animal
             'Field # ', # field_number
           'Individual', # name
              'Sp Ver?', # if yes, set taxon
          'Common Name', # determined_taxon (also used for Observation.taxon)
               'Alive?', # determined_dead_before (also used for Observation.condition)
                 'Date', # determined_dead_before (if not alive) (also used for Observation.datetime_observed and Observation.datetime_reported)
            'Necropsy?', # necropsy, partial_necropsy
        'Full necropsy', # necropsy, partial_necropsy
     'Partial necropsy', # necropsy, partial_necropsy
'Carcass Dispossed Y/N', # carcass_disposed
        'Ceta data rec', # document on an animal with type 'Cetacean Data Record'
        'Histo results', # document on an animal with type 'Histological Findings'

# case
          'Classification', # case_type
               'Re-sight?', # just note in import_notes
  'Resight: Date 1st Seen', # just note in import_notes
        'Event Confirmed?', # valid
'NMFS Database Regional #', # just note in import_notes
        'NMFS Database # ', # just note in import_notes
'Entanglement or Collision #', # just note in import_notes
            'CCS web page', # document attached to case with type 'CCS web page'
                'Hi Form?', # document attached to case with type 'Human-Interaction Form'
          'Lg Whale email', # document attached to case with type 'Large Whale email'
         'Stranding Rept?', # document attached to case with type 'Stranding Report (Level-A)'

# observation
                  'Comments', # narrative
                      'Date', # datetime_observed and datetime_reported (just the year)
            'Initial report', # just note in import_notes
'Disentanglement  or Response Agencies', # just note in import_notes
               'Common Name', # taxon
                   'Sp Ver?', # just note in import_notes
                       'Sex', # gender
'Age (at time of event)  *PRD indicated age by length as presented in field guides ', # age_class
  'Total Length (cm)  *=est', # animal_description
' Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
'                               Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
                    'Alive?', # condition
          'Initial condtion', # condition, observation splitting, initial
             'Exam condtion', # condition, observation splitting, exam
              'Photo w/file', # if yes, there's documentation, otherwise unknown
                  'Pictures', # documentation
           'Genetics Sample', # genetic_sample
                      'HI ?', # human_interaction
'Indication of Entanglement', # indication_entanglement
 'Indication of Ship Strike', # indication_shipstrike
                 'Phone Log', # document(s) attached to observation with type 'Phone Log entry'. just note for now.
    
# entanglement observations
                              'Gear', # entanglement_details
  'Disentangle status of live whale', # disentanglement_outcome
'Disentangle attempt on live whale?', # disentanglement_outcome

# location
        'LATITUDE', # coordinates
       'LONGITUDE', # coordinates
'General location', # description
        'State/EZ', # state, waters, country
))
CLASSIFICATIONS = set((
    'M', # mortality
    'E', # entanglement
    'Injury', # other injury
))

# various length units, in meters
CENTIMETER = Decimal(1) / 100
INCH = Decimal('2.54') * CENTIMETER
FOOT = 12 * INCH
def parse_length(length):
    '''\
    Returns meters.
    '''
    
    # trim
    length = length.strip()
    
    m = None
    
    # centimeters
    match = re.match(r'(?i)(?P<length>[0-9.]+)\s*(cm)?$', length)
    if match:
        cm = Decimal(match.group('length'))
        m = cm / 100
    
    # inches
    match = re.match(r'(?i)(?P<length>[0-9.]+)\s*(in|")$', length)
    if match:
        inches = Decimal(match.group('length'))
        m = inches * INCH
    
    # feet
    match = re.match(r"(?i)(?P<length>[0-9.]+)\s*(ft|')$", length)
    if match:
        feet = Decimal(match.group('length'))
        m = feet * FOOT

    if not m:
        raise ValueError("can't figure out length: %s" % length)
    
    return m

def parse_date(date):
    for format in ('%Y/%m/%d', '%d-%b-%y', '%m/%d/%Y'):
        try:
            return datetime.strptime(date, format).date()
        except ValueError:
            pass
    raise ValueError("can't parse datetime %s" % date)

ASHORE_KEYS = (
    ' Ashore?     - Did the whale/carcass ultimately come ashore',
    '                               Ashore?     - Did the whale/carcass ultimately come ashore',
)
def get_ashore(row):
    # ashore has a couple variations:
    for k in ASHORE_KEYS:
        if k in row:
            ashore = row[k]
        
    return {
        "": None,
        "0": False,
        "1": True,
    }[ashore]

def translate_taxon(data, data_key, row):
    data[data_key] = {
        'BEWH': Taxon.objects.get(tsn=180506), # beaked whales
        'BRWH': Taxon.objects.get(tsn=612597), # bryde's whale
        'FIWH': Taxon.objects.get(tsn=180527), # finback
        'HUWH': Taxon.objects.get(tsn=180530), # humpback
        'MIWH': Taxon.objects.get(tsn=180524), # minke
        'RIWH': Taxon.objects.get(tsn=180537), # right
        'RIWH?': Taxon.objects.get(tsn=180537), # right
        'SEWH': Taxon.objects.get(tsn=180526), # sei whale
        'SPWH': Taxon.objects.get(tsn=180488), # sperm whale
        'UNAN': None,                          # unknown animal
        'UNBA': Taxon.objects.get(tsn=552298), # unknown baleen whale
        'UNRW': Taxon.objects.get(tsn=552298), # unknown rorqual
        'FI/SEWH': Taxon.objects.get(tsn=180523), # finback or sei whale
        'UNWH': Taxon.objects.get(tsn=180403), # unknown whale
    }[row['Common Name']]

    if row['Common Name'] in set(('UNWH', 'UNRW', 'FI/SEWH', 'RIWH?')):
        odd_value(data, 'Common Name')

### Three types of import problems

def note_error(key, column_name, notes):
    if not key in notes:
        notes[key] = set()
    notes[key].add(column_name)

## - a column is ignored
def ignored_column(data, column_name):
    note_error('ignored_column', column_name, data['import_notes'])

## - a column can't be represented
def unimportable_column(data, column_name):
    note_error('unimportable_column', column_name, data['import_notes'])

## - a column's value can't be represented
def unimportable_value(data, column_name):
    note_error('unimportable_value', column_name, data['import_notes'])

## - a column's value isn't understood
def unknown_value(data, column_name):
    note_error('unknown_value', column_name, data['import_notes'])

## - a combination of columns' values isn't understood
def unknown_values(data, column_names):
    note_error('unknown_values', column_names, data['import_notes'])

## - a column's value is recognized, but can't be fully represented
def odd_value(data, column_name):
    note_error('odd_value', column_name, data['import_notes'])

def parse_animal(row):
    
    a = {
        'import_notes': {},
    }
    
    if row['NMFS Database # ']:
        unimportable_column(a, 'NMFS Database # ')
    if row['NMFS Database Regional #']:
        unimportable_column(a, 'NMFS Database Regional #')
    
    # field_number
    if row['Field # ']:
        a['field_number'] = row['Field # ']
    
    # name
    if row['Individual']:
        a['name'] = row['Individual']
    
    # determined_taxon
    if {
        '': False,
        '?': False,
        '0': False,
        '1': True,
    }[row['Sp Ver?']]:
        translate_taxon(a, 'determined_taxon', row)
    # the value isn't understood
    if row['Sp Ver?'] not in set(('', '0', '1')):
        unknown_value(a, 'Sp Ver?')
    
    # determined_gender defaults to ''

    # determined_dead_before
    dead = {
        '': False,
        '?': False,
        '0': True,
        '1': False,
    }[row['Alive?']]
    if dead:
        a['determined_dead_before'] = parse_date(row['Date'])
    # the value isn't understood
    if row['Alive?'] not in set(('', '0', '1')):
        unknown_value(a, 'Alive?')
    
    # carcass_disposed
    a['carcass_disposed'] = {
        '': None,
        '0': False,
        'N': False,
        '1': True,
        'Y': True,
    }[row['Carcass Dispossed Y/N']]
    
    # partial_necropsy
    # necropsy
    a['necropsy'], a['partial_necropsy'], understood = {
        (None,  None,  None ): (False, False, True),
        (None,  False, False): (False, False, True),
        (False, None,  None ): (False, False, True),
        (False, False, None ): (False, False, True),
        (False, False, False): (False, False, True),

        (None,  True,  None ): (True,  False, True),
        (True,  None,  None ): (True,  False, False),
        (True,  True,  None ): (True,  False, True),
        (True,  False, False): (True,  False, False),
        (True,  True,  False): (True,  False, True),

        (None,  False, True ): (False, True,  True),
        (False, False, True ): (False, True,  False),
        (False, None,  True ): (False, True,  False),
        (True,  None,  True ): (False, True,  False),
        (True,  False, True ): (False, True,  False),

        (None,  True,  True ): (True,  True, True),
        (False, True,  True ): (True,  True, False),
        (True,  True,  True ): (True,  True, True),
        
    }[
        {
             '': None,
            '0': False,
            '1': True,
        }[row['Necropsy?']],
        {
              '': None,
             '0': False,
            'na': False,
             '1': True,
        }[row['Full necropsy']],
        {
              '': None,
             '0': False,
            'na': False,
             '1': True,
        }[row['Partial necropsy']],
    ]
    if not understood:
        unknown_values(a, ('Necropsy?', 'Full necropsy', 'Partial necropsy'))
    
    # cause_of_death defaults to ''
    
    return a

def parse_case(row):
    
    # animal
    c = {
        'import_notes': {},
    }
    
    # case_type
    cls = row['Classification']
    cls, resight = re.subn(r'(?i)\s*\(Resight\)', '', cls)
    resight = bool(resight)
    
    c['__class__'] = {
              '': 'Case',
        'Injury': 'Case',
             'M': 'Case',
           'M ?': 'Case', # TODO mark as suspected?
   'M(resight?)': 'Case', # TODO mark in import notes
'M(Likely resight)': 'Case', # TODO mark in import notes
'M(Incidental Take)': 'Case',
             'C': 'Shipstrike',
            'SS': 'Shipstrike',
             'E': 'Entanglement',
      'E  (CAN)': 'Entanglement',
     'E (lures)': 'Entanglement',
           'C,M': set(('Case', 'Shipstrike')),
          'M,SS': set(('Case', 'Shipstrike')),
          'M, C': set(('Case', 'Shipstrike')),
         'M, SS': set(('Case', 'Shipstrike')),
           'M,E': set(('Case', 'Entanglement')),
          'M, E': set(('Case', 'Entanglement')),
          'E, M': set(('Case', 'Entanglement')),
           'E,M': set(('Case', 'Entanglement')),
    }[cls]
    if resight or row['Classification'] in set((
        '',
        'M ?',
        'M(resight?)',
        'M(Likely resight)',
        'M(Incidental Take)',
        'E  (CAN)',
        'E (lures)',
    )):
        odd_value(c, 'Classification')
    
    c['classification'] = cls
    
    if row['Re-sight?']:
        unimportable_column(c, 'Re-sight?')
    if row['Resight: Date 1st Seen']:
        unimportable_column(c, 'Resight: Date 1st Seen')
    
    # valid
    c['valid'] = {
        '': 1,
        '0': 1,
        '1': 2,
    }[row['Event Confirmed?']]
    
    # happened_after defaults to None
    
    # human_interaction
    # choices:
    # ('unk', 'not yet determined'),
    # ('yes', 'yes'),
    # ('no' , 'no'),
    # ('cbd', 'can\'t be determined'),
    c['human_interaction'] = {
        '': 'unk',
        '1/cbd?': 'unk',
        '0': 'no',
        '1': 'yes',
        'cbd': 'cbd',
        'CBD': 'cbd',
    }[row['HI ?']]
    if c['human_interaction'] in set(('1/cbd?',)):
        unknown_value(c, 'human_interaction')

    # ole_investigation defaults to False
    c['ole_investigation'] = None

    ## Entanglement
    if c['__class__'] == 'Entanglement' or c['__class__'] is set and 'Entanglement' in c['__class__']:
        e = {}

        # nmfs_id defaults to ''

        # gear_fieldnumber defaults to ''

        # gear_analyzed defaults to False
        e['gear_analyzed'] = None

        # analyzed_date defaults to None

        # analyzed_by defaults to None

        # gear_types defaults to []

        # gear_owner_info defaults to None
        
        c['entanglement'] = e
    
    ## Shipstrike has no additional fields
    
    return c

def parse_location(row, observation_data):

    l = {}
    
    # description
    if row['General location']:
        l['description'] = row['General location']
    
    # country
    # waters
    # state
    ashore = get_ashore(row)
    state_input = row['State/EZ'].lower()
    if state_input == '':
        country = None
        eez = None
        state = None
    elif state_input in (('ez',)):
        country = Country.objects.get(iso='US')
        eez = True
        state = None
    elif state_input in (('can',)):
        country = Country.objects.get(iso='CA')
        eez = None
        state = None
    elif state_input in STATES_NORMALIZED.keys():
        country = Country.objects.get(iso='US')
        eez = False
        state = STATES_NORMALIZED[state_input]
    else:
        raise KeyError(row['State/EZ'])
    
    # country
    l['country'] = country

    # waters
    l['waters'] = 0
    if ashore:
        l['waters'] = 1
    elif not eez and ashore is None:
        l['waters'] = 0
    else:
        if country and not state:
            l['waters'] = 3
        elif state:
            l['waters'] = 2
    
    # state
    if state:
        l['state'] = state
    
    # coordinates
    lat = None
    lon = None
    if row['LATITUDE']:
        try:
            lat = NiceLocationForm._clean_coordinate(row['LATITUDE'], is_lat=True)
            lat = dms_to_dec(lat)
        except ValidationError as e:
            unknown_value(observation_data, 'LATITUDE')
    if row['LONGITUDE']:
        try:
            lon = NiceLocationForm._clean_coordinate(row['LONGITUDE'], is_lat=False)
            lon = dms_to_dec(lon)
            # assume west
            if lon > 0:
                odd_value(observation_data, 'LONGITUDE')
            lon = - abs(lon)
        except ValidationError:
            unknown_value(observation_data, 'LONGITUDE')
    if (lat is None) != (lon is None):
        unknown_values(observation_data, ('LATITUDE', 'LONGITUDE'))
    if (not lat is None) and (not lon is None):
        l['coordinates'] = "%s,%s" % (lat, lon)
    
    return l

def parse_observation(row, case_data):
    
    o = {
        'import_notes': {},
    }
    
    # animal
    #o['animal'] = case_data['animal']
    
    # cases
    #o['cases'] = case_data['id']
    
    # initial
    # exam
    condition_yes = set(('1', '2', '3', '3+', '4', '4+', '5', '6'))
    condition_expected = set(('', '1', '2', '3', '4', '5', '6'))
    for model_key, row_key in (
        ('initial', 'Initial condtion'),
        ('exam',    'Exam condtion'),
    ):
        o[model_key] = bool(row[row_key] in condition_yes)
        if row[row_key] not in condition_expected:
            odd_value(o, row_key)
    
    # narrative
    if row['Comments']:
        o['narrative'] = row['Comments']
    
    # observer defaults to None
    if row['Initial report']:
        unimportable_column(o, 'Initial report')

    # datetime_observed
    if not row['Date']:
        unimportable_value(o, 'Date')
    date = parse_date(row['Date'])
    uncertain_datetime = UncertainDateTime(date.year, date.month, date.day)
    o['datetime_observed'] = uncertain_datetime
    
    # location
    #o['location'] = location_data['id']
    
    # observer_vessel defaults to None

    # reporter defaults to None

    # datetime_reported
    o['datetime_reported'] = UncertainDateTime(uncertain_datetime.year)
    
    # taxon
    translate_taxon(o, 'taxon', row)

    if row['Sp Ver?']:
        unimportable_column(o, 'Sp Ver?')

    # animal_length
    if row['Total Length (cm)  *=est'] not in set(('', 'U')):
        try:
            o['animal_length'] = parse_length(row['Total Length (cm)  *=est'])
        except ValueError:
            unimportable_value(o, 'Total Length (cm)  *=est')

    # age_class
    age_key = 'Age (at time of event)  *PRD indicated age by length as presented in field guides '
    o['age_class'] = {
        '': '',
        'Y': '',
        'U': '',
        'M': '',
        'C': 'ca',
        'J': 'ju',
        'SA': 'ju',
        'S': 'ju',
        'A': 'ad',
    }[row[age_key]]
    if row[age_key] in set(('Y','S','M')):
        unknown_value(o, age_key)
    
    # gender
    o['gender'] = {
        '': '',
        'U': '',
        'm': 'm',
        'M': 'm',
        'f': 'f',
        'F': 'f',
    }[row['Sex']]
    
    # animal_description defaults to ''
    
    # ashore
    o['ashore'] = get_ashore(row)
        
    conditions = {
         '': 0,
        'U': 0,
       'na': 0,
       'NE': 0,
        '1': 1,
        '2': 2,
        '3': 3,
       '3+': 3,
        '4': 4,
       '4+': 4,
        '5': 5,
        '6': 6,
    }
    # condition
    #        (0, 'unknown'),
    #        (1, 'alive'),
    #        (6, 'dead, carcass condition unknown'),
    #        (2, 'fresh dead'),
    #        (3, 'moderate decomposition'),
    #        (4, 'advanced decomposition'),
    #        (5, 'skeletal'),
    o['initial_condition'] = conditions[row['Initial condtion']]
    o['exam_condition'] = conditions[row['Exam condtion']]
    o['alive_condition'] = {
        '': 0,
        '?': 0,
        '0': 6,
        '1': 1,
    }[row['Alive?']]
    if row['Alive?'] not in set(('', '0', '1')):
        odd_value(o, 'Alive?')
    if o['initial_condition'] == 0 and o['alive_condition'] != 0:
        o['initial_condition'] = o['alive_condition']
    if o['exam_condition'] == 0 and o['alive_condition'] != 0:
        o['exam_condition'] = o['alive_condition']
    o['split'] = False
    o['condition'] = o['initial_condition']
    if o['initial_condition'] != o['exam_condition'] and o['exam_condition'] != 0:
        o['split'] = True
    
    # wounded defaults to None
    
    # wound_description defaults to ''
    
    # documentation
    o['documentation'] = {
        (None,  None ): None,
        (None,  False): None,
        (None,  True ): True,
        (False, None ): False,
        (False, False): False,
        (True,  None ): True,
        (True,  True ): True,
        (True,  False): True,
    }[
        {
            '': None,
            '?': None,
            'No': False,
            'NO': False,
            'Yes': True,
            'video': True,
            'pending': True,
            'Gear only': True,
        }[row['Pictures']],
        {
             '': None,
            '?': None,
            '0': False,
            '1': True,
        }[row['Photo w/file']],
    ]
    if row['Pictures'] not in set(('', 'No', 'NO', 'Yes')):
        odd_value(o, 'Pictures')
    if row['Photo w/file'] not in set(('', '0', '1')):
        odd_value(o, 'Photo w/file')

    # tagged deafults to None
    # biopsy defaults to None
    
    # genetic_sample
    o['genetic_sample'] = {
        "": None,
        "0": False,
        "1": True,
    }[row['Genetics Sample']]
    
    # indication_entanglement
    o['indication_entanglement'] = {
        '': None,
        '0': False,
        '1': True,
    }[row['Indication of Entanglement']]
    
    # indication_shipstrike
    o['indication_shipstrike'] = {
        '': None,
        '0': False,
        '1': True,
    }[row['Indication of Ship Strike']]
    
    ### ObservationExtensions
    o['observation_extensions'] = {}
    
    ## EntanglementObservation
    if case_data['__class__'] == 'Entanglement' or isinstance(case_data['__class__'], set) and 'Entanglement' in case_data['__class__']:
        eo = {}
        
        # anchored defaults to None
        
        # gear_description defaults to ''
        
        # gear_body_location defaults to []
        
        # entanglement_details
        if row['Gear']:
            eo['entanglement_details'] = row['Gear']
        
        # gear_retrieved defaults to None
        
        # disentanglement_outcome
        attempt = {
               '': None,
              '.': None,
              '0': False,
             'no': False,
             'No': False,
              '1': True,
            'Yes': True,
        }[row['Disentangle attempt on live whale?']]
        if row['Disentangle attempt on live whale?'] in set((
            '.',
        )):
            unknown_value(o, 'Disentangle attempt on live whale?')
        outcome = {
            '': 'unknown',
            '?': 'unknown',
            'Carrying gear': 'gear',
            'disentangled': 'no gear',
            'Disentangled': 'no gear',
            'Entangled': 'entangled',
            'entangled': 'entangled',
            'Gear free': 'no gear',
            'Minor': 'unknown',
            'No attempt made': 'unknown',
            'NOAA, GA': 'unknown',
            'Partial Disentanglement': 'partly entangled',
            'partial disentanglement': 'partly entangled',
            'some line still embedded in dorsal peduncle': 'some gear',
            'unable to relocate': 'unknown',
            'Unknown': 'unknown',
            'unknown': 'unknown',
        }[row['Disentangle status of live whale']]
        if row['Disentangle status of live whale'] in set((
            '?',
            'Carrying gear',
            'some line still embedded in dorsal peduncle',
        )):
            odd_value(o, 'Disentangle status of live whale')
        if row['Disentangle status of live whale'] in set((
            'Minor',
            'No attempt made',
            'NOAA, GA',
            'unable to relocate',
        )):
            unknown_value(o, 'Disentangle status of live whale')
        # disentanglement_outcome choices:
        #    #('',    'unknown'),
        #    ('shed', 'gear shed'),
        #    ('mntr', 'monitor'),
        #    ('entg', 'entangled'),
        #    ('part', 'partial'),
        #    ('cmpl', 'complete'),
        #    <em>Was a disentanglement attempted and if so, what was the outcome?<em>
        #    <dl>
        #        <dt>gear shed</dt>
        #        <dd>No disentanglement was attempted since the animal had disentangled itself.</dd>
        #        <dt>monitor</dt>
        #        <dd>No disentanglement was attempted since the entanglement wasn't severe enough to warrant it.</dd>
        #        <dt>entangled</dt>
        #        <dd>A disentanglement was needed, but either couldn't be attempted or was unsuccessful.</dd>
        #        <dt>partial</dt>
        #        <dd>A disentanglement was attempted and the gear was partly removed.</dd>
        #        <dt>complete</dt>
        #        <dd>A disentanglement was attempted and the gear was completely removed.</dd>
        #    </dl>
        eo['disentanglement_outcome'], understood = {
            (None, 'unknown'): ('', True),
            (None, 'gear'): ('', False),
            (None, 'entangled'): ('', False),
            (None, 'partly entangled'): ('', False),
            (None, 'no gear'): ('', False), # could be 'shed' or 'cmpl'

            (False, 'unknown'): ('', False), # could be 'shed' or 'mntr'
            (False, 'no gear'): ('shed', True),
            (False, 'entangled'): ('entg', True),

            (True, 'entangled'): ('entg', True),
            (True, 'partly entangled'): ('part', True),
            (True, 'some gear'): ('', False),
            (True, 'no gear'): ('cmpl', True),
            (True, 'unknown'): ('', False),
        }[(attempt, outcome)]
        o['observation_extensions']['entanglement_observation'] = eo
        if not understood:
            unknown_values(o, ('Disentangle attempt on live whale?', 'Disentangle status of live whale'))
    
    ## ShipstrikeObservation
    # striking_vessel defaults to None
    if case_data['__class__'] == 'Shipstrike' or isinstance(case_data['__class__'], set) and 'Shipstrike' in case_data['__class__']:
        o['observation_extensions']['shipstrike_observation'] = {}
    
    return o

def parse_documents(row, animal_data, case_data):
    
    docs = []
    
    for doc_key, attach_to, data, doctype_name in (
        ('Ceta data rec', 'animal', animal_data, 'Cetacean Data Record'),
        ('Histo results', 'animal', animal_data, 'Histological Findings'),
        ('CCS web page', 'case', case_data, 'CCS web page'),
        ('Hi Form?', 'case', case_data, 'Human-Interaction Form'),
        ('Lg Whale email', 'case', case_data, 'Large Whale email'),
        ('Stranding Rept?', 'case', case_data, 'Stranding Report (Level-A)'),
    ):
        if row[doc_key]:
            yes_values = set(('1',))
            no_values = set(('', '0'))
            if row[doc_key] in yes_values:
                # create a new document
                d = {
                    'attach_to': attach_to,
                    'document_type': DocumentType.objects.get(name=doctype_name),
                }
                docs.append(d)
            elif row[doc_key] not in no_values:
                odd_value(data, doc_key)

    return docs

def parse_csv(csv_file, commit=False):
    '''\
    Given a file-like object with CSV data, return a tuple with one item for
    each row. The items are a dictionary like so:
    {
        'new': {
            'animals': (<animal>,),
            'cases': (<case>,),
            etc...
        }
        'changed': {
            'animals': {pk: <animal>},
            etc...
        }
    }
    Where <animal>, <case> etc. are dictionaries with model fieldnames as keys.
    
    May also throw an exception if the CSV data isn't understood.
    '''
    
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
        
        # ignore beaked whales
        if row['Common Name'] == 'BEWH':
            continue
        
        new = {
            'observation': [],
            'location': [],
        }
        changed = {}
        
        a = parse_animal(row)
        new['animal'] = a
        
        c = parse_case(row)
        new['case'] = c
        
        # observations are always new
        o = parse_observation(row, c)
        new['observation'] = o
        l = parse_location(row, o)
        new['location'] = l
        
        docs = parse_documents(row, a, c)
        if docs:
            new['documents'] = docs
        
        row_results.append({'row_num': i, 'row': row, 'data': new})
        
    return tuple(row_results)

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

def _make_tag(thing, user):
    tag = Tag(entry=thing, user=user, tag_text=CURRENT_IMPORT_TAG)
    tag.clean()
    tag.save()

def _save_row(r, filename, user):
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
    _make_tag(animal, user)

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
        _make_tag(case, user)

    ### observations(s)
    l = r['data']['location']
    o = r['data']['observation']
    
    l_kwargs = copy(l)
    
    observations = []
    def _make_observation(kwargs):
        del kwargs['split']
        del kwargs['alive_condition']
        del kwargs['exam_condition']
        del kwargs['initial_condition']
        del kwargs['observation_extensions']

        kwargs['animal'] = animal
        loc = Location(**l_kwargs)
        loc.clean()
        loc.save()
        kwargs['location'] = loc
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
        obs.clean()
        obs.save()
        obs.cases = cases
        _make_tag(obs, user)
        if 'entanglement_observation' in o['observation_extensions']:
            eo_kwargs = copy(o['observation_extensions']['entanglement_observation'])
            eo_kwargs['observation_ptr'] = obs
            eo = EntanglementObservation(**eo_kwargs)
            eo.clean()
            eo.save()
        if 'shipstrike_observation' in o['observation_extensions']:
            sso_kwargs = copy(o['observation_extensions']['shipstrike_observation'])
            sso_kwargs['observation_ptr'] = obs
            sso = ShipstrikeObservation(**sso_kwargs)
            sso.clean()
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
                d.clean()
                d.save()

def process_results(results, filename, user):
    '''\
    Create all the new models described in results in a single transaction and
    a single revision.
    '''
    # process the results
    for r in results:
        print r['row_num']
        _save_row(r, filename, user)
    
