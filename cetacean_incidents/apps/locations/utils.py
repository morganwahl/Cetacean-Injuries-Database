import math

MILE_IN_METERS = 1609.344 # exact

# FYI the unicode code-points for degrees, minutes, seconds are
# U+00B0 U+2032 U+2033

def dec_to_dms(decimal_degrees):
    '''\
    Converts an angle in decimal degrees to a negative, degrees, minutes, seconds 
    tuple. The negative member will be True if the argument is negative, False 
    otherwise.
    '''
    
    negative = bool(decimal_degrees < 0)
    # the call to trunc is redundant ( int() will do the same thing ) but i want
    # to make it clear how the conversion works.
    degrees = int(math.trunc(abs(decimal_degrees)))
    minutes = int(math.trunc((abs(decimal_degrees) * 60) - (degrees * 60)))
    seconds = (abs(decimal_degrees) * 60 * 60) - (degrees * 60 * 60) - (minutes * 60)
    
    return (negative, degrees, minutes, seconds)

def dms_to_dec(dms):
    '''\
    Expects a 4-tuple of (neg,deg,min,sec). The neg member should be True if the
    argument is negative, False otherwise.
    '''
    
    (negative, degrees, minutes, seconds) = dms
    
    decimal_degrees = ((degrees * 60 * 60) + (minutes * 60) + seconds) / (60 * 60)
    if negative: decimal_degrees = - decimal_degrees
    
    return decimal_degrees

