def probable_gender(observations):
    '''\
    Given a queryset of Observations, returns 'f' if any of them contain a
    female and none of them contain a male; ditto 'm'. Returns None if neither
    gender is probable.
    '''
    
    male = bool( observations.filter(gender= 'm') )
    female = bool( observations.filter(gender= 'f') )
    if male and not female:
        return 'm'
    if female and not male:
        return 'f'
    return None

