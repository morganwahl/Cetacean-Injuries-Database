def merge_form_factory(source, destination, model_form, other_models, other_modelforms={}, dont_merge=set()):
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
    
    other_modelforms is a dictionary mapping Model classes to ModelForm classes
    that should be used when recursively merging OneToOne references.
    
    dont_merge is a set of instances (of any Model) that should be ignored when
    recursively merging OneToOne references.
    '''
    
    # TODO could this be a mix-in superclass for ModelForms, instead of taking
    # one as an arg?
    
    class _MergeForm(model_form):
        
        def get_fk_refs():
            '''
            Get all the ForeignKey references to the source instance. Returns a 
            list of model instances and field names that can be passed to 
            (get|set)attr().
            '''

            return []
       
        def get_m2m_refs():
            '''
            Get all the ManyToMany relationship querysets that include the 
            source instance. Returns a list of QuerySets.
            '''
            
            return []
        
        def get_o2o_refs_in_source():
            '''
            Get all the OneToOne references _from_ the source instance. Returns
            a list of fieldnames.
            '''
        
        def get_o2o_refs_to_source():
            '''
            Get all the OneToOne references _to_ the source instance. Returns
            a list of QuerySets.
            '''
        
        def __init__(self):
            super(_MergeForm, self).__init__(instance=destination)
            self.src_inst = source
            self.dst_inst = destination
        
        def save(self, commit=True):
            # TODO create a transaction?
            new_destination = super(_MergeForm, self).save(commit=False)
            
            for other_inst, fieldname in get_fk_refs():
                setattr(other_inst, fieldname, new_destination)
            
            for other_inst, fieldname in self.source_refs['many_to_many']:
                # add a ref to the new_destination
                getattr(other_inst, filename).
            
            if commit:
                new_destinaiton.save()
                self.save_m2m()
                
            return new_destination
        
        def save_m2m(self):
            super(_MergeForm, self).save_m2m()
            for other_inst, fieldname in self.source_refs:
                other_inst.save()

    return _MergeForm()
    
