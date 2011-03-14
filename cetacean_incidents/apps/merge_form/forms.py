from django.core.exceptions import ObjectDoesNotExist
from django.db import models
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
    
    # TODO rename, since it's both o2o and fk
    @classmethod
    def _get_fk_refs(cls, instance):
        '''
        Get all the ForeignKey and OneToOne references _to_ an instance. 
        Returns a tuple of triples of the form: (<other model>, <other field>, 
        <other instance>).
        '''
        
        results = []
        
        rel_objs = instance._meta.get_all_related_objects()
        for rel_obj in rel_objs:
            # note that OneToOneFields are also ForeignKeys
            if isinstance(rel_obj.field, models.OneToOneField):
                # this may be the 'parent_link' field used to implement multi-
                # table inheritance.
                if rel_obj.field.rel.parent_link:
                    # if so, there must not be anything on the other side of
                    # the relation, since that would mean this instance isn't
                    # the most specific one
                    try:
                        getattr(instance, rel_obj.get_accessor_name())
                        # TODO not the best error message
                        raise ValueError("Can't merge instances of non-abstract superclasses unless there is no data for any subclass.")
                    except ObjectDoesNotExist:
                        pass
                else:
                    other_instance = getattr(instance, rel_obj.get_accessor_name())
                    results.append((
                        rel_obj.model,
                        rel_obj.field,
                        other_instance,
                    ))
            else:
                other_queryset = getattr(instance, rel_obj.get_accessor_name())
                for other_instance in other_queryset.all():
                    results.append((
                        rel_obj.model,
                        rel_obj.field,
                        other_instance,
                    ))
        
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
    
    def __init__(self, source, destination, data=None, **kwargs):
        if not isinstance(source, models.Model):
            raise TypeError("source isn't a Model instance!")
        if not isinstance(destination, models.Model):
            raise TypeError("destination isn't a Model instance!")
            # source can be a superclass of destination, but not the other way
            # around.
        if not isinstance(destination, source.__class__):
            raise TypeError("destination type %s can't have source type %s merged into it!"% (destination.__class__, source.__class__))
        if source == destination:
            raise ValueError("can't merge something with itself!")
        
        super(MergeForm, self).__init__(data, instance=destination, **kwargs)
        self.source = source
        self.destination = destination
        
        # TODO start the transaction here! We're getting queryset of other
        # instances to display, then later saving changes to those instances.
    
        self.source_fk_refs = self._get_fk_refs(self.source)
        self.destination_fk_refs = self._get_fk_refs(self.destination)
    
        self.source_m2m_refs = self._get_m2m_refs(self.source)
        self.destination_m2m_refs = self._get_m2m_refs(self.destination)

        self.source_o2o_from_refs = self._get_o2o_refs_from(self.source)
        self.destination_o2o_from_refs = self._get_o2o_refs_from(self.destination)
        
    def save(self, commit=True):
        # FIXME uncommited saving is uncertain
        if not commit:
            raise NotImplementedError("uncommited saving of MergeForms is not yet implemented")
        
        for (other_model, other_field, other_instance) in self.source_fk_refs:
            # note that OneToOneFields are also ForeignKeys
            if isinstance(other_field, models.OneToOneField):
                raise NotImplementedError("saving o2o references to the merged instance isn't implemented yet")
            else:
                setattr(other_instance, other_field.name, self.destination)
                other_instance.save()
        
        if self.source_m2m_refs:
            raise NotImplementedError("saving merged instances with ManyToManyField references to them is not implemented")
        self.source.delete()
        
        return super(MergeForm, self).save(commit=commit)
    
    # FIXME this method is never called
    def pre_save(self):
        for inst in self._save_m2m_todo:
            inst.save()
        
        self.source.delete()

