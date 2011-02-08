import operator

from django.utils.safestring import mark_safe

from cetacean_incidents.apps.jquery_ui.tabs import Tab

class AnimalTab(Tab):
    
    default_html_display= mark_safe(u"<em>Animal</em><br>&nbsp;")

    default_template = 'incidents/edit_animal_tab.html'
    required_context_keys= ('animal', 'animal_form')
    
    def li_error(self):
        return bool(self.context['animal_form'].errors)

class CaseTab(Tab):
    
    default_html_display= mark_safe(u"<em>Case</em><br>&nbsp;")

    default_template= 'incidents/edit_case_tab.html'
    required_context_keys= ('case', 'case_form')

    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [self.context['case_form'].non_field_errors()] + map(
                    lambda f: self.context['case_form'][f].errors, 
                    (
                        'nmfs_id',
                        'happened_after',
                        'valid',
                        'ole_investigation',
                    )
                )
            )
        )
    
class CaseSINMDTab(CaseTab):
    
    default_html_display= mark_safe(u"<em>Case</em><br><abbr title=\"Serious Injury and Mortality Determination\">SI&MD</abbr>")
    default_template= 'incidents/edit_case_sinmd_tab.html'
    
    def li_error(self):
        return reduce(
            operator.or_, map(
                bool,
                [self.context['case_form'].non_field_errors()] + map(
                    lambda f: self.context['case_form'][f].errors,
                    (
                        'review_1_date',
                        'review_1_inits',
                        'review_2_date',
                        'review_2_inits',
                        'case_confirm_criteria',
                        'animal_fate',
                        'fate_cause',
                        'fate_cause_indications',
                        'si_prevented',
                        'included_in_sar',
                        'review_1_notes',
                        'review_2_notes',
                    )
                )
            )
        )

