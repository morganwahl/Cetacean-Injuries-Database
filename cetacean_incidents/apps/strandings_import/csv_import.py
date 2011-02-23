import operator
from itertools import imap, count
from datetime import datetime
import re
import csv

from django.db import transaction
from django.forms import ValidationError

from reversion import revision

from cetacean_incidents.apps.countries.models import Country
from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.locations.forms import NiceLocationForm
from cetacean_incidents.apps.locations.utils import dms_to_dec
from cetacean_incidents.apps.taxons.models import Taxon
from cetacean_incidents.apps.incidents.models import Animal

class UnrecognizedFieldError(ValueError):
    
    # require a column name
    def __init__(self, column_name, *args, **kwargs):
        super(UnrecognizedFieldError, self).__init__(u'"%s"' % column_name, *args, **kwargs)

FIELDNAMES = set((
    # animal
    'Field # ',   # field_number
    'NMFS Database Regional #',
    'NMFS Database # ',
    'Individual', # name
    'Necropsy?', # necropsy, partial_necropsy
    'Full necropsy', # necropsy, partial_necropsy
    'Partial necropsy', # necropsy, partial_necropsy

    # case
    'Classification',
    'Re-sight?',
    # TODO look up existing case
    'Resight: Date 1st Seen',
    'Event Confirmed?',

    # observation
    'Comments', # narrative
    'Date',     # date observed
    'Initial report', # observer
    'Common Name', # taxon
    'Sp Ver?',
    'Sex', # gender
    'Age (at time of event)  *PRD indicated age by length as presented in field guides ', # age_class
    'Total Length (cm)  *=est', # animal_description
    ' Ashore?     - Did the whale/carcass ultimately come ashore', # ashore
    'Alive?', # condition
    'Pictures', # documentation
    'Genetics Sample', # genetic_sample
    'Indication of Entanglement', # indication_entanglement
    'Indication of Ship Strike', # indication_shipstrike
    
    # entanglement observations
    'Gear', # entanglement_details
    'Disentangle status of live whale', # disentanglement_outcome
    'Disentangle attempt on live whale?', # disentanglement_outcome

    # location
    'LATITUDE',  # coordinates
    'LONGITUDE', # coordinates
    'General location', # description
    'State/EZ',  # state, waters, country
    
    # documents
    'Lg Whale email',
    'CCS web page',
    'Phone Log',
    'Hi Form?',
    'Histo results',
    'Stranding Rept?',
    
    # unknown
    'Photo w/file',
    'Ceta data rec',
))
CLASSIFICATIONS = set((
    'M', # mortality
    'E', # entanglement
    'Injury', # other injury
))

def parse_date(date):
    for format in ('%Y/%m/%d', '%d-%b-%y', '%m/%d/%Y'):
        try:
            return datetime.strptime(date, format).date()
        except ValueError:
            pass
    raise ValueError("can't parse datetime %s" % date)

def translate_taxon(abbr):
    taxon = None

    taxon = {
        'BEWH': Taxon.objects.get(tsn=180506), # beaked whales
        'FIWH': Taxon.objects.get(tsn=180527), # finback
        'HUWH': Taxon.objects.get(tsn=180530), # humpback
        'MIWH': Taxon.objects.get(tsn=180524), # minke
        'RIWH': Taxon.objects.get(tsn=180537), # right
        'SEWH': Taxon.objects.get(tsn=180526), # sei whale
        'SPWH': Taxon.objects.get(tsn=180488), # sperm whale
        'UNAN': None,                          # unknown animal
        'UNBA': Taxon.objects.get(tsn=552298), # unknown baleen whale
        'UNRW': Taxon.objects.get(tsn=552298), # unknown rorqual
        'FI/SEWH': Taxon.objects.get(tsn=180523), # finback or sei whale
        'UNWH': Taxon.objects.get(tsn=180403), # unknown whale
    }[abbr]

    notes = None
    if abbr in set(('UNWH', 'UNRW', 'FI/SEWH')):
        notes = u"originally marked as taxon set \"%s\"\n" % abbr
    
    return taxon, notes

def parse_animal(row, temp_id):
    
    a = {
        'id': temp_id.next(),
        'import_notes': u"",
    }
    if row['NMFS Database Regional #']:
        a['import_notes'] += u"from a stranding entry with 'NMFS Database Regional #': %s" % row['NMFS Database Regional #']
    if row['NMFS Database # ']:
        a['import_notes'] += u"from a stranding entry with 'NMFS Database # ': %s" % row['NMFS Database # ']
    
    # field_number
    if row['Field # ']:
        a['field_number'] = row['Field # ']
    
    # name
    if row['Individual']:
        a['name'] = row['Individual']
    
    # determined_taxon
    if row['Sp Ver?'] in set('1'):
        taxon, notes = translate_taxon(row['Common Name'])
        a['determined_taxon'] = taxon
        if notes:
            a['import_notes'] += notes
    elif row['Sp Ver?'] not in set(('', '0')):
        print "Warning: unrecognized value for 'Sp Ver?': %s" % row['Sp Ver?']
    
    # TODO determined_gender

    # determined_dead_before
    dead = {
        '': False,
        '0': True,
        '?': False,
        '1': False,
    }[row['Alive?']]
    if dead:
        a['determined_dead_before'] = parse_date(row['Date'])
    if row['Alive?'] not in set(('', '0', '1')):
        a['import_notes'] += u"imported from stranding entry with 'Alive?' field as: %s\n" % row['Alive?']
    
    # partial_necropsy
    # necropsy
    a['necropsy'], a['partial_necropsy'] = {
        ('',  '',  '' ): (False, False),
        ('0', '',  '' ): (False, False),
        ('0', '0', '0'): (False, False),
        ('0', '0', '1'): (False, False),
        ('1', '',  '' ): (False, False),
        ('1', '1', '' ): (True,  False),
        ('1', '',  '1'): (False, True ),
        ('',  '1', '' ): (True,  False),
    }[row['Necropsy?'], row['Full necropsy'], row['Partial necropsy']]
    
    # TODO cause_of_death
    
    return a

def parse_case(row, temp_id, animal_data):
    
    # animal
    c = {
        'id': temp_id.next(),
        'animal': animal_data['id'],
        'import_notes': '',
    }
    
    # case_type
    if row['Classification']:
        cls = row['Classification']
        m = re.match(r'(?P<cls>.*)\s*\(Resight\)$', cls, re.I)
        resight = False
        if m:
            resight = True
            cls = m.group('cls')
        if resight and row['Re-sight?'] != '1':
            print u"""Warning: resight class but 'Re-sight?' is not '1': %s""" % row
        
        if resight:
            orig_date = row['Resight: Date 1st Seen']
            if orig_date:
                c['import_notes'] += u"date first seen: %s" % orig_date
            else:
                print u"""Warning: resight with no 'date 1st seen': %s""" % row
        
        c['__class__'] = {
            'Injury': 'Case',
                 'M': 'Case',
              'M,SS': ('Case', 'Shipstrike'),
             'M, SS': ('Case', 'Shipstrike'),
                 'E': 'Entanglement',
               'M,E': ('Case', 'Entanglement'),
        }[cls]
        
        c['class'] = cls
    
    # valid
    c['valid'] = {
        '': 1,
        '0': 1,
        '1': 2,
    }[row['Event Confirmed?']]
    
    # TODO happened_after
    # TODO ole_investigation

    ## TODO Entanglement
    # TODO gear_fieldnumber
    # TODO gear_retrieved
    # TODO gear_analyzed
    # TODO analyzed_date
    # TODO analyzed_by
    # TODO gear_types
    # TODO gear_owner_info
    
    return c

def parse_location(row, temp_id, ashore=None):

    l = {
        'id': temp_id.next(),
        'import_notes': '',
    }
    
    # description
    if row['General location']:
        l['description'] = row['General location']
    
    # country
    if row['State/EZ']:
        l['country'] = Country.objects.get(iso='US')

    # waters
    l['waters'] = 0
    if row['State/EZ']:
        if row['State/EZ'] == 'EZ':
            l['waters'] = 3
        else:
            l['waters'] = {
                None: 0,
                True: 1,
                False: 2,
            }[ashore]
    
    # state
    if row['State/EZ']:
        if not row['State/EZ'] == 'EZ':
            l['state'] = row['State/EZ']
    
    # coordinates
    if row['LATITUDE']:
        try:
            lat = NiceLocationForm._clean_coordinate(row['LATITUDE'], is_lat=True)
            lat = dms_to_dec(lat)
            l['lat'] = lat
        except ValidationError as e:
            l['import_notes'] += u"""Couldn't parse coordinate: "%s"\n""" % row['LATITUDE']
    if row['LONGITUDE']:
        try:
            lon = NiceLocationForm._clean_coordinate(row['LONGITUDE'], is_lat=False)
            # assume west
            lon = - dms_to_dec(lon)
            l['lon'] = lon
        except ValidationError:
            l['import_notes'] += u"""Couldn't parse coordinate: "%s"\n""" % row['LONGITUDE']
    if ('lat' in l) != ('lon' in l):
            l['import_notes'] += u"""got one coordinate but not the other: "%s", "%s"\n""" % (row['LATITUDE'], row['LONGITUDE'])
    if ('lat' in l) and ('lon' in l):
        l['coordinates'] = "%s,%s" % (l['lat'], l['lon'])
    
    return l

def parse_observation(row, temp_id, case_data, location_data):
    
    o = {
        'id': temp_id.next(),
        'import_notes': '',
    }
    
    # animal
    o['animal'] = case_data['animal']
    
    # cases
    o['cases'] = [case_data['id']]
    
    # TODO initial
    # TODO exam
    
    # narrative
    if row['Comments']:
        o['narrative'] = row['Comments']
    
    # TODO observer
    if row['Initial report']:
        o['import_notes'] += "the 'Initial report' field had: %s\n" % row['Initial report']

    # datetime_observed
    if row['Date']:
        d = parse_date(row['Date'])
        udt = UncertainDateTime(d.year, d.month, d.day)
        o['datetime_observed'] = udt.to_unicode()
    
    # location
    o['location'] = location_data['id']
    
    # TODO observer_vessel
    # TODO reporter
    # TODO datetime_reported
    
    # taxon
    taxon, notes = translate_taxon(row['Common Name'])
    o['taxon'] = taxon
    if notes:
        o['import_notes'] += notes

    if row['Sp Ver?']:
        o['import_notes'] += u"the \'Sp Ver?\' field had: %s\n" % row['Sp Ver?']

    # age_class
    o['age_class'] = {
        '': '',
        'U': '',
        'C': 'ca',
        'SA': 'ju',
        'A': 'ad',
    }[row['Age (at time of event)  *PRD indicated age by length as presented in field guides ']]
    
    # gender
    o['gender'] = {
        '': '',
        'U': '',
        'M': 'm',
        'F': 'f',
    }[row['Sex']]
    
    # animal_description
    if row['Total Length (cm)  *=est']:
        length = row['Total Length (cm)  *=est']
        if not re.match(r'\s*[\d\.]+\s*\*?\s*$', length):
            print "unparseable value for 'Total Length (cm)  *=est': %s" % length
        o['animal_description'] = u"Total Length (cm)  *=est: %s" % length
    
    # ashore
    o['ashore'] = {
        "": None,
        "0": False,
        "1": True,
    }[row[' Ashore?     - Did the whale/carcass ultimately come ashore']]
    
    # condition
    o['condition'] = {
        '': 0,
        '?': 0,
        '0': 6,
        '1': 1,
    }[row['Alive?']]
    
    # TODO wounded
    # TODO wound_description
    
    # documentation
    o['documentation'] = {
        '': None,
        'No': None,
        'Yes': True,
    }[row['Pictures']]

    # TODO tagged
    # TODO biopsy
    
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
    if case_data['__class__'] == 'Entanglement':
        eo = {}
        
        # TODO anchored
        # TODO gear_description
        # TODO gear_body_location
        # TODO entanglement_details
        if row['Gear']:
            eo['entanglement_details'] = row['Gear']
        # TODO gear_retrieved
        # disentanglement_outcome
        attempt = row['Disentangle attempt on live whale?']
        outcome = row['Disentangle status of live whale']
        eo['disentanglement_outcome'] = {
        # disentanglement_outcome choices:
        #choices= (
        #    ('entg', 'entangled'),
        #    ('shed', 'gear shed'),
        #    ('part', 'partial'),
        #    ('cmpl', 'complete'),
        #    ('mntr', 'monitor'),
        #),
            ('',  ''            ): ''    ,
            ('',  'disentangled'): 'cmpl',
            ('',  'gear free'   ): 'shed',
            ('',  'entangled'   ): 'entg',
            ('0', 'entangled'   ): 'entg',
            ('0', 'gear free'   ): 'shed',
            ('1', 'entangled'   ): 'entg',
        }[(attempt, outcome)]
        o['observation_extensions']['entanglement_observation'] = eo
    
    ## TODO ShipstrikeObservation
    # TODO striking_vessel
    
    return o

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
        non_empty = False
        for k in row.keys():
            if row[k] is None:
                row[k] = ''
            row[k] = row[k].strip()
            if row[k] != '':
                non_empty = True
                if k not in FIELDNAMES:
                    #raise UnrecognizedFieldError("%s:%s" % (k, row[k]))
                    print u"""Warning: unrecognized field "%s": "%s\"""" % (k, row[k])
        if not non_empty:
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
        
        row_results.append({'row_num': i, 'row': row, 'new': new, 'changed': changed})
        
        if i + 1 == 27:
            break
    
    return tuple(row_results)

