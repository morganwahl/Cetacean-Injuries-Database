from copy import copy
import csv
import datetime
from decimal import Decimal
import os
import pytz
import re

from django.db.models import Q
from django.forms import ValidationError
from django.utils.html import conditional_escape as esc

from django.contrib.localflavor.us.us_states import STATES_NORMALIZED

from cetacean_incidents.apps.countries.models import Country

from cetacean_incidents.apps.documents.models import (
    Document,
    DocumentType,
)

from cetacean_incidents.apps.entanglements.models import (
    Entanglement,
    EntanglementObservation,
)

from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.locations.models import Location
from cetacean_incidents.apps.locations.utils import dms_to_dec

from cetacean_incidents.apps.incidents.models import (
    Animal,
    Case,
    Observation,
)

from cetacean_incidents.apps.shipstrikes.models import (
    Shipstrike,
    ShipstrikeObservation,
)

from cetacean_incidents.apps.tags.models import Tag

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

from . import CURRENT_IMPORT_TAG

FIELDNAMES = set((
# ignorable
 'New event ?',
  'New Case ?',
'File complete? (internal use)',
'Strike form?',
   'CCS Forms',

# animal
             'Field # ', # field_number (regional database # in 2005 data)
          'Field # (S)', # field_number in 2005 data
           'Individual', # name
               'Indiv.', # name
              'Sp Ver?', # if yes, set taxon
          'Common Name', # determined_taxon (also used for Observation.taxon)
               'Alive?', # determined_dead_before (also used for Observation.condition)
'    Alive?       Was the animal ever seen alive during this event? 0=No,1=Yes   ', # " used in 2002
                 'Date', # determined_dead_before (if not alive) (also used for Observation.datetime_observed and Observation.datetime_reported)
            'Necropsy?', # necropsy, partial_necropsy
        'Full necropsy', # necropsy, partial_necropsy
        'Full Necropsy', # " used in 2002
     'Partial necropsy', # necropsy, partial_necropsy
     'Partial Necropsy', # " used in 2002
'Carcass Dispossed Y/N', # carcass_disposed
        'Ceta data rec', # document on an animal with type 'Cetacean Data Record'
 'Cetacean Data Record', # " used in 2002
        'Histo results', # document on an animal with type 'Histological Findings'

# case
          'Classification', # case_type
                   'Class', # " used in 2001
               'Re-sight?', # just note in import_notes
  'Resight: Date 1st Seen', # just note in import_notes
"Date 1st Seen:  If there is a '1' in the Resight column indicating this is a whale with prior events, fill in the date of the whale's initial event in this column.", # " used in 2002
        'Event Confirmed?', # valid
'NMFS Database Regional #', # just note in import_notes
                 'Field #', # 2005 column name for 'NMFS Database Regional'
        'NMFS Database # ', # just note in import_notes
                 'NMFS # ', # 2005 column name for 'NMFS Database # '
                  'NMFS #', # 2003 column name for 'NMFS Database # '
   'Additional Identifier', # just note in import_notes
'Entanglement or Collision #', # just note in import_notes
            'CCS web page', # document attached to case with type 'CCS web page'
                'Hi Form?', # document attached to case with type 'Human-Interaction Form'
          'Lg Whale email', # document attached to case with type 'Large Whale email'
         'Stranding Rept?', # document attached to case with type 'Stranding Report (Level-A)'
                 'Level A', # " used in 2002
'Last Sighting Prior to Entanglement (for Entangled whales only)', # happened_after

# observation
                  'Comments', # narrative
                      'Date', # datetime_observed and datetime_reported (just the year)
            'Initial report', # just note in import_notes
'Disentanglement  or Response Agencies', # just note in import_notes
               'Common Name', # taxon
                   'Sp Ver?', # just note in import_notes
                       'Sex', # gender
'      Sex       M=male  F=female  U=unknown', # " used in 2002
'Age (at time of event)  *PRD indicated age by length as presented in field guides ', # age_class
'Age (at time of event)', # age_class (in 2004 data)
'Est. Age (at time of event) - A=adult, S=sub-adult, Y=Yearling, C=calf, U=unknown, NI=not indicated', # " used in 2002
  'Total Length (cm)  *=est', # animal_description
             'Total Length ', # " used in 2002
' Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
'                               Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
'                       Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
'Ashore - Did the whale/carcass ultimately come ashore', # ashore
'Ashore?  0=No,Floater that never landed  1=Yes, came to shore', # " used in 2002
                    'Alive?', # condition
          'Initial condtion', # condition, observation splitting, initial
'InitialCondition     Code 1=Alive, Code 2=Fresh dead, Code 3=Moderate Decomposition, Code 4=Advanced Decomposition, Code 5=Mummified/Skeletal   6=Dead-Condition Unknown', # " used in 2002
             'Exam condtion', # condition, observation splitting, exam
            'Exam Condition', # " used in 2002
              'Photo w/file', # if yes, there's documentation, otherwise unknown
                  'Pictures', # documentation
           'Genetics Sample', # genetic_sample
          'Genetics sampled', # " used in 2002
                      'HI ?', # human_interaction
'      HI?     1=Yes 2=No CBD=Cannot be determined', # " used in 2002
'Indication of Entanglement', # indication_entanglement
'Indication of Ent  anglement', # " used in 2002
 'Indication of Ship Strike', # indication_shipstrike
                 'Phone Log', # document(s) attached to observation with type 'Phone Log entry'. just note for now.
    
# entanglement observations
                              'Gear', # entanglement_details
  'Disentangle status of live whale', # disentanglement_outcome
       'Disent status of live whale', # disentanglement_outcome
                     'Disent status', # " used in 2002
     'Disent attempt on live whale?', # disentanglement_outcome
'Disentangle attempt on live whale?', # disentanglement_outcome
                   'Disent attempt?', # " used in 2002

# location
        'LATITUDE', # coordinates
       'LONGITUDE', # coordinates
        'Location', # coordinates
'Location     *Location*=estimated', # " used in 2002
'General location', # description
        'State/EZ', # state, waters, country
          'Region', # just note in import_notes
))
CLASSIFICATIONS = set((
    'M', # mortality
    'E', # entanglement
    'Injury', # other injury
))

# various length units, in meters
CENTIMETER = Decimal('0.01')
INCH = Decimal('2.54') * CENTIMETER
FOOT = 12 * INCH
def parse_length(length):
    '''\
    Returns a tuple of length in meters and sigdigs of original.
    '''
    
    # trim
    length = length.strip()
    
    m = None
    
    for unit_match, unit_factor in (
        (r'(cm)?', CENTIMETER), # note that this matches no-unit
        (r'(in|")', INCH),
        (r"(ft|')", FOOT),
    ):
        match = re.match(r'(?i)(?P<length>[0-9.]+)\s*' + unit_match + '$', length)
        if match:
            length_string = match.group('length')
            length_decimal = Decimal(length_string)
            m = length_decimal * unit_factor
            break

    if not m:
        raise ValueError("can't figure out length: %s" % length)
    
    (sign, digits, exponent) = length_decimal.as_tuple()
    # is there a decimal?
    if '.' in length_string:
        # count all the digits as significant
        sigdigs = len(digits)
    else:
        # don't count trailing zeros
        sigdigs = len(length_string.strip('0'))
    
    return m, sigdigs

def parse_date(date):
    for format in (
        '%Y/%m/%d',
        '%d-%b-%y',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%d-%b-%y*',
        '%B %d.%Y',
    ):
        try:
            return datetime.datetime.strptime(date, format).date()
        except ValueError:
            pass
    raise ValueError("can't parse datetime %s" % date)

ASHORE_KEYS = (
    ' Ashore?     - Did the whale/carcass ultimately come ashore',
    '                               Ashore?     - Did the whale/carcass ultimately come ashore',
    '                       Ashore?     - Did the whale/carcass ultimately come ashore',
    'Ashore - Did the whale/carcass ultimately come ashore',
    'Ashore?  0=No,Floater that never landed  1=Yes, came to shore',
)
def get_ashore(row):
    # ashore has a couple variations:
    key = None
    for k in ASHORE_KEYS:
        if k in row:
            key = k
            break
    if key is None:
        return None
    
    ashore = row[k]

    return {
        "": None,
        '0-1': None,
        "0": False,
        "1": True,
    }[ashore]

def translate_taxon(data, data_key, row):
    data[data_key] = {
        'BEWH': Taxon.objects.get(tsn=180506), # beaked whales
        'BOWH': Taxon.objects.get(tsn=180533), # bowhead whale
        'BRWH': Taxon.objects.get(tsn=612597), # bryde's whale
        'FIWH': Taxon.objects.get(tsn=180527), # finback
        'Fin': Taxon.objects.get(tsn=180527), # finback
        'HUWH': Taxon.objects.get(tsn=180530), # humpback
        'HUWH?': Taxon.objects.get(tsn=180530), # humpback
        'Humpback': Taxon.objects.get(tsn=180530), # humpback
        'MIWH': Taxon.objects.get(tsn=180524), # minke
        'Minke': Taxon.objects.get(tsn=180524), # minke
        'RIWH': Taxon.objects.get(tsn=180537), # right
        'RIWH?': Taxon.objects.get(tsn=180537), # right
        'Right': Taxon.objects.get(tsn=180537), # right
        'SEWH': Taxon.objects.get(tsn=180526), # sei whale
        'Sei': Taxon.objects.get(tsn=180526), # sei whale
        'SPWH': Taxon.objects.get(tsn=180488), # sperm whale
        'Sperm': Taxon.objects.get(tsn=180488), # sperm whale
        'UNAN': None,                          # unknown animal
        'Unk': None,
        'UNBA': Taxon.objects.get(tsn=552298), # unknown baleen whale
        'UNRW': Taxon.objects.get(tsn=552298), # unknown rorqual
        'UNFS': Taxon.objects.get(tsn=180523), # finback or sei whale
        'FI/SEWH': Taxon.objects.get(tsn=180523), # finback or sei whale
        'FI-SEWH': Taxon.objects.get(tsn=180523), # finback or sei whale
        'FIN/SEI': Taxon.objects.get(tsn=180523), # finback or sei whale
        'Fin/sei': Taxon.objects.get(tsn=180523), # finback or sei whale
        'UNWH': Taxon.objects.get(tsn=180403), # unknown whale
    }[row['Common Name']]

    if row['Common Name'] in set(('UNWH', 'UNRW', 'FI/SEWH', 'RIWH?', 'UNFS')):
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
    
    if 'NMFS Database # ' in row and row['NMFS Database # ']:
        unimportable_column(a, 'NMFS Database # ')
    if 'NMFS # ' in row and row['NMFS # ']:
        unimportable_column(a, 'NMFS # ')
    if 'NMFS Database Regional #' in row and row['NMFS Database Regional #']:
        unimportable_column(a, 'NMFS Database Regional #')
    #if 'Field #' in row and row['Field #']:
    #    unimportable_column(a, 'Field #')
    if 'Additional Identifier' in row and row['Additional Identifier']:
        unimportable_column(a, 'Additional Identifier')
    
    # field_number
    # 2005 has different column names
    if 'Field # (S)' in row and row['Field # (S)']:
        a['field_number'] = row['Field # (S)']
    elif 'Field # ' in row and row['Field # ']:
        a['field_number'] = row['Field # ']
    elif 'Field #' in row and row['Field #']:
        a['field_number'] = row['Field #']
    
    # name
    name_key = None
    for k in ('Individual', 'Indiv.'):
        if k in row and row[k]:
            name_key = k
            break
    if not name_key is None:
        # filter 'unknown'
        if row[name_key] not in set(('U', 'Unknown')):
            a['name'] = row[name_key]
    
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
    alive_key = None
    for kn in (
        'Alive?',
        '    Alive?       Was the animal ever seen alive during this event? 0=No,1=Yes   ',
    ):
        if kn in row:
            alive_key = kn
            break
    if alive_key:
        dead = {
            '': False,
            '?': False,
            '1-0': False,
            '0-1': False,
            '0': True,
            '1': False,
        }[row[alive_key]]
        if dead:
            # a one-off exception
            if row['Date'] == 'unk-Sep07':
                a['determined_dead_before'] = datetime.date(2007, 10, 1)
            elif row['Date'] == '7/1/2003*':
                a['determined_dead_before'] = datetime.date(2003, 7, 1)
                odd_value(a, 'Date')
            else:
                a['determined_dead_before'] = parse_date(row['Date'])
        # the value isn't understood
        if row[alive_key] not in set(('', '0', '1')):
            unknown_value(a, alive_key)
    
    # carcass_disposed
    if 'Carcass Dispossed Y/N' in row:
        a['carcass_disposed'] = {
            '': None,
            'U': None,
            '0': False,
            'N': False,
            '1': True,
            'Y': True,
        }[row['Carcass Dispossed Y/N']]
    
    # partial_necropsy
    # necropsy
    full_necropsy_key = None
    for kn in (
        'Full Necropsy',
        'Full necropsy',
    ):
        if kn in row:
            full_necropsy_key = kn
            break
    if full_necropsy_key is None:
        full_necropsy_key = 'Full Necropsy'
        row['Full Necropsy'] = ''
    partial_necropsy_key = None
    for kn in (
        'Partial Necropsy',
        'Partial necropsy',
    ):
        if kn in row:
            partial_necropsy_key = kn
            break
    if partial_necropsy_key is None:
        partial_necropsy_key = 'Partial Necropsy'
        row['Partial Necropsy'] = ''
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
            'X': None,
      'Pending': None,
            '0': False,
            '1': True,
'Performed by Bob Bonde, no report in file': True,
'yes- but no report': True,
 '0-Kim Durham': False,
        }[row['Necropsy?']],
        {
              '': None,
             '?': None,
             '0': False,
            'na': False,
           'N/A': False,
             '1': True,
        }[row[full_necropsy_key]],
        {
              '': None,
             '0': False,
            'na': False,
           'N/A': False,
             '1': True,
        }[row[partial_necropsy_key]],
    ]
    if not understood:
        unknown_values(a, ('Necropsy?', full_necropsy_key, partial_necropsy_key))
    if row['Necropsy?'] not in set(('', '0', '1')):
        odd_value(a, 'Necropsy?')
    
    # cause_of_death defaults to ''
    
    return a

def parse_case(row):
    
    # animal
    c = {
        'import_notes': {},
    }
    
    # case_type
    class_key = None
    for kn in (
        'Classification',
        'Class',
    ):
        if kn in row:
            class_key = kn
            break
    cls = row[class_key]
    cls, resight = re.subn(r'(?i)\s*\(?(likely )?resight\??\)?', '', cls)
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
    'C (injury)': 'Shipstrike',
             'E': 'Entanglement',
            'E,': 'Entanglement',
      'E  (CAN)': 'Entanglement',
     'E (lures)': 'Entanglement',
 'E (entrapped)': 'Entanglement',
           'C,M': set(('Case', 'Shipstrike')),
           'M,C': set(('Case', 'Shipstrike')),
          'M,SS': set(('Case', 'Shipstrike')),
          'M, C': set(('Case', 'Shipstrike')),
          'C, M': set(('Case', 'Shipstrike')),
         'M, SS': set(('Case', 'Shipstrike')),
         'SS, M': set(('Case', 'Shipstrike')),
           'M,E': set(('Case', 'Entanglement')),
          'M, E': set(('Case', 'Entanglement')),
          'E, M': set(('Case', 'Entanglement')),
           'E,M': set(('Case', 'Entanglement')),
       'E, C, M': set(('Case', 'Shipstrike', 'Entanglement')),
    }[cls]
    if resight or row[class_key] in set((
        '',
        'M ?',
        'M(resight?)',
        'M(Likely resight)',
        'M(Incidental Take)',
        'C (injury)',
        'E  (CAN)',
        'E (lures)',
        'E (entrapped)',
    )):
        odd_value(c, class_key)
    
    c['classification'] = cls
    
    for kn in (
        'Re-sight?',
        'Resight: Date 1st Seen',
        "Date 1st Seen:  If there is a '1' in the Resight column indicating this is a whale with prior events, fill in the date of the whale's initial event in this column.",
    ):
        if kn in row and row[kn]:
            unimportable_column(c, kn)
    
    # valid
    c['valid'] = {
        '': 1,
     '1,0': 1,
       '?': 1,
       '0': 1,
      '0?': 1,
       '1': 2,
    }[row['Event Confirmed?']]
    if c['valid'] in set(('0?',)):
        odd_value(c, 'valid')
    
    # happened_after defaults to None
    last_seen_key = 'Last Sighting Prior to Entanglement (for Entangled whales only)'
    if last_seen_key in row and row[last_seen_key]:
        m = re.search(r'^(?P<date>(August )?[\d/Aug\-.]+)\s*(?P<other>[^\s]+.*)?$', row[last_seen_key])
        if m:
            c['happened_after'] = parse_date(m.group('date'))
            if m.group('other'):
                odd_value(c, last_seen_key)
        else:
            if row[last_seen_key] not in set((
                'Unk',
                'N/A',
                'U',
                'N/A, Previously unknown individual'
            )):
                raise ValueError("can't parse last-sighted field: '%s'" % row[last_seen_key])
    
    # human_interaction
    # choices:
    # ('unk', 'not yet determined'),
    # ('yes', 'yes'),
    # ('no' , 'no'),
    # ('cbd', 'can\'t be determined'),
    hi_key = None
    for kn in (
        'HI ?',
        '      HI?     1=Yes 2=No CBD=Cannot be determined',
    ):
        if kn in row:
            hi_key = kn
            break;
    if not hi_key is None:
        c['human_interaction'] = {
            '': 'unk',
            '?': 'unk',
            'X': 'unk',
            '1/cbd?': 'unk',
            '1?': 'unk',
    'PENDING HISTO': 'unk',
            'No': 'no',
            '0': 'no',
            '1': 'yes',
            'cbd': 'cbd',
            'CBD': 'cbd',
            'CBD`': 'cbd',
        }[row[hi_key]]
        if c['human_interaction'] in set(('1/cbd?', '1?', 'PENDING HISTO', 'X')):
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
    state_input = row['State/EZ'].lower() if 'State/EZ' in row else ''
    if state_input == '':
        country = None
        eez = None
        state = None
    elif state_input in (('ez',)):
        country = Country.objects.get(iso='US')
        eez = True
        state = None
    elif state_input in (('ber', 'can', 'cn', 'dr',)):
        country = Country.objects.get(iso={
            'ber': 'BM',
            'can': 'CA',
            'cn':  'CA',
            'dr':  'DO',
        }[state_input])
        eez = None
        state = None
    elif state_input in STATES_NORMALIZED.keys():
        country = Country.objects.get(iso='US')
        eez = False
        state = STATES_NORMALIZED[state_input]
    # one-off errors
    elif state_input in set(('ma eez',)):
        unknown_value(observation_data, 'State/EZ')
        country = None
        eez = None
        state = None
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
    for kn in (
        'Location',
        'Location     *Location*=estimated',
    ):
        if kn in row and row[kn]:
            # split 'Location' into a lat and long
            number = r'[\d.+\-]+[^\s]*'
            for regex in (
                r'^(?P<lat>' + number + '[^\d.+\-]*)(?P<lon>' + number + '[^\d.+\-]*)$',
                r'^(?P<lat>' + '\s+'.join([number] * 2) + '[^\d.+\-]*)(?P<lon>' + '\s+'.join([number] * 1) + '[^\d.+\-]*)$',
                r'^(?P<lat>' + '\s+'.join([number] * 2) + '[^\d.+\-]*)(?P<lon>' + '\s+'.join([number] * 2) + '[^\d.+\-]*)$',
                r'^(?P<lat>' + '\s+'.join([number] * 3) + '[^\d.+\-]*)(?P<lon>' + '\s+'.join([number] * 3) + '[^\d.+\-]*)$',
            ):
                m = re.search(regex, row[kn])
                if m:
                    if 'LATITUDE' not in row or not row['LATITUDE']:
                        row['LATITUDE'] = m.group('lat')
                    if 'LONGITUDE' not in row or not row['LONGITUDE']:
                        row['LONGITUDE'] = m.group('lon')
                    break
            if not m:
                if row[kn] in set((
                    '44 17 49    66 26 43 (7/10/03 sighting)',
                    'est: 4405.532  6837.161',
                    '*4128.52   7116.27*',
                )):
                    unknown_value(observation_data, kn)
                elif row[kn] not in set(('?', 'unknown', '??', 'None')):
                    raise ValueError("can't parse Location: '%s'" % row[kn])
    
    lat = None
    lon = None
    if 'LATITUDE' in row and row['LATITUDE']:
        try:
            lat = NiceLocationForm._clean_coordinate(row['LATITUDE'], is_lat=True)
            lat = dms_to_dec(lat)
        except ValidationError:
            unknown_value(observation_data, 'LATITUDE')
    if 'LONGITUDE' in row and row['LONGITUDE']:
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
    
    if 'Region' in row and row['Region']:
        unimportable_column(observation_data, 'Region')
    
    return l

def parse_observation(row, case_data):
    
    o = {
        'import_notes': {},
    }
    
    # animal
    #o['animal'] = case_data['animal']
    
    # cases
    #o['cases'] = case_data['id']
    
    # narrative
    if row['Comments']:
        o['narrative'] = row['Comments']
    
    # observer defaults to None
    if row['Initial report']:
        unimportable_column(o, 'Initial report')
    if 'Disentanglement  or Response Agencies' in row and row['Disentanglement  or Response Agencies']:
        unimportable_column(o, 'Disentanglement  or Response Agencies')

    # datetime_observed
    if not row['Date']:
        unimportable_value(o, 'Date')
    # a one-off exception
    if row['Date'] == 'unk-Sep07':
        uncertain_datetime = UncertainDateTime(2007, 9)
    elif row['Date'] == '7/1/2003*':
        uncertain_datetime = UncertainDateTime(2003, 7, 1)
        odd_value(o, 'Date')
    else:
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
    length_key = None
    for kn in (
        'Total Length ',
        'Total Length (cm)  *=est',
    ):
        if kn in row:
            length_key = kn
            break;
    if not length_key is None:
        if row[length_key] not in set(('', 'U')):
            try:
                length, sigdigs = parse_length(row[length_key])
                o['animal_length'] = length
                o['animal_length_sigdigs'] = sigdigs
            except ValueError:
                unimportable_value(o, length_key)

    # age_class
    age_keys = (
        'Age (at time of event)  *PRD indicated age by length as presented in field guides ',
        'Age (at time of event)',
        'Est. Age (at time of event) - A=adult, S=sub-adult, Y=Yearling, C=calf, U=unknown, NI=not indicated',
    )
    for age_key in age_keys:
        if age_key in row:
            o['age_class'] = {
                '': '',
               '?': '',
    'Born in 2001': '',
         '6 tons*': '',
               'Y': '',
              'Y*': '',
               'U': '',
            'Unk.': '',
     'U-Aknowlton': '',
'First id in 1992': '',
               'M': '',
               'X': '',
               'C': 'ca',
            'Calf': 'ca',
               'J': 'ju',
              'SA': 'ju',
               'S': 'ju',
              'S*': 'ju',
        'Subadult': 'ju',
               'A': 'ad',
              'A*': 'ad',
            }[row[age_key]]
            if row[age_key] in set(('S*','A*', 'U-Aknowlton',)):
                odd_value(o, age_key)
            if row[age_key] in set(('Y', 'Y*', 'S', 'M', 'First id in 1992', '6 tons*', 'Born in 2001', 'X')):
                unknown_value(o, age_key)
            break
    
    # gender
    sex_key = None
    for kn in (
        '      Sex       M=male  F=female  U=unknown',
        'Sex',
    ):
        if kn in row:
            sex_key = kn
            break;
    if not sex_key is None:
        o['gender'] = {
            '': '',
            '0': '',
            '4': '',
            'U': '',
            'U-Aknowlton': '',
            'X': '',
            '?': '',
            'CBD': '',
            'm': 'm',
            'M': 'm',
            'f': 'f',
            'F': 'f',
        }[row[sex_key]]
        if row[sex_key] in set(('CBD', 'U-Aknowlton')):
            odd_value(o, sex_key)
        if row[sex_key] in set(('4', 'X', '0')):
            unknown_value(o, sex_key)
    
    # animal_description defaults to ''
    
    # ashore
    o['ashore'] = get_ashore(row)

    # initial
    # exam
    # condition
    #        (0, 'unknown'),
    #        (1, 'alive'),
    #        (6, 'dead, carcass condition unknown'),
    #        (2, 'fresh dead'),
    #        (3, 'moderate decomposition'),
    #        (4, 'advanced decomposition'),
    #        (5, 'skeletal'),
    alive_key = None
    for kn in (
        'Alive?',
        '    Alive?       Was the animal ever seen alive during this event? 0=No,1=Yes   ',
    ):
        if kn in row:
            alive_key = kn
            break
    initial_key = None
    for kn in (
        'Initial condtion',
        'InitialCondition     Code 1=Alive, Code 2=Fresh dead, Code 3=Moderate Decomposition, Code 4=Advanced Decomposition, Code 5=Mummified/Skeletal   6=Dead-Condition Unknown',
    ):
        if kn in row:
            initial_key = kn
            break
    exam_key = None
    for kn in (
        'Exam condtion',
        'Exam Condition',
    ):
        if kn in row:
            exam_key = kn
            break
    conditions = {
         '': 0,
        '?': 0,
        'X': 0,
        '0': 0,
        'U': 0,
       'na': 0,
       'NE': 0,
        '1': 1,
      '1/2': 2,
        '2': 2,
        '3': 3,
       '3+': 3,
   '3 or 4': 3,
   '3 to 4': 3,
        '4': 4,
       '4?': 4,
       '4+': 4,
       '~4': 4,
        '5': 5,
        '6': 6,
    }
    if not initial_key is None:
        o['initial_condition'] = conditions[row[initial_key]]
    else:
        o['initial_condition'] = 0
    if not exam_key is None:
        o['exam_condition'] = conditions[row[exam_key]]
    else:
        o['exam_condition'] = 0
    o['alive_condition'] = {
        '': 0,
        '?': 0,
        '1-0': 0,
        '0-1': 0,
        '0': 6,
        '1': 1,
    }[row[alive_key]]
    if row[alive_key] not in set(('', '0', '1')):
        odd_value(o, alive_key)
    if o['initial_condition'] == 0 and o['alive_condition'] != 0:
        o['initial_condition'] = o['alive_condition']
    if o['exam_condition'] == 0 and o['alive_condition'] != 0:
        o['exam_condition'] = o['alive_condition']
    o['split'] = False
    o['condition'] = o['initial_condition']
    if o['initial_condition'] != o['exam_condition'] and o['exam_condition'] != 0:
        o['split'] = True
    condition_expected = set(('', '1', '2', '3', '4', '5', '6'))
    for model_key, row_key in (
        ('initial', initial_key),
        ('exam',    exam_key),
    ):
        o[model_key] = bool(o[model_key + '_condition'])
        if not row_key is None:
            if row[row_key] not in condition_expected:
                odd_value(o, row_key)
    
    # wounded defaults to None
    
    # wound_description defaults to ''
    
    # documentation
    # if 'Pictures' starts with 'yes' or 'no', strip out the rest
    pictures = row['Pictures']
    # don't forget 'match' only matches at the beginning of the string
    yesno_match = re.match(r'(yes|no)\s*[^\s]+', row['Pictures'], re.I)
    if yesno_match:
        pictures = yesno_match.group(1)
        odd_value(o, 'Pictures')
    o['documentation'] = {
        (None,  None ): None,
        (None,  False): None,
        (None,  True ): True,
        (False, None ): False,
        (False, False): False,
        (False, True): None,
        (True,  None ): True,
        (True,  True ): True,
        (True,  False): True,
    }[
        {
            '': None,
            '?': None,
            'Unk': None,
            'Unknown': None,
            'Maybe, WW Vessel, but NOAA never received.  Photos with file are from a separate 8/11 sighting of Sickle': None,
            'Uncertain - Canadian CG, Fundy Voyager.': None,
            'Unknown - perhaps w/ S. Dufault': None,
            'Unknown- DFO?': None,
            'No': False,
            'NO': False,
            'Yes': True,
            'yes': True,
            '1': True,
            'video': True,
            'Video -NMFS': True,
            'Video, USCG': True,
            'pending': True,
            'Pending': True,
            'Pending -from Navy': True,
            'Gear only': True,
            'Video- Grisel Rodrigues': True,
            'CCSN': True,
        }[pictures],
        {
             '': None,
            '?': None,
            'X': None,
           'PG': None,
            '0': False,
            '1': True,
        }[row['Photo w/file']],
    ]
    if row['Pictures'] not in set(('', 'No', 'NO', 'Yes', 'yes', '1')):
        odd_value(o, 'Pictures')
    if row['Photo w/file'] not in set(('', '0', '1')):
        odd_value(o, 'Photo w/file')

    # tagged deafults to None
    # biopsy defaults to None
    
    # genetic_sample
    genetic_key = None
    for kn in (
        'Genetics Sample',
        'Genetics sampled',
    ):
        if kn in row:
            genetic_key = kn
            break
    if not genetic_key is None:
        o['genetic_sample'] = {
            "": None,
            "0": False,
            "1": True,
        }[row[genetic_key]]
    
    # indication_entanglement
    indication_entanglement_key = None
    for kn in (
        'Indication of Entanglement',
        'Indication of Ent  anglement',
    ):
        if kn in row:
            indication_entanglement_key = kn
            break
    if not indication_entanglement_key is None:
        o['indication_entanglement'] = {
            '': None,
            '1?': None,
            '0': False,
            '1': True,
        }[row[indication_entanglement_key]]
        if row[indication_entanglement_key] in set(('1?',)):
            unknown_value(o, indication_entanglement_key)
    
    # indication_shipstrike
    if 'Indication of Ship Strike' in row:
        o['indication_shipstrike'] = {
            '': None,
            '0': False,
            '1': True,
            '1*': True,
        }[row['Indication of Ship Strike']]
        if not row['Indication of Ship Strike'] in set(('', '0', '1')):
            odd_value(o, 'Indication of Ship Strike')
    
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
        
        disent_attempt_key = None
        for k in (
            'Disentangle attempt on live whale?',
            'Disent attempt on live whale?',
            'Disent attempt?',
        ):
            if k in row:
                disent_attempt_key = k
                break
        disent_status_key = None
        for k in (
            'Disentangle status of live whale',
            'Disent status of live whale',
            'Disent status',
        ):
            if k in row:
                disent_status_key = k
                break
        # disentanglement_outcome
        attempt = {
               '': None,
              '.': None,
            'N/A': None,
'Document and tag if possible': None,
          '1-F/V': None,
              '0': False,
             'no': False,
             'No': False,
              '1': True,
            'Yes': True,
        }[row[disent_attempt_key]]
        if row[disent_attempt_key] in set((
            '.',
            'Document and tag if possible',
        )):
            unknown_value(o, disent_attempt_key)
        outcome = {
            '': 'unknown',
            '?': 'unknown',
            'N/A': 'unknown',
            'Animal releases': 'unknown',
            'Carrying gear': 'gear',
            'disentangled': 'no gear',
            'Disentangled': 'no gear',
            '"Disentangled"': 'no gear',
            'Disentangled (presumed)': 'no gear',
            'Completely disentangled': 'no gear',
            'fully disentangled': 'no gear',
            'disentangled by bystander': 'no gear',
            'Entangled': 'entangled',
            'entangled': 'entangled',
            'Entangled, needs full assessment': 'entangled, needs assesment',
            'Entangled -suspect but cannot confirm that gear shed': 'entangled, suspected shed',
            'Presumed Entangled': 'entangled',
            'Unsuccessful': 'unsuccessful',
            'Gear free': 'no gear',
            'Gear shed': 'gear shed',
            'Potentially gear free': 'unknown',
            'Minor': 'unknown',
            'No attempt made': 'unknown',
            'NOAA, GA': 'unknown',
            'Partial Disentanglement': 'partly entangled',
            'partial disentanglement': 'partly entangled',
            'Partial disentanglement': 'partly entangled',
            'Disentangled from most gear': 'partly entangled',
            'some line still embedded in dorsal peduncle': 'some gear',
            'unable to relocate': 'unknown',
            'Unable to relocate': 'unknown',
            'Animal could not be relocated': 'unknown',
            'Unknown': 'unknown',
            'unknown': 'unknown',
            'Unknown/unconfirmed': 'unknown',
            'Lost/Unidentifiable': 'unknown',
            'Freed by fisherman': 'no gear by fisherman',
            'Animal freed itself': 'gear shed',
            'Presumed Entangled - Gear shed': 'unknown',
        }[row[disent_status_key]]
        if row[disent_status_key] in set((
            '?',
            'Carrying gear',
            'some line still embedded in dorsal peduncle',
            'disentangled by bystander',
            'Disentangled (presumed)',
        )):
            odd_value(o, disent_status_key)
        if row[disent_status_key] in set((
            'Minor',
            'No attempt made',
            'NOAA, GA',
            'unable to relocate',
            'Unable to relocate',
            'Animal could not be relocated',
            'Potentially gear free',
            'Animal releases',
            'Lost/Unidentifiable',
        )):
            unknown_value(o, disent_status_key)
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
            (False, 'no gear by fisherman'): ('', False),
            (False, 'entangled'): ('entg', True),
            (False, 'entangled, needs assesment'): ('entg', False),
            (False, 'gear shed'): ('shed', True),

            (True, 'entangled'): ('entg', True),
            (True, 'entangled, needs assesment'): ('entg', False),
            (True, 'entangled, suspected shed'): ('entg', False),
            (True, 'unsuccessful'): ('entg', True),
            (True, 'partly entangled'): ('part', True),
            (True, 'some gear'): ('', False),
            (True, 'gear shed'): ('', False),
            (True, 'no gear'): ('cmpl', True),
            (True, 'unknown'): ('', False),
        }[(attempt, outcome)]
        if not understood:
            unknown_values(o, (disent_attempt_key, disent_status_key))

        o['observation_extensions']['entanglement_observation'] = eo

    ## ShipstrikeObservation
    # striking_vessel defaults to None
    if case_data['__class__'] == 'Shipstrike' or isinstance(case_data['__class__'], set) and 'Shipstrike' in case_data['__class__']:
        o['observation_extensions']['shipstrike_observation'] = {}
    
    return o

def parse_documents(row, animal_data, case_data):
    
    docs = []
    
    for doc_keys, attach_to, data, doctype_name in (
        (('Ceta data rec', 'Cetacean Data Record'), 'animal', animal_data, 'Cetacean Data Record'),
        (('Histo results',), 'animal', animal_data, 'Histological Findings'),
        (('CCS web page',), 'case', case_data, 'CCS web page'),
        (('Hi Form?',), 'case', case_data, 'Human-Interaction Form'),
        (('Lg Whale email',), 'case', case_data, 'Large Whale email'),
        (('Stranding Rept?', 'Level A'), 'case', case_data, 'Stranding Report (Level-A)'),
    ):
        for doc_key in doc_keys:
            if doc_key in row and row[doc_key]:
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

def parse_csv(csv_file):
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
        
        new = {}
        
        a = parse_animal(row)
        new['animal'] = a
        
        c = parse_case(row)
        new['case'] = c
        
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
        esc(datetime.datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %z')),
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

        if len(observations) != 2:
            raise ValueError("Observation data has 'split' but is missing 'exam' and 'initial'!")
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

