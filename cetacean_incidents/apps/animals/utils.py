'''Various utility functions for the animal models.'''

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

def probable_taxon(observations):
    '''\
    Given a queryset of Observations, finds the Taxon that is a supertaxon of 
    all the Taxa mentioned. If no such Taxon exists, returns None.
    '''

    from models import Taxon # do this here to avoid circular dependancies

    # TODO fancier algorithm

    # note that values_list returns taxon IDs or Nones
    taxon_ids = observations.values_list('taxon', flat=True)
    # remove Nones
    taxon_ids = filter( lambda x: not x is None, taxon_ids )
    if len(taxon_ids) == 0:
        return None

    taxon_ids = set(taxon_ids)
    taxa = set()
    for id in taxon_ids:
        taxa.add(Taxon.objects.get(id=id))
        
    if len(taxa) == 1:
        return taxa.pop()
    
    supertaxa = []
    depth = float('inf')
    for taxon in taxa:
        ancestors = []
        while taxon is not None:
            ancestors.append(taxon)
            taxon = taxon.supertaxon
        # reverse so root is first
        ancestors.reverse()
        depth = min(depth, len(ancestors))
        supertaxa.append(ancestors)
    
    candidate = None
    for i in range(depth + 1):
        taxa_at_this_depth = set(map(lambda x: x[i], supertaxa)) 
        if len(taxa_at_this_depth) > 1:
            break
        candidate = taxa_at_this_depth.pop()
    
    return candidate
