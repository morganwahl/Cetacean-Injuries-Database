from django import forms
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

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
    
    @classmethod
    def _get_fk_refs(cls, instance):
        '''
        Get all the ForeignKey and OneToOne references _to_ an instance. 
        Returns a tuple of triples of the form: (<other model>, <other field>, 
        <other instance>).
        '''
        
        results = []
        
        import pdb; pdb.set_trace()
        
        rel_objs = instance._meta.get_all_related_objects()
        for rel_obj in rel_objs:
            # note that OneToOneFields are also ForeignKeys
            if isinstance(rel_obj.field, models.OneToOneField):
                # There isn't necessarily another instance at the other end of  
                # the relation
                try:
                    other_instance = getattr(instance, rel_obj.get_accessor_name())
                    results.append( (rel_obj.model, rel_obj.field, other_instance) )
                except ObjectDoesNotExist:
                    pass
            else:
                other_queryset = getattr(instance, rel_obj.get_accessor_name())
                for other_instance in other_queryset.all():
                    results.append( (rel_obj.model, rel_obj.field, other_instance) )
        
        return tuple(results)

    @classmethod
    def _get_m2m_refs(cls, instance):
        '''
        Get all the ManyToManyField references _to_ an instance. Returns a 
        tuple of triples of the form: (<other model>, <other field>, 
        <RelatedManager of other instances>).
        '''
        
        if instance._meta.get_all_related_many_to_many_objects():
            raise NotImplementedError("merging models with ManyToManyField references to them isn't implemented yet")
        
        return []
    
    @classmethod
    def _get_o2o_refs_from(cls, instance):
        '''
        Get all the OneToOne references _from_ an instance. Returns a tuple of 
        fields.
        '''
        
        results = []
        inheritance_fields = instance._meta.parents.values()
        for field in instance._meta.fields:
            if isinstance(field, models.OneToOneField):
                if not field.auto_created:
                    results.append(field)
        
        return tuple(results)
    
    def __init__(self, source, destination):
        super(MergeForm, self).__init__(data={}, instance=destination)
        self.source = source
        self.destination = destination
        
        # TODO start the transaction here! We're getting queryset of other
        # instances to display, then later saving changes to those instances.
    
        self.source_fk_refs = self._get_fk_refs(self.source)
    
        for (other_model, other_field, other_inst) in self.source_fk_refs:
            print "%s \"%s\" has field '%s' pointing to source" % (
                other_model._meta.verbose_name,
                unicode(other_inst),
                other_field.verbose_name,
            )
        
        self.source_m2m_refs = self._get_m2m_refs(self.source)

        self.source_o2o_from_refs = self._get_o2o_refs_from(self.source)
        for field in self.source_o2o_from_refs:
            print "source has one-to-one field %s pointing to %s" % (
                field.name,
                unicode(getattr(self.source, field.name)),
            )

    def save(self, commit=True):
        # TODO create a transaction?
        if not commit:
            self._save_m2m_todo = []
        
        new_destination = super(MergeForm, self).save(commit=commit)
        
        for (other_model, other_field, rel_manager) in self.source_fk_refs:
            for other_instance in rel_manager.all():
                setattr(other_instance, other_field.name, new_destination)
                if commit:
                    other_instance.save()
                else:
                    self._save_m2m_todo.append(other_instance)
        
        
        
        return new_destination
    
    def save_m2m(self):
        super(MergeForm, self).save_m2m()
        
        for inst in self._save_m2m_todo:
            inst.save()
        
