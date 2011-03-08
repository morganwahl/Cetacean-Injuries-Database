import base64
import random

def int_to_bytes(i):
    result = ''
    while i:
        last_byte = i & 0xff
        result = chr(last_byte) + result
        i = i >> 8
    return result

# generate a unique filename
def rand_string(bits=128):
    '''\
    Returns a string of random bits in a url-safe base64 encoding. 
    '''
    
    rand_bytes = int_to_bytes(random.getrandbits(bits))
    return base64.urlsafe_b64encode(rand_bytes)

