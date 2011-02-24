import operator
from itertools import imap, count
from decimal import Decimal
from datetime import datetime
import re
import csv

from django.db import transaction
from django.forms import ValidationError
from django.contrib.localflavor.us.us_states import STATES_NORMALIZED

from reversion import revision

from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.locations.utils import dms_to_dec
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.incidents.models import Animal
from cetacean_incidents.apps.documents.models import DocumentType

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

def translate_taxon(data, key, abbr):
    data[key] = {
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
    }[abbr]

    if abbr in set(('UNWH', 'UNRW', 'FI/SEWH', 'RIWH?')):
        odd_value(data, key)

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

def parse_animal(row, temp_id):
    
    a = {
        'id': temp_id.next(),
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
        translate_taxon(a, 'determined_taxon', row['Common Name'])
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
        (None,  False, False): (False, False, False),
        (False, None,  None ): (False, False, False),
        (False, False, None ): (False, False, False),
        (False, False, False): (False, False, True),

        (None,  True,  None ): (True,  False, True),
        (True,  None,  None ): (True,  False, False),
        (True,  True,  None ): (True,  False, True),
        (True,  False, False): (True,  False, False),
        (True,  True,  False): (True,  False, False),

        (None,  False, True ): (False, True,  False),
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

def parse_case(row, temp_id, animal_data):
    
    # animal
    c = {
        'id': temp_id.next(),
        'animal': animal_data['id'],
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
           'C,M': ('Case', 'Shipstrike'),
          'M,SS': ('Case', 'Shipstrike'),
          'M, C': ('Case', 'Shipstrike'),
         'M, SS': ('Case', 'Shipstrike'),
           'M,E': ('Case', 'Entanglement'),
          'M, E': ('Case', 'Entanglement'),
          'E, M': ('Case', 'Entanglement'),
           'E,M': ('Case', 'Entanglement'),
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

def parse_location(row, temp_id):

    l = {
        'id': temp_id.next(),
        'import_notes': {},
    }
    
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
    if row['LATITUDE']:
        try:
            lat = NiceLocationForm._clean_coordinate(row['LATITUDE'], is_lat=True)
            lat = dms_to_dec(lat)
            l['lat'] = lat
        except ValidationError as e:
            unknown_value(l, 'LATITUDE')
    if row['LONGITUDE']:
        try:
            lon = NiceLocationForm._clean_coordinate(row['LONGITUDE'], is_lat=False)
            lon = dms_to_dec(lon)
            # assume west
            if lon > 0:
                odd_value(l, 'LONGITUDE')
            lon = - abs(lon)
            l['lon'] = lon
        except ValidationError:
            unknown_value(l, 'LONGITUDE')
    if ('lat' in l) != ('lon' in l):
        unknown_values(l, ('LATITUDE', 'LONGITUDE'))
    if ('lat' in l) and ('lon' in l):
        l['coordinates'] = "%s,%s" % (l['lat'], l['lon'])
    
    return l

def parse_observation(row, temp_id, case_data, location_data):
    
    o = {
        'id': temp_id.next(),
        'import_notes': {},
    }
    
    # animal
    o['animal'] = case_data['animal']
    
    # cases
    o['cases'] = case_data['id']
    
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
    o['datetime_observed'] = uncertain_datetime.to_unicode()
    
    # location
    o['location'] = location_data['id']
    
    # observer_vessel defaults to None

    # reporter defaults to None

    # datetime_reported
    o['datetime_reported'] = UncertainDateTime(uncertain_datetime.year).to_unicode()
    
    # taxon
    translate_taxon(o, 'taxon', row['Common Name'])

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
    if case_data['__class__'] == 'Entanglement' or case_data['__class__'] is set and 'Entanglement' in case_data['__class__']:
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
              '0': False,
             'no': False,
             'No': False,
              '1': True,
            'Yes': True,
        }[row['Disentangle attempt on live whale?']]
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

            (True, 'entangled'): ('entg', False),
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
    
    return o

def parse_documents(row, temp_id, animal_data, case_data):
    
    docs = []
    
    for doc_key, data, doctype_name in (
        ('CCS web page', case_data, 'CCS web page'),
        ('Ceta data rec', animal_data, 'Cetacean Data Record'),
        ('Hi Form?', case_data, 'Human-Interaction Form'),
        ('Histo results', animal_data, 'Histological Findings'),
        ('Lg Whale email', case_data, 'Large Whale email'),
        ('Stranding Rept?', case_data, 'Stranding Report (Level-A)'),
    ):
        if row[doc_key]:
            yes_values = set(('1',))
            no_values = set(('', '0'))
            if row[doc_key] in yes_values:
                # create a new document
                d = {
                    'id': temp_id.next(),
                    'attached_to': data['id'],
                    'document_type': DocumentType.objects.get(name=doctype_name),
                }
                docs.append(d)
            elif row[doc_key] not in no_values:
                odd_value(data, doc_key)

    return docs

@transaction.commit_on_success
@revision.create_on_success
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
    temp_id = imap(operator.neg, count(1))
    
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
        #if row['Common Name'] == 'BEWH':
        #    continue
        
        new = {
            'observation': [],
            'location': [],
        }
        changed = {}
        
        a = parse_animal(row, temp_id)
        if a['id'] < 0:
            new['animal'] = a
        else:
            changed['animal'] = a
        
        c = parse_case(row, temp_id, a)
        if c['id'] < 0:
            new['case'] = c
        else:
            changed['case'] = c
        
        # observations are always new
        l = parse_location(row, temp_id)
        new['location'] = l
        o = parse_observation(row, temp_id, case_data=c, location_data=l)
        new['observation'] = o
        
        docs = parse_documents(row, temp_id, animal_data=a, case_data=c)
        if docs:
            new['documents'] = docs
        
        row_results.append({'row_num': i, 'row': row, 'model': new, 'changed': changed})
        
        #if i + 1 == 3:
        #    break
    
    return tuple(row_results)

