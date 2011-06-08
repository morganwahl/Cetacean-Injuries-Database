from decimal import Decimal as D

from django import template

from case_extras import YearsForm

register = template.Library()

@register.inclusion_tag('observation_years_link.html')
def observation_years_link():
    return {'years_form': YearsForm()}

@register.simple_tag
def date_observed_display(dt):
    '''\
    Returns the HTML for displaying a just the date of an UncertainDateTime
    from an Observation
    '''
    
    if dt:
        return dt.to_unicode(unknown_char=None, time=False)
    return ''

@register.simple_tag
def datetime_observed_display(dt):
    '''\
    Returns the HTML for displaying a UncertainDateTime from an Observation
    '''
    
    if dt:
        return dt.to_unicode(unknown_char=None, seconds=False)
    return ''

METER = D('1')
CENTIMETER = D('.01') * METER
INCH = D('2.54') * CENTIMETER
FOOT = D('12') * INCH
YARD = D('3') * FOOT
FATHOM = D('2') * YARD

@register.simple_tag
def display_length(length_in_meters, unit, sigdigs=None):
    if not isinstance(length_in_meters, D):
        return ''

    if sigdigs is None:
        sign, digits, exponent = length_in_meters.as_tuple()
        sigdigs = len(digits)
    
    length_in_unit = length_in_meters / {
        'm': METER,
        'cm': CENTIMETER,
        'ft': FOOT,
        'in': INCH,
        'ftm': FATHOM,
    }[unit]
    
    length = round_decimal(length_in_unit, sigdigs)
    unit_abbr = unit
    
    return u'%s %s' % (display_decimal(length), unit_abbr)

def round_decimal(dec, sigdigs):
    sign, digits, exponent = dec.as_tuple()
    rounding_exp = len(digits) - sigdigs + exponent
    return dec.quantize(D(u'1e' + unicode(rounding_exp)))

def display_decimal(dec):
    sign, digits, exponent = dec.as_tuple()

    result = u''    
    if sign:
        result += u'\u2212' # minus sign, instead of hyphen-minus
    
    done = False
    min_place = -50
    place = len(digits) + exponent - 1
    # do we need to prepend zeros?
    while not done:
        if place < min_place:
            raise Exception("infinite loop!")

        # which digit are we printing?
        index = place - exponent # this produces the correct index for the reverse of digits
        index = len(digits) - index - 1 # reverse the index

        if index < 0:
            # are we at place -1?
            if place == -1:
                result += '.'
            # we haven't started yet
            result += '0'
        if index > (len(digits) - 1):
            # we're out of digits
            if place >= 0:
                result += '0'
            else:
                done = True
        else:
            # are we at place -1?
            if place == -1:
                result += '.'
            if (index == (len(digits) - 1) # we're at the last digit
                and place >= 0 # we're not past the decimal yet
                and digits[index] == 0 # the digit is zero
                and len(digits) > 1 # and it's not the only digit
            ):
                #format = u'%s\u0305' # overline character
                format = u'<u>%s</u>' # HTML underline
            else:
                format = '%s'
                
            result += format % unicode(digits[index])

        place -= 1
        
    return result
