import base64
import bz2
from datetime import datetime

from django.conf import settings
from django.core.paginator import (
    Paginator,
    InvalidPage,
    EmptyPage,
)
from django.core.urlresolvers import reverse
from django.db.models import (
    Q,
    Min,
)
from django import forms as django_forms
from django.forms import Media
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import (
    render_to_response,
    redirect,
)
from django.template import (
    Context,
    RequestContext,
)
from django.views.decorators.http import condition
from django.utils.datastructures import SortedDict
from django.utils.http import urlencode

from django.contrib.auth.decorators import login_required

from cetacean_incidents.decorators import (
    permission_required,
    global_etag,
)
from cetacean_incidents import generic_views

from cetacean_incidents.forms import PagingForm

from cetacean_incidents.apps.csv_export import UnicodeDictWriter

from cetacean_incidents.apps.entanglements.models import (
    Entanglement,
    EntanglementObservation,
)

from cetacean_incidents.apps.jquery_ui.tabs import Tabs

from cetacean_incidents.apps.locations.models import Location

from cetacean_incidents.apps.reports.forms import (
    StringReportForm,
    FileReportForm,
)
from cetacean_incidents.apps.reports.models import (
    Report,
    StringReport,
    FileReport,
)

from cetacean_incidents.apps.shipstrikes.models import (
    Shipstrike,
    ShipstrikeObservation,
    StrikingVesselInfo,
)

from cetacean_incidents.apps.taxons.models import Taxon

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField

from cetacean_incidents.apps.vessels.models import VesselInfo

from ..models import (
    Animal,
    Case,
    Observation,
    YearCaseNumber,
)
from ..forms import (
    AnimalForm,
    CaseAnimalForm,
    CaseCSVForm,
    CaseForm,
    CaseMergeForm,
    CaseMergeSourceForm,
    CaseSearchForm,
    CaseSelectionForm,
    ChangeCaseReportForm,
    UseCaseReportForm,
)
from ..templatetags.case_extras import YearsForm

from tabs import (
    AnimalTab,
    CaseTab,
)

@login_required
def case_detail(request, case_id, extra_context={}):
    # TODO this is quite inefficient
    case = Case.objects.get(id=case_id)
    case_class = case.specific_class()
    
    # TODO hack
    if case.case_type == 'Entanglement':
        return redirect(case.specific_instance())
    
    # the case_detail.html template needs jQuery
    if not 'media' in extra_context:
        extra_context['media'] = Media(js=(settings.JQUERY_FILE,))

    if request.user.has_perms(('incidents.change_case', 'incidents.delete_case')):
        merge_form = CaseMergeSourceForm(destination=case)
        extra_context['merge_form'] = merge_form
        extra_context['media'] += merge_form.media
        extra_context['media'] += Media(js=(settings.JQUERY_FILE,))

    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= case_class.objects.select_related().all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
def cases_by_year(request, year=None):
    # handle the year in a GET arg:
    yf = YearsForm(request.GET)
    if yf.is_valid():
        year = yf.cleaned_data['year']
        return redirect(reverse('cases_by_year', args=[year]), permanent=True)
    
    if year is None:
        year = datetime.now().year
    year = int(year)
    cases = Case.objects.filter(observation__datetime_observed__startswith=u"%04d" % year).order_by('date', 'current_yearnumber__year', 'current_yearnumber__number', 'pk')
    # Oracle doesn't support distinct, so this is a work-around
    case_list = []
    case_set = set()
    for c in cases:
        if not c in case_set:
            case_list.append(c)
        case_set.add(c)
    cases = case_list
    return render_to_response(
        "incidents/cases_by_year.html",
        {
            'year': year,
            'cases': cases,
        },
        context_instance= RequestContext(request),
    )

@login_required
@condition(etag_func=global_etag)
def case_search(
    request,
    searchform_class=CaseSearchForm,
    searchform_kwargs={},
    template=u'incidents/case_search.html',
):
    
    # use a SortedDict to ensure 'paging' comes last
    form_classes = SortedDict([
        ('case', searchform_class),
        ('paging', PagingForm),
    ])
    forms = SortedDict()
    for name, cls in form_classes.items():
        form_kwargs = {
            'prefix': name
        }
        if request.GET:
            form_kwargs['data'] = request.GET
        if name == 'case':
            form_kwargs.update(searchform_kwargs)
        forms[name] = cls(**form_kwargs)
    
    case_list = tuple()
    case_qs = None
    
    search_done = False
    if forms['case'].is_bound:
        if forms['case'].is_valid():
            case_qs = forms['case'].results()
            # QuerySet.distinct() won't remove duplicate cases because of the
            # joins happening behind the scenes.
            
            # Simultaneously ordering by the earliest datetime_observed of a
            # case and removing duplicates is hard!
            seen_ids = []
            seen_cases = []
            for c in case_qs:
                if not c.id in seen_ids:
                    seen_ids.append(c.id)
                    seen_cases.append(c)
            case_list = seen_cases
            # UseCaseReportForm expects a QuerySet, so create a new one with
            # no dupes.
            case_qs = Case.objects.filter(id__in=seen_ids)
            
            search_done = True
    
    pressed = request.GET.get('pressed', None)

    if pressed == 'use_report_button':
        use_report_form = UseCaseReportForm(case_qs, case_list, prefix='use_report', data=request.GET)
        if use_report_form.is_valid():
            report = use_report_form.cleaned_data['report'].specific_instance()
            rendered = report.render({
                'cases': use_report_form.cleaned_data['cases'],
            })
            return HttpResponse(rendered, mimetype=report.format)
    else:
        use_report_form = UseCaseReportForm(case_qs, case_list, prefix='use_report')
    
    if request.user.has_perm('entanglements.view_gearowner'):
        if pressed == 'csv_button':
            csv_form = CaseCSVForm(case_qs, case_list, prefix='csv', data=request.GET)
            if csv_form.is_valid():
                return _case_dump_response(case_list)
        else:
            csv_form = CaseCSVForm(case_qs, case_list, prefix='csv')
    else:
        csv_form = None
    
    if pressed == 'change_report_button':
        change_report_form = ChangeCaseReportForm(prefix='change_report', data=request.GET)
        if change_report_form.is_valid():
            if not change_report_form.cleaned_data['report']:
                response_url = reverse(
                    'case_report_create',
                    kwargs= {
                        'report_type': change_report_form.cleaned_data['report_type']
                    },
                )
            else:
                report = change_report_form.cleaned_data['report'].specific_instance()
                response_url = reverse(
                    'case_report_edit',
                    args=(report.id,),
                )
            case_ids = map(lambda c: c.id, case_list)
            querystring = urlencode(
                doseq=True,
                query={'cases': case_ids},
            )
            return HttpResponsePermanentRedirect(response_url + '?' + querystring)
    else:
        change_report_form = ChangeCaseReportForm(prefix='change_report')

    per_page = 1
    page = 1
    if forms['paging'].is_valid():
        if 'per_page' in forms['paging'].cleaned_data:
            per_page = forms['paging'].cleaned_data['per_page']
        if 'page_num' in forms['paging'].cleaned_data:
            page = forms['paging'].cleaned_data['page_num']

    paginator = Paginator(case_list, per_page)
    
    try:
        cases = paginator.page(page)
    except (EmptyPage, InvalidPage):
        cases = paginator.page(paginator.num_pages)
    
    template_media = Media(
        js=(settings.JQUERY_FILE, 'checkboxhider.js', 'selecthider.js'),
    )
    media = reduce(
        lambda m, f: m + f.media,
        forms.values() + [use_report_form],
        template_media
    )
    
    return render_to_response(
        template,
        {
            'forms': forms,
            'is_bound': search_done,
            'media': media,
            'cases': cases,
            'case_count': paginator.count,
            'use_report_form': use_report_form,
            'change_report_form': change_report_form,
            'csv_form': csv_form,
        },
        context_instance= RequestContext(request),
    )

def _case_dump_response(cases):
    
    # TODO move all this into the model definitions?
    
    csv_fields = [] # all the CSV fieldnames, in order
    c = {} # CSV fieldnames, keyed to model fieldnames
    r = {} # model field renderers; callables that take a field value
    g = {} # model field getters; callables that take a model instance
    
    def _display_taxon(t):
        if t is None:
            return None
        return '%s (TSN: %d)' % (t.scientific_name(), t.tsn)
    
    def _display_taxa(taxa):
        return ', '.join(map(_display_taxon, taxa))
    
    def _display_gear_attribs(attribs):
        return ', '.join(map(lambda gt: gt.name, attribs))
    
    def _display_contact(contact):
        if contact is None:
            return u''
        return u'contact #%06d: %s' % (contact.id, contact.name)
    
    def _get_choiced_field(inst, fieldname):
        return getattr(inst, 'get_%s_display' % fieldname)()
    
    # used for m2m fields
    def _get_from_manager(inst, fieldname):
        return getattr(inst, fieldname).all()
    
    c['animal'] = {}
    r['animal'] = {
        'determined_taxon': _display_taxon,
        'probable_taxon': _display_taxon,
    }
    g['animal'] = {
        'determined_gender':  _get_choiced_field,
        'probable_gender':  _get_choiced_field,
        'probable_taxon':  lambda a, fn: getattr(a, fn)(),
    }
    for f in Animal._meta.fields:
        if f.name in ('import_notes', 'documentable_ptr'):
            continue
        
        csv_name = 'animal: ' + f.verbose_name
        csv_fields.append(csv_name)
        c['animal'][f.name] = csv_name
    for propname, displayname in (
        ('probable_taxon', 'probable taxon'),
        ('probable_gender', 'probable sex'),
    ):
        csv_name = 'animal: %s' % displayname
        csv_fields.append(csv_name)
        c['animal'][propname] = csv_name
    
    c['case'] = {}
    r['case'] = {
        'date': lambda d: d.to_unicode(),
    }
    g['case'] = {
        'valid':  _get_choiced_field,
        'human_interaction':  _get_choiced_field,
        'animal_fate':  _get_choiced_field,
        'fate_cause':  _get_choiced_field,
    }
    csv_fields.append('case: name')
    c['case']['name'] = 'case: name'
    for f in Case._meta.fields:
        if f.name in (
            'import_notes',
            'documentable_ptr',
            'animal',
            'current_yearnumber',
        ):
            continue
        
        csv_name = 'case: ' + f.verbose_name
        
        if f.name in Case.si_n_m_fieldnames():
            csv_name = 'case: SI&M: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['case'][f.name] = csv_name
    
    from cetacean_incidents.apps.entanglements.models import (
        Entanglement,
        GearOwner,
        LocationGearSet,
    )

    c['entanglement'] = {}
    r['entanglement'] = {
        'observed_gear_attributes': _display_gear_attribs,
        'implied_observed_gear_attributes': _display_gear_attribs,
        'gear_types': _display_gear_attribs,
        'implied_gear_types': _display_gear_attribs,
        'gear_owner_info': lambda goi: "yes (CONFIDENTIAL!)",
        'targets': lambda gts: ', '.join(map(unicode, gts)),
    }
    g['entanglement'] = {
        'observed_gear_attributes': _get_from_manager,
        'gear_types': _get_from_manager,
        'targets': _get_from_manager,
    }
    for f in Entanglement._meta.fields + Entanglement._meta.many_to_many:
        if f.name in Case._meta.get_all_field_names():
            continue
        if f.name in (
            'case_ptr',
        ):
            continue
        
        csv_name = 'entanglement: ' + f.verbose_name
        
        if f.name in Entanglement.gear_analysis_fieldnames():
            csv_name = 'entanglement: gear analysis: ' + f.verbose_name

        csv_fields.append(csv_name)
        c['entanglement'][f.name] = csv_name
    for propname, displayname in (
        ('implied_observed_gear_attributes', 'implied observed gear attributes'),
        ('implied_gear_types', 'implied analyzed gear attributes'),
    ):
        csv_name = 'entanglement: gear analysis: %s' % displayname
        csv_fields.append(csv_name)
        c['entanglement'][propname] = csv_name

    c['gearowner'] = {}
    r['gearowner'] = {
        'datetime_set': lambda d: d.to_unicode(),
        'datetime_missing': lambda d: d.to_unicode(),
    }
    g['gearowner'] = {}
    for f in GearOwner._meta.fields:
        if f.name in (
            'id',
            'location_gear_set',
        ):
            continue
        
        csv_name = 'entanglement: gear owner: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['gearowner'][f.name] = csv_name

    c['locationset'] = {}
    r['locationset'] = {}
    g['locationset'] = {
        'waters': _get_choiced_field,
        'state': _get_choiced_field,
    }
    for f in LocationGearSet._meta.fields:
        if f.name in (
            'location_ptr',
            'import_notes',
            'roughness',
        ):
            continue
        
        csv_name = 'entanglement: gear owner: location set: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['locationset'][f.name] = csv_name

    c['observation'] = {}
    r['observation'] = {
        'observer': _display_contact,
        'reporter': _display_contact,
        'datetime_observed': lambda d: d.to_unicode(),
        'datetime_reported': lambda d: d.to_unicode(),
        'taxon': _display_taxon,
    }
    g['observation'] = {
        'gender': _get_choiced_field,
        'age_class': _get_choiced_field,
        'condition': _get_choiced_field,
    }
    for f in Observation._meta.fields:
        if f.name in (
            'import_notes',
            'documentable_ptr',
            'animal',
            'cases',
            'initial',
            'exam',
            'location',
            'observer_vessel',
        ):
            continue

        csv_name = 'observation: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['observation'][f.name] = csv_name

    c['location'] = {}
    r['location'] = {}
    g['location'] = {
        'waters': _get_choiced_field,
        'state': _get_choiced_field,
    }
    for f in Location._meta.fields:
        if f.name in (
            'id',
            'import_notes',
            'roughness',
        ):
            continue

        csv_name = 'observation: location: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['location'][f.name] = csv_name
    
    def _display_vessel_tags(tags):
        return ', '.join(map(lambda t: t.name, tags))
    
    c['vessel'] = {}
    r['vessel'] = {
        'vessel_tags': _display_vessel_tags,
        'contact': _display_contact,
    }
    g['vessel'] = {
        'vessel_tags': _get_from_manager,
    }
    for f in VesselInfo._meta.fields:
        if f.name in (
            'id',
        ):
            continue

        csv_name = 'observation: vessel: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['vessel'][f.name] = csv_name
    
    def _display_gear_body_locations(gbls):
        # gbls will be a list of pairs. the first item will be a BodyLocation, the second a GearBodyLocation
        return '; '.join(
            map(
                lambda l: "%s: %s" % (l[0], l[1].gear_seen_here),
                filter(
                    lambda l: l[1] is not None,
                    gbls,
                )
            )
        )
    
    c['entanglementobservation'] = {}
    r['entanglementobservation'] = {
        'gear_body_location': _display_gear_body_locations,
        'gear_retriever': _display_contact,
        'gear_giver': _display_contact,
    }
    g['entanglementobservation'] = {
        'gear_body_location': lambda eo, propname: eo.get_gear_body_locations(),
        'disentanglement_outcome': _get_choiced_field,
    }
    for f in EntanglementObservation._meta.fields + EntanglementObservation._meta.many_to_many:
        if f.name in (
            'observation_ptr',
        ):
            continue

        csv_name = 'observation: entanglement: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['entanglementobservation'][f.name] = csv_name

    c['shipstrikeobservation'] = {}
    r['shipstrikeobservation'] = {}
    g['shipstrikeobservation'] = {}
    for f in ShipstrikeObservation._meta.fields:
        if f.name in (
            'observation_ptr',
            'striking_vessel',
        ):
            continue

        csv_name = 'observation: shipstrike: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['shipstrikeobservation'][f.name] = csv_name

    c['strikingvessel'] = {}
    r['strikingvessel'] = {
        'vessel_tags': _display_vessel_tags,
        'contact': _display_contact,
        'captain': _display_contact,
    }
    g['strikingvessel'] = {
        'vessel_tags': _get_from_manager,
    }
    for f in StrikingVesselInfo._meta.fields:
        if f.name in (
            'id',
            'import_notes',
            'vesselinfo_ptr',
        ):
            continue

        csv_name = 'observation: shipstrike: striking vessel: ' + f.verbose_name
        
        csv_fields.append(csv_name)
        c['strikingvessel'][f.name] = csv_name

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=cases.csv'
    
    writer = UnicodeDictWriter(response, fieldnames=csv_fields, dialect='excel', encoding='utf-8')
    header_row = {}
    for header in csv_fields:
        header_row[header] = header
    writer.writerow(header_row)
    
    for case in cases:
        case = case.specific_instance()
        animal = case.animal
        
        for obs in case.observation_set.all():
            
            row = {}
            
            def _process_fields(keyname, inst):
                for model_fieldname, csv_name in c[keyname].items():
                    val = None
                    if model_fieldname in g[keyname].keys():
                        val = g[keyname][model_fieldname](inst, model_fieldname)
                    else:
                        val = getattr(inst, model_fieldname)
                    if model_fieldname in r[keyname].keys():
                        val = r[keyname][model_fieldname](val)
                    
                    row[csv_name] = val
            
            _process_fields('animal', animal)
            _process_fields('case', case)

            if isinstance(case, Entanglement):
                _process_fields('entanglement', case)
                if not case.gear_owner_info is None:
                    _process_fields('gearowner', case.gear_owner_info)
                    if not case.gear_owner_info.location_gear_set is None:
                        _process_fields('locationset', case.gear_owner_info.location_gear_set)
        
            # Shipstrike cases have no fields of their own

            _process_fields('observation', obs)
            if not obs.location is None:
                _process_fields('location', obs.location)
            if not obs.observer_vessel is None:
                _process_fields('vessel', obs.observer_vessel)
            
            try:
                oe = obs.entanglements_entanglementobservation
                _process_fields('entanglementobservation', oe)
            except EntanglementObservation.DoesNotExist:
                pass

            try:
                oe = obs.shipstrikes_shipstrikeobservation
                _process_fields('shipstrikeobservation', oe)
                if not oe.striking_vessel is None:
                    _process_fields('strikingvessel', oe.striking_vessel)
            except ShipstrikeObservation.DoesNotExist:
                pass

            writer.writerow(row)
    
    return response

def _case_report_change(request, report=None, report_type=None):
    # the list of test cases comes from the GET string
    case_ids = request.GET.getlist('cases')
    cases = Case.objects.filter(id__in=case_ids)
    
    creating = report is None
    
    if creating:
        form_class = {
            'string': StringReportForm,
            'file': FileReportForm,
        }[report_type]
    else:
        if isinstance(report, StringReport):
            form_class = StringReportForm
        if isinstance(report, FileReport):
            form_class = FileReportForm

    if request.POST:
        pressed = request.POST.get('pressed', None)
        form = form_class(request.POST, files=request.FILES, instance=report)
        cases_form = CaseSelectionForm(cases, request.POST, prefix='cases')
        
        if pressed == 'save':
            if form.is_valid():
                if form_class == FileReportForm:
                    report = form.save(commit=False)
                    report.uploader = request.user
                    report.save()
                    form.save_m2m()
                else:
                    report = form.save()

                if creating:
                    url = reverse('case_report_edit', args=(report.id,))
                    querystring = urlencode(doseq=True, query={'cases': case_ids})
                    return redirect(url + '?' + querystring)
        if pressed == 'try':
            if creating:
                report = form.save(commit=False)
            if form.is_valid() and cases_form.is_valid():
                report = report.specific_instance()
                rendered = report.render({
                    'cases': cases_form.cleaned_data['cases'],
                })
                return HttpResponse(rendered, mimetype=report.format)
    else:
        form = form_class(instance=report)
        cases_form = CaseSelectionForm(cases, prefix='cases')
    
    template_media = Media(js=(settings.JQUERY_FILE,))

    return render_to_response(
        'incidents/case_report_change.html',
        {
            'report': report,
            'form': form,
            'cases_form': cases_form,
            'media': template_media + form.media + cases_form.media,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_report_create(request, report_type):
    # the list of test cases comes from the GET string
    return _case_report_change(request, None, report_type)

@login_required
def case_report_edit(request, report_id):
    # the list of test cases comes from the GET string
    report = Report.objects.get(id=report_id).specific_instance()
    return _case_report_change(request, report)

# TODO login_required?
def edit_case_animal(request, case_id):
    
    case = Case.objects.get(id=case_id)
    
    # we'll need to change the animal for all this case's observations, and for
    # any cases they're relevant to, and any of those cases other observations,
    # etc.
    case_set = set([case])
    observation_set = set()
    sets_changed = True
    while sets_changed:
        sets_changed = False
        for c in case_set:
            for o in c.observation_set.all():
                if o not in observation_set:
                    observation_set.add(o)
                    sets_changed = True
        for o in observation_set:
            for c in o.cases.all():
                if c not in case_set:
                    case_set.add(c)
                    sets_changed = True
    
    if request.method == 'POST':
        form = CaseAnimalForm(request.POST, initial={'animal': case.animal.pk})
        if form.is_valid():
            # empty value means new animal
            if form.cleaned_data['animal'] is None:
            # TODO wrap the creation of the animal and the saving of the cases
            # in a transaction? or is that already handled by middleware?
                animal = Animal.objects.create()
            else:
                animal = form.cleaned_data['animal']
            for c in case_set:
                c.animal = animal
                c.save()
            for o in observation_set:
                o.animal = animal
                o.save()
            return redirect(case)

    else:
        form = CaseAnimalForm(initial={'animal': case.animal.pk})
    
    return render_to_response(
        "incidents/edit_case_animal.html",
        {
            'case': case,
            'case_set': case_set,
            'observation_set': observation_set,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

def _change_case(
        request,
        case,
        case_form,
        template='incidents/edit_case.html',
        additional_tabs=[],
        additional_tab_context={},
    ):

    if request.method == 'POST':
        animal_form = AnimalForm(request.POST, prefix='animal', instance=case.animal)
        if animal_form.is_valid() and case_form.is_valid():
            animal_form.save()
            case_form.save()
            return redirect(case)
            
    else:
        animal_form = AnimalForm(prefix='animal', instance=case.animal)
    
    tab_context = Context({
        'animal': case.animal,
        'animal_form': animal_form,
        'case': case,
        'case_form': case_form,
    })
    tab_context.update(additional_tab_context)
    
    tabs = [
        AnimalTab(html_id='animal'),
        CaseTab(html_id='case'),
    ] + additional_tabs
    for t in tabs:
        t.context = tab_context
    
    tabs = Tabs(tabs)
    
    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE),
    )
    
    return render_to_response(
        template, 
        {
            'animal': case.animal,
            'case': case,
            'tabs': tabs,
            'media': case_form.media + animal_form.media + tabs.media + template_media,
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
def edit_case(request, case_id):

    case = Case.objects.get(id=case_id).specific_instance()

    if request.method == 'POST':
        form = CaseForm(request.POST, prefix='case', instance=case)
    else:
        form = CaseForm(prefix='case', instance=case)
        
    return _change_case(request, case, form)

@login_required
@permission_required('incidents.change_case')
@permission_required('incidents.delete_case')
def case_merge(request, destination_id, source_id=None):
    # the "source" case will be deleted and references to it will be change to
    # the "destination" case
    
    destination = Case.objects.get(id=destination_id)
    
    if source_id is None:
        merge_form = CaseMergeSourceForm(destination, request.GET)
        if not merge_form.is_valid():
            return redirect('case_detail', destination.id)
        source = merge_form.cleaned_data['source']
    else:
        source = Case.objects.get(id=source_id)

    form_kwargs = {
        'source': source,
        'destination': destination,
    }
    
    if request.method == 'POST':
        form = CaseMergeForm(data=request.POST, **form_kwargs)
        if form.is_valid():
            form.save()
            form.delete()
            return redirect('case_detail', destination.id)
    else:
        form = CaseMergeForm(**form_kwargs)
    
    return render_to_response(
        'incidents/case_merge.html',
        {
            'object_name': 'case',
            'object_name_plural': 'cases',
            'destination': destination,
            'source': source,
            'form': form,
            'media': form.media,
        },
        context_instance= RequestContext(request),
    )

