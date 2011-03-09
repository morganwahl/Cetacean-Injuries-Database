import operator

from django.utils.safestring import mark_safe

from cetacean_incidents.apps.jquery_ui.tabs import Tab

class AnimalTab(Tab):
    
    default_html_display = mark_safe(u"<em>Animal</em><br>&nbsp;")

    default_template = 'incidents/edit_animal_tab.html'
    required_context_keys = ('animal', 'animal_form')
    
    def li_error(self):
        return bool(self.context['animal_form'].errors)

class CaseTab(Tab):
    
    default_html_display = mark_safe(u"<em>Case</em><br>&nbsp;")

    default_template = 'incidents/edit_case_tab.html'
    required_context_keys = ('case', 'case_form')

    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [self.context['case_form'].non_field_errors()] + map(
                    lambda f: self.context['case_form'][f].errors, 
                    (
                        'valid',
                        'happened_after',
                        'human_interaction',
                        'ole_investigation',
                    )
                )
            )
        )
    

class ObservationTab(Tab):
    required_context_keys = ('forms',)

class ObservationReportingTab(ObservationTab):

    default_html_display = mark_safe(u"<em>Observation</em><br>Reporter")
    default_template = 'incidents/edit_observation_reporting_tab.html'
    
    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [
                    self.context['forms']['observation'].non_field_errors(),
                    self.context['forms']['new_reporter'].errors,
                ] + map(
                    lambda f: self.context['forms']['observation'][f].errors, 
                    (
                        'datetime_reported',
                        'new_reporter',
                        'reporter',
                    ),
                ),
            )
        )

class ObservationObservingTab(Tab):
    
    default_html_display = mark_safe(u"<em>Observation</em><br>Observer")
    default_template = 'incidents/edit_observation_observing_tab.html'
    required_context_keys = ('forms',)

    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [
                    self.context['forms']['observation'].non_field_errors(),
                    self.context['forms']['new_observer'].errors,
                    self.context['forms']['location'].errors,
                    self.context['forms']['observer_vessel'].errors,
                ] + map(
                    lambda f: self.context['forms']['observation'][f].errors,
                    (
                        'initial',
                        'exam',
                        'new_observer',
                        'observer',
                        'datetime_observed',
                        'observer_on_vessel',
                    )
                )
            )
        )

class ObservationAnimalIDTab(Tab):
    
    default_html_display = mark_safe(u"<em>Observation</em><br>Animal Description")
    default_template = 'incidents/edit_observation_animal_identification_tab.html'
    required_context_keys = ('forms',)
    
    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [
                    self.context['forms']['observation'].non_field_errors(),
                ] + map(
                    lambda f: self.context['forms']['observation'][f].errors, 
                    (
                        'taxon',
                        'gender',
                        'animal_description',
                        'animal_length_and_sigdigs',
                        #'animal_length',         # handled by ObservationForm
                        #'animal_length_sigdigs',
                        'age_class',
                        'condition',
                        'biopsy',
                        'genetic_sample',
                        'tagged',
                    )
                )
            )
        )

class ObservationIncidentTab(Tab):
    
    default_html_display = mark_safe(u"<em>Observation</em><br>Incident")
    default_template = 'incidents/edit_observation_incident_tab.html'
    required_context_keys = ('forms',)
    
    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [
                    self.context['forms']['observation'].non_field_errors(),
                ] + map(
                    lambda f: self.context['forms']['observation'][f].errors, 
                    (
                        'documentation',
                        'ashore',
                        'indication_entanglement',
                        'indication_shipstrike',
                        'wounded',
                        'wound_description',
                    )
                )
            )
        )

class ObservationNarrativeTab(Tab):

    default_template = 'incidents/edit_observation_narrative_tab.html'
    default_html_display = mark_safe(u"<em>Observation</em><br>Narrative")
    required_context_keys = ('forms',)

    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [
                    self.context['forms']['observation'].non_field_errors(),
                ] + map(
                    lambda f: self.context['forms']['observation'][f].errors, 
                    (
                        'narrative',
                    )
                )
            )
        )

