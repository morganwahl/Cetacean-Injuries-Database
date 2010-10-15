from django import forms

class MergeForm(forms.ModelForm):
    '''
    Given a source and destination instance of a Model and a corresponding
    ModelForm, returns a subclass of the ModelForm whose fields' HTML has the
    data for both instances. When this form is saved, it saves it's contents
    to the destination instance, changes all references to the sources 
    instance to the destination, and *deletes* the source instance.

    ForeignKeys _to_ the source instance are simply switched to the destination. 
    ManyToMany refs are merged (i.e. the set of refs to source is unioned with 
    the set of refs to dest). OneToOne references ought to be merged 
    recursively...
    '''

    # TODO could this be a mix-in superclass for ModelForms?
        
    def get_fk_refs(self):
        '''
        Get all the ForeignKey references to the source instance. Returns a 
        list of model instances and field names that can be passed to 
        (get|set)attr().
        '''

        return []
   
    def get_m2m_refs(self):
        '''
        Get all the ManyToMany relationship querysets that include the 
        source instance. Returns a list of QuerySets.
        '''
        
        return []
    
    def get_o2o_refs_in_source(self):
        '''
        Get all the OneToOne references _from_ the source instance. Returns
        a list of fieldnames.
        '''
        pass
    
    def get_o2o_refs_to_source(self):
        '''
        Get all the OneToOne references _to_ the source instance. Returns
        a list of QuerySets.
        '''
        pass
    
    def __init__(self, source, destination, other_models, other_mergeforms={}, dont_merge=set())
        '''
        other_mergeforms is a dictionary mapping Model classes to MergeForm 
        classes that should be used when recursively merging OneToOne
        references.

        dont_merge is a set of instances (of any Model) that should be ignored
        when recursively merging OneToOne references.
        '''
        super(MergeForm, self).__init__(instance=destination)
        self.src_inst = source
        self.dst_inst = destination
    
    def save(self, commit=True):
        # TODO create a transaction?
        new_destination = super(MergeForm, self).save(commit=False)
        
        for other_inst, fieldname in get_fk_refs():
            setattr(other_inst, fieldname, new_destination)
        
        if commit:
            new_destinaiton.save()
            self.save_m2m()
            
        return new_destination
    
    def save_m2m(self):
        super(MergeForm, self).save_m2m()

