from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import Media
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from cetacean_incidents import generic_views
from cetacean_incidents.decorators import permission_required

from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime
from cetacean_incidents.apps.uncertain_datetimes.models import UncertainDateTimeField
from cetacean_incidents.apps.documents.views import _get_documentforms, _save_documentforms

from ..models import Case, YearCaseNumber, CaseDocument
from ..forms import AnimalForm, CaseForm, CaseSearchForm

from cetacean_incidents.apps.entanglements.models import Entanglement
from cetacean_incidents.apps.shipstrikes.models import Shipstrike

@login_required
def case_detail(request, case_id, extra_context={}):
    case_class = Case
    for detailed_class in Case.detailed_classes.values():
        if detailed_class.objects.filter(id=case_id).exists():
            case_class = detailed_class
            break
    return generic_views.object_detail(
        request,
        object_id= case_id,
        queryset= case_class.objects.select_related().all(),
        template_object_name= 'case',
        extra_context= extra_context,
    )

@login_required
def cases_by_year(request, year=None):
    if year is None:
        year = datetime.now().year
    year = int(year)
    yearcasenumbers = YearCaseNumber.objects.filter(year__exact=year).select_related('case')
    return render_to_response(
        "incidents/cases_by_year.html",
        {
            'year': year,
            'yearcasenumbers': yearcasenumbers,
        },
        context_instance= RequestContext(request),
    )

@login_required
def case_search(request, after_date=None, before_date=None):
    # prefix should be the same as the homepage
    prefix = 'case_search'
    form_kwargs = {
        'prefix': prefix,
    }
    if request.GET:
        form_kwargs['data'] = request.GET
    else:
        data = {}
        if not after_date is None:
            data[prefix + '-after_date'] = after_date
        if not before_date is None:
            data[prefix + '-before_date'] = before_date
        if data:
            form_kwargs['data'] = data
    form = CaseSearchForm(**form_kwargs)
    
    case_list = tuple()

    if form.is_valid():

        manager = Case.objects
        if form.cleaned_data['case_type']:
            # TODO go through different case types automatically
            ct = form.cleaned_data['case_type']
            if ct == 'e':
                manager = Entanglement.objects
            if ct == 's':
                manager = Shipstrike.objects
            if ct == 'c':
                manager = Case.objects
        
        query = Q()
    
        if form.cleaned_data['observed_after_date']:
            
            date = form.cleaned_data['observed_after_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_after_q(date, 'observation__datetime_observed')
            
        if form.cleaned_data['observed_before_date']:

            date = form.cleaned_data['observed_before_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_before_q(date, 'observation__datetime_observed')
        
        if form.cleaned_data['reported_after_date']:
        
            date = form.cleaned_data['reported_after_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_after_q(date, 'observation__datetime_reported')
            
        if form.cleaned_data['reported_before_date']:

            date = form.cleaned_data['reported_before_date']
            date = UncertainDateTime.from_date(date)
            
            query &= UncertainDateTimeField.get_before_q(date, 'observation__datetime_reported')

        if form.cleaned_data['taxon']:
            t = form.cleaned_data['taxon']
            # TODO handle taxon uncertainty!
            query &= Q(observation__taxon__in=Taxon.objects.with_descendants(t))

        if form.cleaned_data['case_name']:
            name = form.cleaned_data['case_name']
            query &= Q(names__icontains=name)

        if form.cleaned_data['observation_narrative']:
            on = form.cleaned_data['observation_narrative']
            query &= Q(observation__narrative__icontains=on)

        # TODO shoulde be ordering such that cases with no date come first
        case_order_args = ('-current_yearnumber__year', '-current_yearnumber__number', 'id')

        # TODO Oracle doesn't support distinct() on models with TextFields
        #cases = manager.filter(query).distinct().order_by(*case_order_args)
        cases = manager.filter(query).order_by(*case_order_args)
        
        # simulate distinct() for Oracle
        # an OrderedSet in the collections library would be nice...
        # TODO not even a good workaround, since we have to pass in the count
        # seprately
        seen = set()
        case_list = list()
        for c in cases:
            if not c in seen:
                seen.add(c)
                case_list.append(c)

    return render_to_response(
        "incidents/case_search.html",
        {
            'form': form,
            'case_list': case_list,
            'case_count': len(case_list),
        },
        context_instance= RequestContext(request),
    )

@login_required
@permission_required('incidents.change_case')
@permission_required('incidents.change_animal')
def edit_case(request, case_id, template='incidents/edit_case.html', form_class=CaseForm):
    case = Case.objects.get(id=case_id).detailed
    if request.method == 'POST':
        animal_form = AnimalForm(request.POST, prefix='animal', instance=case.animal)
        form = form_class(request.POST, prefix='case', instance=case)
        if animal_form.is_valid() and form.is_valid():
            animal_form.save()
            form.save()
            return redirect(case)
    else:
        animal_form = AnimalForm(prefix='animal', instance=case.animal)
        form = form_class(prefix='case', instance=case)
    
    template_media = Media(
        css= {'all': (settings.JQUERYUI_CSS_FILE,)},
        js= (settings.JQUERY_FILE, settings.JQUERYUI_JS_FILE),
    )
    
    return render_to_response(
        template, {
            'animal': case.animal,
            'case': case,
            'forms': {
                'animal': animal_form,
                'case': form,
            },
            'media': form.media + animal_form.media + template_media,
        },
        context_instance= RequestContext(request),
    )

