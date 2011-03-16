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
        Returns a dict like {<other model>: {<other instance primary key>: [<other fields>]}}
        '''
        
        results = {}
        def _results_add(other_model, other_instance, other_field):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instance of the same
            # object in the database
            pk = other_instance.pk
            if not other_model in results:
                results[other_model] = {}
            if not pk in results[other_model]:
                results[other_model][pk] = []
            results[other_model][pk].append(other_field)        
        
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
                    other_instance_pk = getattr(instance, rel_obj.get_accessor_name())
                    _results_add(rel_obj.model, other_instance, rel_obj.field)
            else:
                other_queryset = getattr(instance, rel_obj.get_accessor_name())
                for other_instance in other_queryset.all():
                    _results_add(rel_obj.model, other_instance, rel_obj.field)
        
        return results

    @classmethod
    def _get_m2m_refs(cls, instance):
        '''
        Get all the ManyToManyField references _to_ an instance. Returns a 
        tuple of triples of the form: (<other Model>, <other field>, 
        <other instance primary key>).
        '''
        
        related_objects = instance._meta.get_all_related_many_to_many_objects()
        results = []
        for ro in related_objects:
            other_queryset = getattr(instance, ro.get_accessor_name()).all()
            for other_instance in other_queryset:
                results.append((
                    ro.model,
                    ro.field,
                    other_instance.pk,
                ))
        
        return tuple(results)
    
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
    
    @staticmethod
    def _get_fk_refs_display(fk_refs):
        result = {}
        for model, model_dict in fk_refs.items():
            new_model_dict = {}
            for pk, fields in model_dict.items():
                new_model_dict[model.objects.get(pk=pk)] = map(lambda f: f.verbose_name, fields)
            if len(new_model_dict) == 1:
                model_name = model._meta.verbose_name
            else:
                model_name = model._meta.verbose_name_plural
            result[model_name] = new_model_dict
        return result
    
    @property
    def source_fk_refs_display(self):
        return self._get_fk_refs_display(self.source_fk_refs)
    
    @property
    def destination_fk_refs_display(self):
        return self._get_fk_refs_display(self.destination_fk_refs)

    @staticmethod
    def _get_m2m_refs_display(m2m_refs):
        return map(
            lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[0].objects.get(pk=t[2])),
            m2m_refs
        )

    @property
    def source_m2m_refs_display(self):
        return self._get_m2m_refs_display(self.source_m2m_refs)
    
    @property
    def destination_m2m_refs_display(self):
        return self._get_m2m_refs_display(self.destination_m2m_refs)

    def save(self, commit=True):
        # FIXME uncommited saving is uncertain
        if not commit:
            raise NotImplementedError("uncommited saving of MergeForms is not yet implemented")
        
        for (other_model, other_field, other_instance_pk) in self.source_m2m_refs:
            other_instance = other_model.objects.get(pk=other_instance_pk)
            accessor = getattr(other_instance, other_field.name)
            # don't remove source; the references to it will disappear when it
            # is deleted.
            #accessor.remove(self.source)
            accessor.add(self.destination)
        
        for other_model, model_dict in self.source_fk_refs.items():
            for other_instance_pk, fields in model_dict.items():
                other_instance = other_model.objects.get(pk=other_instance_pk)
                for f in fields:
                    if isinstance(f, models.OneToOneField):
                        raise NotImplementedError("saving o2o references to the merged instance isn't implemented yet")
                    else:
                        setattr(other_instance, f.name, self.destination)
                other_instance.save()
        
        self.source.delete()
        
        return super(MergeForm, self).save(commit=commit)
    
    # FIXME this method is never called
    def pre_save(self):
        for inst in self._save_m2m_todo:
            inst.save()
        
        self.source.delete()

